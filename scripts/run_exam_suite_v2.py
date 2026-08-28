#!/usr/bin/env python3
"""Раннер экзаменационного сьюта v2 (карточка task-llm-coding-upgrade-exam-suite-v2).

Два бекенда:
  --backend opencode            бесплатные/локальные модели через opencode CLI
  --backend http                любой OpenAI-совместимый эндпоинт (llama-server и т.п.)

Примеры:
  python scripts/run_exam_suite_v2.py --backend opencode --model opencode/hy3-free
  python scripts/run_exam_suite_v2.py --backend http \
      --base-url http://host:8023/v1 --model flash-next
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
DEFAULT_SUITE = ROOT / "evals" / "exam-suite-v2" / "suite.json"
DEFAULT_OUT = ROOT / "runs" / "exam-suite-v2"

CODE_SUFFIX = "Выведи ТОЛЬКО код файла целиком, без markdown-разметки и без пояснений."
FENCE_RE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.DOTALL)


def strip_code_fences(text: str) -> str:
    m = FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
    return "\n".join(lines).strip()


# --- бекенды -----------------------------------------------------------------

def ask_opencode(model: str, prompt: str, timeout: int) -> str:
    opencode_bin = shutil.which("opencode")  # на Windows это npm-шим .cmd
    if not opencode_bin:
        raise RuntimeError("opencode не найден в PATH")
    proc = subprocess.run(
        [opencode_bin, "run", "-m", model, prompt],
        capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    out = ANSI_RE.sub("", proc.stdout)
    lines = [l.rstrip() for l in out.splitlines()]
    body = []
    for line in lines:
        if line.startswith("> ") or line.startswith("Run `"):  # заголовок сессии
            body = []
            continue
        body.append(line)
    return "\n".join(body).strip()


def ask_http(base_url: str, model: str, prompt: str, timeout: int,
             temperature: float = 0.1, max_tokens: int = 4096) -> tuple[str, dict]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if "8023" in base_url:  # llama-server Flash-Next: гасим xhigh-размышления шаблона
        payload["chat_template_kwargs"] = {"reasoning_effort": "low"}
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    timings = data.get("timings", {})
    timings["wall"] = round(time.time() - t0, 1)
    content = data["choices"][0].get("message", {}).get("content", "")
    return content, timings


# --- задачи -------------------------------------------------------------------

def run_executable_task(task: dict, ask) -> dict:
    prompt_file = ROOT / "evals" / "exam-suite-v2" / task["prompt_file"]
    spec = prompt_file.read_text(encoding="utf-8")
    target = ROOT / "evals" / "exam-suite-v2" / task["target_file"]
    prompt = (
        f"Реализуй модуль по спецификации ниже.\n\n{spec}\n\n{CODE_SUFFIX} "
        f"Имя файла: {target.name}"
    )
    t0 = time.time()
    try:
        raw = ask(prompt)
    except Exception as e:  # noqa: BLE001
        return {"id": task["id"], "passed": False, "error": f"model call: {e}",
                "wall_s": round(time.time() - t0, 1)}
    code = strip_code_fences(raw)
    target.write_text(code, encoding="utf-8")
    try:
        proc = subprocess.run(
            task["test_cmd"], cwd=str(ROOT / "evals" / "exam-suite-v2"),
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
        summary = next(
            (l.strip() for l in (proc.stdout + proc.stderr).splitlines()
             if "passed" in l or "failed" in l or "error" in l), "")
        return {
            "id": task["id"], "passed": proc.returncode == 0,
            "wall_s": round(time.time() - t0, 1), "code_chars": len(code),
            "summary": summary,
        }
    except subprocess.TimeoutExpired:
        return {"id": task["id"], "passed": False, "error": "tests timeout",
                "wall_s": round(time.time() - t0, 1)}
    finally:
        target.unlink(missing_ok=True)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def run_knowledge_task(task: dict, ask) -> dict:
    t0 = time.time()
    try:
        raw = ask(task["question"])
    except Exception as e:  # noqa: BLE001
        return {"id": task["id"], "passed": False, "error": f"model call: {e}",
                "wall_s": round(time.time() - t0, 1)}
    answer = norm(raw)
    main_ok = any(norm(a) in answer for a in task["accepted_answers"])
    extras_ok = all(norm(a) in answer for a in task.get("answer_extra_required", []))
    return {
        "id": task["id"], "passed": main_ok and extras_ok,
        "wall_s": round(time.time() - t0, 1),
        "answer_excerpt": raw[:200],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", default=str(DEFAULT_SUITE))
    ap.add_argument("--backend", choices=["opencode", "http"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    if args.backend == "http" and not args.base_url:
        ap.error("--base-url обязателен для --backend http")

    if args.backend == "opencode":
        ask = lambda p: ask_opencode(args.model, p, args.timeout)  # noqa: E731
    else:
        def ask(p: str) -> str:
            content, _ = ask_http(args.base_url, args.model, p, args.timeout)
            return content

    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    stamp = time.strftime("%Y%m%dT%H%M%S")
    out_dir = Path(args.out_dir) / f"{stamp}-{args.model.replace('/', '_')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for task in suite["tasks"]:
        if task["kind"] == "executable":
            r = run_executable_task(task, ask)
        else:
            r = run_knowledge_task(task, ask)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{task['id']}] {status} ({r.get('wall_s')}s) {r.get('summary', r.get('answer_excerpt', '') or r.get('error', ''))[:80]}")

    passed = sum(1 for r in results if r["passed"])
    report = {
        "suite": suite["suite"], "suite_version": suite["version"],
        "backend": args.backend, "model": args.model,
        "timestamp": stamp, "results": results,
        "score": f"{passed}/{len(results)}",
    }
    (out_dir / "results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSCORE: {passed}/{len(results)}  -> {out_dir / 'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
