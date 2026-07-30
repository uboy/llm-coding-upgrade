#!/usr/bin/env python3
"""
run-context-benchmark.py — Measure llama.cpp performance at various context sizes.

Tests PP (prefill) throughput, decode throughput, and wall time at each context size.
Useful for understanding how performance degrades as context grows, and for identifying
when KV-cache offloading to CPU RAM becomes a bottleneck.

Usage:
  python scripts/run-context-benchmark.py \\
    --endpoint http://127.0.0.1:4001/v1 \\
    --model qwen \\
    [--sizes 1000,8000,32000,64000,128000,196000] \\
    [--decode-tokens 32] \\
    [--repeats 1]

Output: runs/ctx-bench-TIMESTAMP.md + summary to stdout
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

# One repetition of the padding base (calibrated to ~9.5 tokens)
BASE_CHUNK = "The quick brown fox jumps over the lazy dog. "

ANSI_GREEN  = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RED    = "\033[91m"
ANSI_CYAN   = "\033[96m"
ANSI_RESET  = "\033[0m"
ANSI_BOLD   = "\033[1m"


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{ANSI_RESET}"


def api_post(endpoint: str, path: str, payload: dict, timeout: int = 600) -> tuple:
    """POST to endpoint/path. Returns (response_dict, wall_s, error_str)."""
    url = endpoint.rstrip("/") + "/" + path.lstrip("/")
    data = json.dumps(payload).encode()
    req = urlrequest.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            wall_s = time.perf_counter() - t0
            return json.loads(resp.read()), wall_s, None
    except HTTPError as e:
        wall_s = time.perf_counter() - t0
        return None, wall_s, f"HTTP {e.code}: {e.reason}"
    except URLError as e:
        wall_s = time.perf_counter() - t0
        return None, wall_s, f"URLError: {e.reason}"
    except Exception as e:
        wall_s = time.perf_counter() - t0
        return None, wall_s, str(e)


def estimate_token_count(endpoint: str, model: str, text: str) -> int | None:
    """Use llama.cpp /tokenize endpoint to get exact token count."""
    # llama.cpp tokenize is at /tokenize (not /v1/tokenize)
    base = endpoint.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = base + "/tokenize"
    payload = {"content": text}
    data = json.dumps(payload).encode()
    req = urlrequest.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlrequest.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return len(result.get("tokens", []))
    except Exception:
        return None


def build_prompt(target_tokens: int, use_calibration: bool = True) -> str:
    """Build a padding prompt of approximately target_tokens tokens."""
    # Rough estimate: BASE_CHUNK ≈ 9.5 tokens
    reps = max(1, int(target_tokens / 9.5))
    return BASE_CHUNK * reps


def run_benchmark(
    endpoint: str,
    model: str,
    sizes: list[int],
    decode_tokens: int,
    repeats: int,
) -> list[dict]:
    results = []
    for target in sizes:
        user_content = build_prompt(target)
        messages = [{"role": "user", "content": user_content}]
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": decode_tokens,
            "stream": False,
            "temperature": 0.0,
        }
        # Timeout scales with context size: ~1ms per token for prefill + decode
        timeout = max(120, target // 80)

        for rep in range(repeats):
            label = f"{target:>10,} tok"
            sys.stdout.write(f"  {label}  rep {rep+1}/{repeats}  ... ")
            sys.stdout.flush()

            resp, wall_s, err = api_post(
                endpoint, "/chat/completions", payload, timeout=timeout
            )

            if err or resp is None:
                print(colorize(f"ERROR: {err}", ANSI_RED))
                results.append({
                    "target": target,
                    "rep": rep,
                    "error": err,
                    "wall_s": wall_s,
                })
                continue

            usage = resp.get("usage", {})
            timings = resp.get("timings", {})
            choices = resp.get("choices", [{}])

            prompt_n   = usage.get("prompt_tokens", 0)
            decode_n   = usage.get("completion_tokens", 0)
            cached_n   = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)

            pp_tps     = timings.get("prompt_per_second", 0.0)
            dec_tps    = timings.get("predicted_per_second", 0.0)
            pp_ms      = timings.get("prompt_ms", 0.0)
            dec_ms     = timings.get("predicted_ms", 0.0)

            # Fallback calculations
            if not pp_tps and pp_ms and prompt_n:
                pp_tps = prompt_n / (pp_ms / 1000)
            if not dec_tps and dec_ms and decode_n:
                dec_tps = decode_n / (dec_ms / 1000)

            finish = choices[0].get("finish_reason", "?") if choices else "?"
            cache_pct = (cached_n / prompt_n * 100) if prompt_n else 0

            if dec_tps >= 35:
                speed_color = ANSI_GREEN
            elif dec_tps >= 20:
                speed_color = ANSI_YELLOW
            else:
                speed_color = ANSI_RED

            status_str = colorize(f"OK ({finish})", ANSI_GREEN) if finish in ("stop", "length") else colorize(finish, ANSI_YELLOW)
            print(
                f"PP {colorize(f'{pp_tps:5.0f}', ANSI_CYAN)} tok/s  "
                f"Dec {colorize(f'{dec_tps:5.1f}', speed_color)} tok/s  "
                f"Wall {wall_s:6.1f}s  "
                f"Ctx {prompt_n:>7,}  "
                f"Cache {cache_pct:.0f}%  "
                f"{status_str}"
            )

            results.append({
                "target": target,
                "rep": rep,
                "prompt_tokens": prompt_n,
                "decode_tokens": decode_n,
                "cached_tokens": cached_n,
                "pp_tps": round(pp_tps, 1),
                "dec_tps": round(dec_tps, 1),
                "wall_s": round(wall_s, 2),
                "finish_reason": finish,
                "error": None,
            })

    return results


def render_markdown(
    endpoint: str,
    model: str,
    decode_tokens: int,
    results: list[dict],
    ts: str,
) -> str:
    rows = []
    for r in results:
        if r.get("error"):
            rows.append(
                f"| {r['target']:>10,} | — | — | {r['wall_s']:>8.1f} | ERROR: {r['error']} |"
            )
        else:
            rows.append(
                f"| {r['prompt_tokens']:>10,} | {r['pp_tps']:>8.1f} | "
                f"{r['dec_tps']:>12.1f} | {r['wall_s']:>8.1f} | "
                f"{r['finish_reason']} / cache {r['cached_tokens']:,} |"
            )

    rows_text = "\n".join(rows)
    return f"""# Context Benchmark

