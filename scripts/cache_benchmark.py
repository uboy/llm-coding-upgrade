#!/usr/bin/env python3
"""
cache_benchmark.py — Measure KV-cache efficiency in llama.cpp.

Research tool for understanding how to optimize system prompts, skills,
and agent configurations for maximum token savings.

Tests:
  1. cold_warm     — Same prompt sent twice; measures TTFT speedup from warm cache
  2. prefix_share  — N requests sharing a long prefix, different suffixes
  3. team_sim      — Simulate M users sending requests with identical system prompt
  4. prefix_length — Sweep prefix length to find cache efficiency curve

Usage:
  python scripts/cache_benchmark.py \\
    --endpoint http://127.0.0.1:4001/v1 \\
    --model qwen \\
    --test cold_warm \\
    [--prefix-tokens 500] \\
    [--n-requests 8] \\
    [--output runs/cache-bench-TIMESTAMP.json]

  # Run all tests:
  python scripts/cache_benchmark.py --endpoint ... --model qwen --test all
"""

import argparse
import json
import statistics
import sys
import threading
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

# Calibrated: each BASE_UNIT ≈ 9.5 tokens
BASE_UNIT = "The quick brown fox jumps over the lazy dog. "

# Realistic system prompt text (simulates a coding assistant system prompt)
SYSTEM_PROMPT_TEMPLATE = """You are an expert software engineer. Your role is to help developers write high-quality, production-ready code.

Guidelines:
- Write clean, well-documented code following language conventions
- Include proper error handling and edge case coverage
- Prefer explicit over implicit; clarity over cleverness
- Add type hints for all function signatures
- Write code that is testable and maintainable

When asked to implement a function or class:
1. Read the requirements carefully
2. Think about edge cases and error conditions
3. Write the implementation
4. Add docstrings explaining the purpose, parameters, and return values

Current context: {context_filler}
"""


def make_text(tokens: int) -> str:
    """Generate padding text of approximately `tokens` tokens."""
    reps = max(1, int(tokens / 9.5))
    return BASE_UNIT * reps


def api_chat(
    endpoint: str,
    model: str,
    messages: list,
    max_tokens: int = 32,
    timeout: int = 120,
) -> dict:
    """Send chat completion request. Returns result dict with timing info."""
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
        "temperature": 0.0,
    }).encode()
    req = urlrequest.Request(url, data=payload, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            wall_s = time.perf_counter() - t0
            data = json.loads(resp.read())
            usage = data.get("usage", {})
            timings = data.get("timings", {})
            return {
                "ok": True,
                "wall_s": wall_s,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
                "pp_tps": timings.get("prompt_per_second", 0),
                "dec_tps": timings.get("predicted_per_second", 0),
                "pp_ms": timings.get("prompt_ms", 0),
                "cache_n": timings.get("cache_n", 0),  # llama.cpp native cache counter
                "error": None,
            }
    except HTTPError as e:
        return {"ok": False, "wall_s": time.perf_counter() - t0, "error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"ok": False, "wall_s": time.perf_counter() - t0, "error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"ok": False, "wall_s": time.perf_counter() - t0, "error": str(e)}


def test_cold_warm(endpoint: str, model: str, prefix_tokens: int) -> dict:
    """
    Send the same prompt twice.
    First call: cold cache (all tokens computed).
    Second call: warm cache (tokens reused from KV cache).
    """
    print(f"\n{ANSI_BOLD}[1] Cold vs Warm Cache{ANSI_RESET}")
    print(f"    Prefix tokens: ~{prefix_tokens:,}")

    filler = make_text(prefix_tokens)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(context_filler=filler)},
        {"role": "user", "content": "Write a Python function that reverses a string."},
    ]

    # Cold call
    print("    Cold call ... ", end="", flush=True)
    cold = api_chat(endpoint, model, messages, max_tokens=64)
    if not cold["ok"]:
        print(f"{ANSI_RED}FAILED: {cold['error']}{ANSI_RESET}")
        return {"test": "cold_warm", "error": cold["error"]}

    cache_hit_cold = cold["cached_tokens"] / max(cold["prompt_tokens"], 1) * 100
    print(
        f"wall={cold['wall_s']:.2f}s  PP={cold['pp_tps']:.0f} tok/s  "
        f"cache_hit={cache_hit_cold:.0f}%  "
        f"({cold['prompt_tokens']:,} prompt tokens)"
    )

    # Warm call — same messages
    print("    Warm call ... ", end="", flush=True)
    warm = api_chat(endpoint, model, messages, max_tokens=64)
    if not warm["ok"]:
        print(f"{ANSI_RED}FAILED: {warm['error']}{ANSI_RESET}")
        return {"test": "cold_warm", "cold": cold, "error": warm["error"]}

    cache_hit_warm = warm["cached_tokens"] / max(warm["prompt_tokens"], 1) * 100
    speedup = cold["wall_s"] / max(warm["wall_s"], 0.001)
    speedup_color = ANSI_GREEN if speedup > 1.5 else ANSI_YELLOW
    print(
        f"wall={warm['wall_s']:.2f}s  PP={warm['pp_tps']:.0f} tok/s  "
        f"cache_hit={colorize(f'{cache_hit_warm:.0f}%', ANSI_GREEN)}  "
        f"speedup={colorize(f'{speedup:.1f}×', speedup_color)}"
    )

    result = {
        "test": "cold_warm",
        "prefix_tokens": prefix_tokens,
        "cold": cold,
        "warm": warm,
        "cache_hit_cold_pct": round(cache_hit_cold, 1),
        "cache_hit_warm_pct": round(cache_hit_warm, 1),
        "wall_speedup": round(speedup, 2),
        "pp_speedup": round(warm["pp_tps"] / max(cold["pp_tps"], 1), 2),
    }

    print(f"\n    {ANSI_BOLD}Summary:{ANSI_RESET}")
    print(f"      Cold wall time:   {cold['wall_s']:.2f}s")
    print(f"      Warm wall time:   {warm['wall_s']:.2f}s")
    print(f"      Wall speedup:     {colorize(f'{speedup:.1f}×', speedup_color)}")
    print(f"      Cache hit warm:   {colorize(f'{cache_hit_warm:.0f}%', ANSI_GREEN)}")
    print(f"      Tokens saved:     {warm['cached_tokens']:,} / {warm['prompt_tokens']:,}")

    return result


