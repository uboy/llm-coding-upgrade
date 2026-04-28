#!/usr/bin/env python3
"""Run strict eval cases with max_tokens=16384 to test think-mode budget."""
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
import shutil
import hashlib
from pathlib import Path

PROXY_URL = os.environ.get("PROXY_URL", "http://127.0.0.1:4001/v1/chat/completions")
MODEL = os.environ.get("MODEL", "qwen")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "16384"))
TIMEOUT = int(os.environ.get("TIMEOUT", "600"))
RESULTS_DIR = Path(__file__).parent
FIXTURE_ROOT = Path(__file__).parent.parent.parent / "eval-fixtures"

CASES = [
    {"id": "case01_ttl_cache", "fixture": "case01_ttl_cache", "solution_file": "ttl_cache.py",
     "prompt": "Implement the missing ttl_cache.py according to README.md. Do not modify tests. Return only the full contents of the file. No Markdown fences. No explanation."},
    {"id": "case02_env_template", "fixture": "case02_env_template", "solution_file": "env_template.py",
     "prompt": "Implement the missing env_template.py according to README.md. Do not modify tests. Return only the full contents of the file. No Markdown fences. No explanation."},
    {"id": "case03_json_patch", "fixture": "case03_json_patch", "solution_file": "json_patch.py",
     "prompt": "Implement the missing json_patch.py according to README.md. Do not modify tests. Return only the full contents of the file. No Markdown fences. No explanation."},
    {"id": "speed_numbers",
     "prompt": "Write the numbers from 1 to 80 separated by spaces, and nothing else."},
]

EXTRA_PROMPT_TEXT = (
    "\n\nIMPORTANT: Your entire response must be ONLY the source code of the solution file. "
    "Do NOT wrap it in markdown fences. Do NOT add explanations. "
    "Think step-by-step first, then output the complete file contents."
)


def api_chat(prompt: str) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(PROXY_URL, data=body,
                                headers={"Content-Type": "application/json"}, method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API call failed: {exc}") from exc
    elapsed = time.time() - started
    payload = json.loads(raw)
    payload["wall_time_s"] = round(elapsed, 3)
    return payload


def check_speed_numbers(content: str) -> bool:
    expected = " ".join(str(i) for i in range(1, 81))
    return content.strip() == expected


def run_tests(case_dir: Path, case: dict) -> dict:
    """Run fixture tests if they exist."""
    test_dir = case_dir / "tests"
    if not test_dir.exists():
        return {"has_tests": False}

    result_file = case_dir / case["solution_file"]
    if not result_file.exists():
        return {"has_tests": True, "ran": False, "reason": "no solution file"}

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(test_dir), "-v"],
            capture_output=True, text=True, timeout=60, cwd=str(case_dir),
        )
        return {
            "has_tests": True, "ran": True,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-1000:] if len(completed.stdout) > 1000 else completed.stdout,
            "stderr": completed.stderr[-1000:] if len(completed.stderr) > 1000 else completed.stderr,
            "passed": completed.returncode == 0,
        }
    except Exception as exc:
        return {"has_tests": True, "ran": False, "reason": str(exc)}


