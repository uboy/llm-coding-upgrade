#!/usr/bin/env python3
"""
diagnose.py — System diagnostics for llama.cpp inference server.

Identifies performance bottlenecks:
  - GPU memory utilization and bandwidth
  - PCIe bandwidth (estimated and measured)
  - Theoretical vs actual decode throughput
  - What's limiting performance: compute / HBM bandwidth / PCIe

Usage:
  python scripts/diagnose.py --endpoint http://127.0.0.1:4001/v1 --model qwen

Requirements: nvidia-smi must be available (runs on the inference server).
  For remote servers, either SSH and run there, or point at a remote endpoint.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

ANSI_GREEN  = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RED    = "\033[91m"
ANSI_CYAN   = "\033[96m"
ANSI_BOLD   = "\033[1m"
ANSI_RESET  = "\033[0m"

# Theoretical limits by GPU model (GB/s HBM bandwidth)
GPU_BANDWIDTH_GB_S = {
    "V100":   900,
    "V100S":  1134,
    "A100":   2000,
    "A100 80GB": 2000,
    "H100":   3350,
    "RTX 3090":  936,
    "RTX 4090": 1008,
    "RTX 3080": 760,
    "A6000":  768,
    "A40":    696,
    "L40":    864,
    "L40S":   864,
}

# PCIe theoretical bandwidth (GB/s, bidirectional)
PCIE_BANDWIDTH = {
    "PCIe 3.0 x16": 16,
    "PCIe 4.0 x16": 32,
    "PCIe 5.0 x16": 64,
    "NVLink":       600,
}


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{ANSI_RESET}"


def run_cmd(cmd: list[str], timeout: int = 10) -> tuple[str, str, int]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", f"Command not found: {cmd[0]}", 1
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1


def get_gpu_info() -> list[dict]:
    """Query nvidia-smi for GPU inventory."""
    out, err, rc = run_cmd([
        "nvidia-smi",
        "--query-gpu=index,name,memory.used,memory.total,memory.free,"
        "utilization.gpu,utilization.memory,temperature.gpu,clocks.current.sm,clocks.max.sm",
        "--format=csv,noheader,nounits"
    ])
    if rc != 0:
        return []

    gpus = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 10:
            continue
        try:
            gpus.append({
                "index":     int(parts[0]),
                "name":      parts[1],
                "mem_used":  int(parts[2]),
                "mem_total": int(parts[3]),
                "mem_free":  int(parts[4]),
                "gpu_util":  int(parts[5]),
                "mem_util":  int(parts[6]),
                "temp_c":    int(parts[7]),
                "clk_cur":   int(parts[8]) if parts[8].isdigit() else 0,
                "clk_max":   int(parts[9]) if parts[9].isdigit() else 0,
            })
        except (ValueError, IndexError):
            continue
    return gpus


def get_pcie_info() -> list[dict]:
    """Query nvidia-smi for PCIe bandwidth statistics."""
    out, err, rc = run_cmd([
        "nvidia-smi",
        "--query-gpu=index,pcie.link.gen.current,pcie.link.width.current,"
        "pcie.link.gen.max,pcie.link.width.max",
        "--format=csv,noheader,nounits"
    ])
    if rc != 0:
        return []

    results = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            continue
        try:
            gen_cur  = int(parts[1]) if parts[1].isdigit() else 0
            width_cur = int(parts[2]) if parts[2].isdigit() else 0
            gen_max  = int(parts[3]) if parts[3].isdigit() else 0
            width_max = int(parts[4]) if parts[4].isdigit() else 0

            # Theoretical bandwidth per PCIe gen (GB/s per lane, bidirectional)
            gen_bw = {1: 0.5, 2: 1.0, 3: 2.0, 4: 4.0, 5: 8.0}
            bw_cur = gen_bw.get(gen_cur, 0) * width_cur
            bw_max = gen_bw.get(gen_max, 0) * width_max

            results.append({
                "index": int(parts[0]),
                "gen_current": gen_cur,
                "width_current": width_cur,
                "gen_max": gen_max,
                "width_max": width_max,
                "bw_theoretical_gb_s": bw_cur,
                "bw_max_gb_s": bw_max,
                "at_max_width": width_cur == width_max,
                "at_max_gen": gen_cur == gen_max,
            })
        except (ValueError, IndexError):
            continue
    return results


def measure_pcie_bandwidth(endpoint: str, model: str) -> dict:
    """
    Estimate PCIe bandwidth by timing a large prompt.
    If KV cache is in CPU RAM (--no-kv-offload NOT set, but ctx > VRAM),
    the prefill speed will be PCIe-limited.

    This test: sends a large (50K token) prompt and observes if PP tok/s drops
    compared to what HBM bandwidth would suggest.
    """
    print("  Running PCIe bandwidth estimation... ", end="", flush=True)
    chunk = "The quick brown fox jumps over the lazy dog. "
    padding = chunk * 5200  # ~50K tokens
    messages = [{"role": "user", "content": padding}]
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 8,
        "stream": False,
        "temperature": 0.0,
    }).encode()
    req = urlrequest.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    try:
        with urlrequest.urlopen(req, timeout=300) as resp:
            wall_s = time.perf_counter() - t0
            data = json.loads(resp.read())
    except Exception as e:
        print(colorize(f"FAILED: {e}", ANSI_RED))
        return {"error": str(e)}

    usage = data.get("usage", {})
    timings = data.get("timings", {})
    prompt_n = usage.get("prompt_tokens", 0)
    pp_tps = timings.get("prompt_per_second", 0)

    print(f"done  prompt={prompt_n:,} tokens  PP={pp_tps:.0f} tok/s  wall={wall_s:.1f}s")
    return {
        "prompt_tokens": prompt_n,
        "pp_tps": round(pp_tps, 1),
        "wall_s": round(wall_s, 2),
    }


def api_quick_bench(endpoint: str, model: str) -> dict:
    """Short inference test: measure current decode tok/s."""
    messages = [{"role": "user", "content": "List 10 programming languages, one per line."}]
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 128,
        "stream": False,
        "temperature": 0.0,
    }).encode()
    req = urlrequest.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    try:
        with urlrequest.urlopen(req, timeout=60) as resp:
            wall_s = time.perf_counter() - t0
            data = json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}

    timings = data.get("timings", {})
    usage = data.get("usage", {})
    return {
        "ok": True,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "pp_tps": timings.get("prompt_per_second", 0),
        "dec_tps": timings.get("predicted_per_second", 0),
        "wall_s": round(wall_s, 2),
    }


def identify_bottleneck(
    gpus: list[dict],
    dec_tps: float,
    pcie_list: list[dict],
    large_ctx_pp_tps: float = 0,
) -> dict:
    """
    Analyze metrics and identify the current performance bottleneck.

    Returns bottleneck classification and recommendations.
    """
    issues = []
    recommendations = []

    if not gpus:
        return {"bottleneck": "unknown", "issues": ["nvidia-smi not available"]}

    # Determine GPU family and theoretical bandwidth
    gpu_name = gpus[0]["name"]
    hbm_bw = 0
    for key, bw in GPU_BANDWIDTH_GB_S.items():
        if key in gpu_name:
            hbm_bw = bw
            break
    if not hbm_bw:
        hbm_bw = 900  # V100 default

    n_gpus = len(gpus)
    total_hbm_bw = hbm_bw * n_gpus

    # Decode throughput analysis
    # For a model with D parameters in float16: bytes_per_token = 2*D
    # decode bandwidth = dec_tps * bytes_per_token
    # We can't know exact model size here, but we can estimate from dec_tps vs theoretical
    # V100: 900 GB/s, typical 30B model = ~60GB = ~1000 tok/s theoretically
    # Actual: usually 40-80 tok/s for 30B+ on V100 (due to overhead)

    # Check VRAM usage
    total_vram_used = sum(g["mem_used"] for g in gpus)
    total_vram_total = sum(g["mem_total"] for g in gpus)
    vram_usage_pct = total_vram_used / total_vram_total * 100

    if vram_usage_pct > 95:
        issues.append(f"VRAM nearly full ({vram_usage_pct:.1f}%) — risk of OOM at large ctx")
        recommendations.append("Reduce --ctx-size or use q4_0 KV cache to free VRAM")

    # Check GPU utilization
    avg_util = sum(g["gpu_util"] for g in gpus) / n_gpus
    if avg_util < 20 and dec_tps > 0:
        issues.append(f"Low GPU compute utilization ({avg_util:.0f}%) during decode — memory-bandwidth bound")

    # PCIe analysis
    for pcie in pcie_list:
        if not pcie.get("at_max_gen") or not pcie.get("at_max_width"):
            issues.append(
                f"GPU {pcie['index']}: PCIe running at Gen{pcie['gen_current']} x{pcie['width_current']} "
                f"(max: Gen{pcie['gen_max']} x{pcie['width_max']}) — "
                f"bandwidth {pcie['bw_theoretical_gb_s']:.0f} GB/s vs max {pcie['bw_max_gb_s']:.0f} GB/s"
            )
            recommendations.append(
                f"GPU {pcie['index']}: Check PCIe slot — not running at max bandwidth"
            )

    # Large context PP analysis
    if large_ctx_pp_tps > 0:
        # For 50K token prefill on V100 (3 GPUs):
        # If KV fits in VRAM: PP should be >300 tok/s
        # If KV is partially in CPU: PP will be much lower (PCIe limited)
        if large_ctx_pp_tps < 100:
            issues.append(
                f"PP tok/s at 50K ctx is {large_ctx_pp_tps:.0f} — likely PCIe bottleneck "
                f"(KV cache partially in CPU RAM)"
            )
            recommendations.append(
                "KV cache is spilling to CPU RAM — consider: "
                "reduce ctx-size, use q4_0/q8_0 KV, add more VRAM, or accept PCIe overhead"
            )

    # Decode bottleneck assessment
    bottleneck = "unknown"
    if dec_tps > 0:
        if avg_util > 60:
            bottleneck = "compute"
            recommendations.append("Compute-bound: reducing batch size or using smaller model may help")
        elif large_ctx_pp_tps > 0 and large_ctx_pp_tps < 200:
            bottleneck = "pcie_kv_offload"
        else:
            bottleneck = "hbm_bandwidth"
            recommendations.append(
                f"Memory-bandwidth bound (typical for decode). "
                f"Theoretical max at {hbm_bw} GB/s HBM. "
                "Speculative decoding can improve decode tok/s."
            )

    return {
        "bottleneck": bottleneck,
        "hbm_bw_gb_s_per_gpu": hbm_bw,
        "total_hbm_bw_gb_s": total_hbm_bw,
        "vram_usage_pct": round(vram_usage_pct, 1),
        "avg_gpu_util_pct": round(avg_util, 1),
        "issues": issues,
        "recommendations": recommendations,
    }


def print_separator(title: str = ""):
    w = 70
    if title:
        pad = (w - len(title) - 2) // 2
        print(f"{'─' * pad} {title} {'─' * (w - pad - len(title) - 2)}")
    else:
        print("─" * w)


def main():
    parser = argparse.ArgumentParser(description="Diagnose llama.cpp server performance")
    parser.add_argument("--endpoint", default="http://127.0.0.1:4001/v1")
    parser.add_argument("--model", default="qwen")
    parser.add_argument("--skip-large-ctx", action="store_true",
                        help="Skip 50K-token PCIe bandwidth test (faster)")
    parser.add_argument("--output", default=None,
                        help="Save JSON report to file")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{ANSI_BOLD}LLM Server Diagnostics{ANSI_RESET}")
    print(f"  Endpoint : {args.endpoint}")
    print(f"  Model    : {args.model}")
    print(f"  Time     : {ts}")

    report = {
        "timestamp": ts,
        "endpoint": args.endpoint,
        "model": args.model,
    }

    # 1. GPU inventory
    print_separator("GPU Inventory")
    gpus = get_gpu_info()
    if gpus:
        for g in gpus:
            mem_pct = g["mem_used"] / g["mem_total"] * 100
            mem_color = ANSI_RED if mem_pct > 90 else ANSI_YELLOW if mem_pct > 75 else ANSI_GREEN
            clk_pct = g["clk_cur"] / g["clk_max"] * 100 if g["clk_max"] else 0
            print(
                f"  GPU {g['index']}: {g['name']:30s}  "
                f"VRAM {colorize(f'{g[\"mem_used\"]:>6,}/{g[\"mem_total\"]:>6,} MiB ({mem_pct:.0f}%)', mem_color)}  "
                f"Util {g['gpu_util']:>3d}%  "
                f"Temp {g['temp_c']:>3d}°C  "
                f"Clk {g['clk_cur']}/{g['clk_max']} MHz"
            )
        report["gpus"] = gpus
    else:
        print(f"  {colorize('nvidia-smi not available — run on the inference server', ANSI_YELLOW)}")
        report["gpus"] = []

    # 2. PCIe info
    print_separator("PCIe Configuration")
    pcie_list = get_pcie_info()
    if pcie_list:
        for p in pcie_list:
            bw_color = ANSI_RED if not p["at_max_gen"] or not p["at_max_width"] else ANSI_GREEN
            print(
                f"  GPU {p['index']}: PCIe Gen{p['gen_current']} x{p['width_current']}  "
                f"→ {colorize(f'{p[\"bw_theoretical_gb_s\"]:.0f} GB/s', bw_color)}  "
                f"(max: Gen{p['gen_max']} x{p['width_max']} = {p['bw_max_gb_s']:.0f} GB/s)"
            )
        report["pcie"] = pcie_list
    else:
        print(f"  {colorize('PCIe info unavailable', ANSI_YELLOW)}")
        report["pcie"] = []

    # 3. Quick inference test
    print_separator("Inference Baseline")
    print("  Short prompt benchmark... ", end="", flush=True)
    quick = api_quick_bench(args.endpoint, args.model)
    if quick["ok"]:
        pp_color = ANSI_GREEN if quick["pp_tps"] > 300 else ANSI_YELLOW
        dec_color = ANSI_GREEN if quick["dec_tps"] > 35 else ANSI_YELLOW if quick["dec_tps"] > 15 else ANSI_RED
        print(
            f"PP {colorize(f'{quick[\"pp_tps\"]:.0f}', pp_color)} tok/s  "
            f"Decode {colorize(f'{quick[\"dec_tps\"]:.1f}', dec_color)} tok/s  "
            f"Prompt {quick['prompt_tokens']} tok  "
            f"Decode {quick['completion_tokens']} tok  "
            f"Wall {quick['wall_s']}s"
        )
        report["baseline"] = quick
    else:
        print(colorize(f"FAILED: {quick['error']}", ANSI_RED))
        report["baseline"] = quick

    # 4. Large context PCIe test
    large_pp_tps = 0
    if not args.skip_large_ctx:
        print_separator("Large Context PCIe Test (~50K tokens)")
        print("  Note: this takes ~2 min on V100. Use --skip-large-ctx to omit.")
        large = measure_pcie_bandwidth(args.endpoint, args.model)
        report["large_ctx"] = large
        large_pp_tps = large.get("pp_tps", 0)
    else:
        print_separator("Large Context Test (skipped)")
        report["large_ctx"] = {"skipped": True}

    # 5. Bottleneck analysis
    print_separator("Bottleneck Analysis")
    dec_tps = quick.get("dec_tps", 0) if quick.get("ok") else 0
    analysis = identify_bottleneck(gpus, dec_tps, pcie_list, large_pp_tps)
    report["analysis"] = analysis

    bottleneck_colors = {
        "compute": ANSI_YELLOW,
        "hbm_bandwidth": ANSI_CYAN,
        "pcie_kv_offload": ANSI_RED,
        "unknown": ANSI_RESET,
    }
    bc = bottleneck_colors.get(analysis["bottleneck"], ANSI_RESET)
    print(f"  Bottleneck: {colorize(analysis['bottleneck'].upper(), bc + ANSI_BOLD)}")
    print(f"  VRAM usage: {analysis['vram_usage_pct']:.1f}%")
    print(f"  GPU compute util: {analysis['avg_gpu_util_pct']:.0f}%")
    print(f"  HBM bandwidth per GPU: {analysis['hbm_bw_gb_s_per_gpu']} GB/s (theoretical)")
    print(f"  Total HBM bandwidth: {analysis['total_hbm_bw_gb_s']} GB/s ({len(gpus)} GPUs)")

    if analysis["issues"]:
        print(f"\n  {ANSI_BOLD}Issues:{ANSI_RESET}")
        for issue in analysis["issues"]:
            print(f"    ⚠  {colorize(issue, ANSI_YELLOW)}")

    if analysis["recommendations"]:
        print(f"\n  {ANSI_BOLD}Recommendations:{ANSI_RESET}")
        for rec in analysis["recommendations"]:
            print(f"    →  {rec}")

    print_separator()

    # Save report
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report saved: {args.output}")


if __name__ == "__main__":
    main()