def test_prefix_share(
    endpoint: str, model: str, prefix_tokens: int, n_requests: int
) -> dict:
    """
    Send N requests with a shared long prefix + unique short suffix.
    Measures prefix cache hit rate and latency improvement for subsequent requests.
    Simulates N developers with same project context asking different questions.
    """
    print(f"\n{ANSI_BOLD}[2] Prefix Sharing ({n_requests} requests){ANSI_RESET}")
    print(f"    Shared prefix: ~{prefix_tokens:,} tokens")

    shared_prefix = make_text(prefix_tokens)
    system_msg = SYSTEM_PROMPT_TEMPLATE.format(context_filler=shared_prefix)

    questions = [
        "Write a Python function that reverses a linked list.",
        "Implement a binary search algorithm in Python.",
        "Write a function to check if a string is a palindrome.",
        "Implement a simple stack data structure in Python.",
        "Write a function to find the maximum subarray sum.",
        "Implement a depth-first search for a graph.",
        "Write a function to merge two sorted arrays.",
        "Implement a simple LRU cache in Python.",
        "Write a function to count words in a string.",
        "Implement a function to flatten a nested list.",
        "Write a recursive function to compute Fibonacci numbers.",
        "Implement a function to validate parentheses balance.",
    ]

    results_list = []
    for i in range(n_requests):
        q = questions[i % len(questions)]
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": q},
        ]
        label = f"    Request {i+1:>2}/{n_requests}"
        sys.stdout.write(f"{label} ... ")
        sys.stdout.flush()

        r = api_chat(endpoint, model, messages, max_tokens=64)
        if not r["ok"]:
            print(f"{ANSI_RED}FAILED: {r['error']}{ANSI_RESET}")
            continue

        cache_hit_pct = r["cached_tokens"] / max(r["prompt_tokens"], 1) * 100
        hit_color = ANSI_GREEN if cache_hit_pct > 50 else ANSI_YELLOW
        print(
            f"wall={r['wall_s']:.2f}s  "
            f"PP={r['pp_tps']:.0f} tok/s  "
            f"cache={colorize(f'{cache_hit_pct:.0f}%', hit_color)}  "
            f"({r['cached_tokens']:,}/{r['prompt_tokens']:,} cached)"
        )
        results_list.append(r)

    if not results_list:
        return {"test": "prefix_share", "error": "all requests failed"}

    wall_times = [r["wall_s"] for r in results_list]
    cache_hits = [r["cached_tokens"] / max(r["prompt_tokens"], 1) * 100 for r in results_list]
    pp_tps_list = [r["pp_tps"] for r in results_list if r["pp_tps"] > 0]

    result = {
        "test": "prefix_share",
        "prefix_tokens": prefix_tokens,
        "n_requests": n_requests,
        "wall_mean_s": round(statistics.mean(wall_times), 2),
        "wall_min_s": round(min(wall_times), 2),
        "wall_max_s": round(max(wall_times), 2),
        "cache_hit_mean_pct": round(statistics.mean(cache_hits), 1),
        "cache_hit_max_pct": round(max(cache_hits), 1),
        "pp_tps_mean": round(statistics.mean(pp_tps_list), 1) if pp_tps_list else 0,
        "requests": results_list,
    }

    print(f"\n    {ANSI_BOLD}Summary:{ANSI_RESET}")
    print(f"      Wall mean/min/max:   {result['wall_mean_s']:.2f}s / {result['wall_min_s']:.2f}s / {result['wall_max_s']:.2f}s")
    print(f"      Cache hit (mean):    {colorize(f\"{result['cache_hit_mean_pct']:.0f}%\", ANSI_GREEN)}")
    print(f"      Cache hit (max):     {colorize(f\"{result['cache_hit_max_pct']:.0f}%\", ANSI_GREEN)}")

    return result