def extract_code(response_text: str) -> str:
    """Extract code from response, stripping markdown fences if present."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```python) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        return "\n".join(lines)
    return text


def main():
    print(f"=== max_tokens={MAX_TOKENS} think-mode eval ===")
    print(f"Proxy: {PROXY_URL}, Model: {MODEL}")
    print()

    all_results = []

    for case in CASES:
        case_id = case["id"]
        case_dir = RESULTS_DIR / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        # Copy fixture if it's a fixture case
        if "fixture" in case:
            fixture_src = FIXTURE_ROOT / case["fixture"]
            if fixture_src.exists():
                # Copy fresh fixture
                if case_dir.exists():
                    shutil.rmtree(case_dir)
                shutil.copytree(fixture_src, case_dir)

        # Read README for context if available
        readme_path = case_dir / "README.md"
        prompt = case["prompt"]
        if readme_path.exists():
            readme_text = readme_path.read_text()
            prompt = f"{readme_text}\n\n{prompt}"

        prompt += EXTRA_PROMPT_TEXT

        print(f"[{case_id}] Sending request (max_tokens={MAX_TOKENS})...", flush=True)
        try:
            resp = api_chat(prompt)
        except Exception as exc:
            print(f"[{case_id}] FAILED: {exc}")
            all_results.append({"case_id": case_id, "error": str(exc)})
            continue

        msg = resp.get("choices", [{}])[0].get("message", {})
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning_content", "") or ""
        usage = resp.get("usage", {})
        finish = resp.get("choices", [{}])[0].get("finish_reason", "?")
        wall = resp.get("wall_time_s", 0)
        comp_tokens = usage.get("completion_tokens", 0)
        timings = resp.get("timings", {})
        tps = timings.get("predicted_per_second", 0)

        print(f"[{case_id}] {comp_tokens} tokens, {wall:.1f}s, "
              f"reasoning={len(reasoning)}ch, content={len(content)}ch, "
              f"finish={finish}, tps={tps:.1f}")

        # Save raw response
        raw_data = {
            "ok": True, "wall_time_s": wall,
            "usage": usage, "timings": timings,
            "reasoning_chars": len(reasoning),
            "content_chars": len(content),
            "finish_reason": finish,
            "completion_tps_client": tps,
            "reasoning_preview": reasoning[:500] if reasoning else "",
            "content_preview": content[:500] if content else "",
        }
        (case_dir / "raw.json").write_text(json.dumps(raw_data, indent=2, ensure_ascii=False))
        (case_dir / "response.txt").write_text(content)

        # Try to save solution file
        test_result = {"has_tests": False}
        if "solution_file" in case and content:
            code = extract_code(content)
            (case_dir / case["solution_file"]).write_text(code)
            print(f"[{case_id}] Saved {len(code)} chars to {case['solution_file']}")
            test_result = run_tests(case_dir, case)

        # Quick checks
        passed_check = None
        if case_id == "speed_numbers":
            passed_check = check_speed_numbers(content)
            print(f"[{case_id}] speed_numbers check: {'PASS' if passed_check else 'FAIL'}")

        if test_result.get("ran"):
            print(f"[{case_id}] Tests: {'PASS' if test_result['passed'] else 'FAIL'} "
                  f"(rc={test_result['returncode']})")

        all_results.append({
            "case_id": case_id,
            "completion_tokens": comp_tokens,
            "wall_time_s": wall,
            "tps": tps,
            "reasoning_chars": len(reasoning),
            "content_chars": len(content),
            "finish_reason": finish,
            "test_result": test_result,
            "speed_check": passed_check,
        })
        print()

    # Summary
    print("=" * 60)
    print(f"RESULTS (max_tokens={MAX_TOKENS})")
    print("=" * 60)
    for r in all_results:
        if "error" in r:
            print(f"  {r['case_id']:25s} ERROR: {r['error']}")
            continue
        test_str = ""
        if r.get("test_result", {}).get("ran"):
            test_str = f" tests={'PASS' if r['test_result']['passed'] else 'FAIL'}"
        if r.get("speed_check") is not None:
            test_str = f" speed={'PASS' if r['speed_check'] else 'FAIL'}"
        print(f"  {r['case_id']:25s} {r['completion_tokens']:6d} tok  "
              f"{r['wall_time_s']:6.1f}s  reason={r['reasoning_chars']:6d}  "
              f"content={r['content_chars']:6d}  finish={r['finish_reason']}{test_str}")

    # Save summary
    summary = {
        "run_id": f"max-tokens-16k-test",
        "max_tokens": MAX_TOKENS,
        "model": MODEL,
        "generated_at": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        "results": all_results,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nSummary saved to {RESULTS_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