- **Endpoint**: `{endpoint}`
- **Model**: `{model}`
- **Date**: {ts}
- **Decode tokens per call**: {decode_tokens}

## Results

| Ctx tokens | PP tok/s | Decode tok/s | Wall (s) | Status / Cache |
|------------|----------|--------------|----------|----------------|
{rows_text}

## Interpretation

| Metric | What it tells you |
|---|---|
| PP tok/s drops at large ctx | KV-cache is stored in CPU RAM (PCIe bottleneck) or compute-bound on attention |
| Decode tok/s drops at large ctx | KV-cache bandwidth: reading all past KV per step is memory-bandwidth limited |
| Wall time > 20 min at 128K+ | Normal for V100; consider reducing context or enabling KV offload selectively |
| Cache tokens > 0 | llama.cpp prefix cache hit — same prefix sent again, faster prefill |

## Theoretical limits (V100)

| Limit | Value | Bottleneck |
|---|---|---|
| HBM bandwidth | ~900 GB/s | Decode at large ctx |
| PCIe 3.0 x16 | ~14 GB/s | KV offload to CPU RAM |
| FP16 TFLOPS | ~130 | Compute-bound prefill |
"""


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark llama.cpp at various context sizes"
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:4001/v1",
                        help="OpenAI-compatible endpoint base URL")
    parser.add_argument("--model", default="qwen",
                        help="Model alias")
    parser.add_argument("--sizes", default="1000,8000,32000,64000,128000,196000",
                        help="Comma-separated list of target context sizes in tokens")
    parser.add_argument("--decode-tokens", type=int, default=32,
                        help="Max tokens to generate per request (default 32)")
    parser.add_argument("--repeats", type=int, default=1,
                        help="Repeat each size N times (useful for warm cache measurement)")
    parser.add_argument("--output", default=None,
                        help="Output markdown file (default: runs/ctx-bench-TIMESTAMP.md)")
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",")]
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = args.output or f"runs/ctx-bench-{ts}.md"

    print(f"{ANSI_BOLD}Context Benchmark{ANSI_RESET}")
    print(f"  Endpoint : {args.endpoint}")
    print(f"  Model    : {args.model}")
    print(f"  Sizes    : {', '.join(f'{s:,}' for s in sizes)}")
    print(f"  Decode   : {args.decode_tokens} tokens per call")
    print(f"  Repeats  : {args.repeats}")
    print()

    results = run_benchmark(
        endpoint=args.endpoint,
        model=args.model,
        sizes=sizes,
        decode_tokens=args.decode_tokens,
        repeats=args.repeats,
    )

    md = render_markdown(args.endpoint, args.model, args.decode_tokens, results, ts)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(md, encoding="utf-8")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