def test_prefix_length_sweep(endpoint: str, model: str) -> dict:
    """
    Sweep prefix lengths [50, 200, 500, 1000, 2000, 4000] tokens.
    For each: send twice (cold + warm), record cache_hit_pct and speedup.
    Shows where prefix caching kicks in and how much it helps.
    """
    print(f"\n{ANSI_BOLD}[3] Prefix Length Sweep{ANSI_RESET}")

    sweep_sizes = [50, 200, 500, 1000, 2000, 4000]
    rows = []

    for size in sweep_sizes:
        filler = make_text(size)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(context_filler=filler)},
            {"role": "user", "content": "Write a Python hello world function."},
        ]

        sys.stdout.write(f"    ~{size:>5,} prefix tokens ... ")
        sys.stdout.flush()

        cold = api_chat(endpoint, model, messages, max_tokens=32)
        if not cold["ok"]:
            print(f"{ANSI_RED}ERROR{ANSI_RESET}")
            continue
        warm = api_chat(endpoint, model, messages, max_tokens=32)
        if not warm["ok"]:
            print(f"{ANSI_RED}ERROR (warm){ANSI_RESET}")
            continue

        cache_pct = warm["cached_tokens"] / max(warm["prompt_tokens"], 1) * 100
        speedup = cold["wall_s"] / max(warm["wall_s"], 0.001)
        print(
            f"cold={cold['wall_s']:.2f}s  warm={warm['wall_s']:.2f}s  "
            f"speedup={colorize(f'{speedup:.1f}×', ANSI_GREEN)}  "
            f"cache={colorize(f'{cache_pct:.0f}%', ANSI_GREEN)}"
        )
        rows.append({
            "prefix_target": size,
            "prompt_tokens": warm["prompt_tokens"],
            "cached_tokens": warm["cached_tokens"],
            "cache_pct": round(cache_pct, 1),
            "cold_wall_s": round(cold["wall_s"], 2),
            "warm_wall_s": round(warm["wall_s"], 2),
            "speedup": round(speedup, 2),
        })

    return {"test": "prefix_length_sweep", "rows": rows}


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{ANSI_RESET}"


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark KV-cache efficiency for prompt optimization research"
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:4001/v1")
    parser.add_argument("--model", default="qwen")
    parser.add_argument(
        "--test",
        default="all",
        choices=["cold_warm", "prefix_share", "prefix_sweep", "all"],
        help="Which test(s) to run",
    )
    parser.add_argument("--prefix-tokens", type=int, default=500,
                        help="Prefix size for cold_warm and prefix_share tests")
    parser.add_argument("--n-requests", type=int, default=8,
                        help="Number of requests in prefix_share test")
    parser.add_argument("--output", default=None,
                        help="Output JSON file (default: runs/cache-bench-TIMESTAMP.json)")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = args.output or f"runs/cache-bench-{ts}.json"

    print(f"{ANSI_BOLD}Cache Benchmark{ANSI_RESET}")
    print(f"  Endpoint : {args.endpoint}")
    print(f"  Model    : {args.model}")
    print(f"  Tests    : {args.test}")
    print()
    print("  Note: This tool measures prompt prefix caching (KV-cache reuse).")
    print("  Results guide optimal system prompt placement for agents and teams.")

    all_results = {
        "timestamp": ts,
        "endpoint": args.endpoint,
        "model": args.model,
        "tests": {},
    }

    run_all = args.test == "all"

    if run_all or args.test == "cold_warm":
        r = test_cold_warm(args.endpoint, args.model, args.prefix_tokens)
        all_results["tests"]["cold_warm"] = r

    if run_all or args.test == "prefix_share":
        r = test_prefix_share(args.endpoint, args.model, args.prefix_tokens, args.n_requests)
        all_results["tests"]["prefix_share"] = r

    if run_all or args.test == "prefix_sweep":
        r = test_prefix_length_sweep(args.endpoint, args.model)
        all_results["tests"]["prefix_sweep"] = r

    # Print cache optimization recommendations
    print(f"\n{ANSI_BOLD}Cache Optimization Recommendations:{ANSI_RESET}")
    print("""
  1. PLACE STABLE CONTENT FIRST
     llama.cpp caches from the beginning of the context.
     Put system prompt + knowledge before user messages.
     Never change the beginning of the system prompt between requests.

  2. KEEP SYSTEM PROMPT IDENTICAL ACROSS USERS
     A single shared system prompt is cached once and reused for all users.
     Even one character difference = cache miss for that user.

  3. STRUCTURE: [system prompt] [docs/skills] [user history] [current question]
     This maximizes the cacheable prefix length.

  4. MEASURE WITH THIS TOOL
     Run with --test prefix_sweep to find your optimal prefix length.
     Run with --test prefix_share --n-requests 20 to simulate your team size.
""")

    # Save results
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Results saved: {out_path}")


if __name__ == "__main__":
    main()
