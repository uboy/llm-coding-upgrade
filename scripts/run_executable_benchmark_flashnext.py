import urllib.request
import urllib.error
import subprocess
import json
import time
import re
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE_FILE = os.path.join(PROJECT_ROOT, "evals/exec-benchmark-suite.json")
OUT_DIR = os.path.join(PROJECT_ROOT, "runs/exec_benchmark_flashnext")
os.makedirs(OUT_DIR, exist_ok=True)

with open(SUITE_FILE, "r", encoding="utf-8") as f:
    suite = json.load(f)

tasks = [t for t in suite.get("tasks", []) if t.get("evaluation_mode") == "executable_test" and t.get("language") == "python"]

ENDPOINT = "http://v100-host:8023/v1/chat/completions"
MODEL_NAME = "flash-next"
# Ответ может содержать блок размышлений <think>...</think> — вырезаем до извлечения кода.
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

def extract_python_code(text):
    text = THINK_RE.sub("", text)
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        if line.strip().startswith("```"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()

def query_model(prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты опытный инженер-программист. Пиши ТОЛЬКО чистый Python-код без markdown-разметки и без пояснений."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
        # Сравнимо с Fast Mode у Qwen3.8-27B: шаблон Flash-Next по умолчанию
        # ставит reasoning effort xhigh (тысячи токенов размышлений на задачу).
        "chat_template_kwargs": {"reasoning_effort": "low"}
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            wall = time.time() - start
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            reasoning = choice.get("message", {}).get("reasoning_content", "")
            timings = data.get("timings", {})
            return {
                "success": True,
                "wall_time": round(wall, 2),
                "decode_tok_s": round(timings.get("predicted_per_second", 0), 1),
                "content": content,
                "reasoning_len": len(reasoning)
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "wall_time": round(time.time() - start, 2),
            "decode_tok_s": 0,
            "content": "",
            "reasoning_len": 0
        }

print("=" * 80)
print(f"STARTING EXECUTABLE PYTEST BENCHMARK ON {len(tasks)} PYTHON TASKS")
print(f"Target: Qwen3.8-Flash-Next UD-Q4_K_XL (port 8023, 1x..3x V100 + RAM offload)")
print("=" * 80)

results = []

for t in tasks:
    t_id = t["id"]
    t_name = t["name"]
    fixture_dir = os.path.join(PROJECT_ROOT, t["fixture_dir"])
    target_file = t["target_file"]
    code_path = os.path.join(fixture_dir, target_file)
    readme_path = os.path.join(fixture_dir, "README.md")

    print(f"\n[{t_id}] {t_name}...")

    if not os.path.exists(readme_path):
        print(f"  -> SKIP (README not found at {readme_path})")
        continue

    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    prompt = f"Реализуй модуль `{target_file}` в соответствии со следующей спецификацией:\n\n{readme_content}\n\nВыведи ТОЛЬКО чистый Python код."

    res = query_model(prompt)
    if not res["success"]:
        print(f"  -> MODEL ERROR: {res.get('error')}")
        results.append({
            "id": t_id,
            "name": t_name,
            "passed": False,
            "error": res.get("error"),
            "wall_time": res["wall_time"]
        })
        continue

    code = extract_python_code(res["content"])
    print(f"  -> Generated {len(code)} chars of code in {res['wall_time']}s ({res['decode_tok_s']} tok/s, reasoning {res['reasoning_len']} chars)")

    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)

    with open(os.path.join(OUT_DIR, f"{t_id}_generated.py"), "w", encoding="utf-8") as f:
        f.write(code)

    tests_dir = os.path.join(fixture_dir, "tests")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{fixture_dir};{env.get('PYTHONPATH', '')}"

    cmd = [
        sys.executable, "-m", "pytest",
        tests_dir,
        "-v", "--tb=short"
    ]

    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        test_out = proc.stdout + "\n" + proc.stderr
        passed = (proc.returncode == 0)

        summary_line = ""
        for line in test_out.splitlines():
            if "passed" in line or "failed" in line or "error" in line:
                summary_line = line.strip()

        status_tag = "PASS" if passed else "FAIL"
        print(f"  -> [pytest: {status_tag}] {summary_line}")

        with open(os.path.join(OUT_DIR, f"{t_id}_test_output.txt"), "w", encoding="utf-8") as f:
            f.write(test_out)

        results.append({
            "id": t_id,
            "name": t_name,
            "passed": passed,
            "exit_code": proc.returncode,
            "wall_time": res["wall_time"],
            "decode_tok_s": res["decode_tok_s"],
            "code_len": len(code),
            "reasoning_len": res["reasoning_len"],
            "summary": summary_line
        })
    except subprocess.TimeoutExpired:
        print("  -> [pytest: TIMEOUT] Tests hung for >30s")
        results.append({
            "id": t_id,
            "name": t_name,
            "passed": False,
            "error": "pytest timeout (>30s)",
            "wall_time": res["wall_time"]
        })
    finally:
        if os.path.exists(code_path):
            os.remove(code_path)

with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n\n" + "=" * 80)
print("EXECUTABLE PYTEST BENCHMARK SUMMARY")
print("=" * 80)
header = "{:<6} | {:<30} | {:<8} | {:<8} | {:<10} | {:<35}".format("ID", "Task Name", "Status", "Time", "Decode", "Test Summary")
print(header)
print("-" * len(header))
passed_count = sum(1 for r in results if r.get("passed"))
for r in results:
    stat = "PASS" if r.get("passed") else "FAIL"
    print("{:<6} | {:<30} | {:<8} | {:<8} | {:<10} | {:<35}".format(
        r["id"],
        r["name"][:30],
        stat,
        f"{r.get('wall_time', 0)}s",
        f"{r.get('decode_tok_s', 0)} t/s",
        r.get("summary", "")[:35]
    ))

pass_rate = (passed_count / len(results) * 100) if results else 0
print("-" * len(header))
print(f"FINAL SCORE: {passed_count}/{len(results)} PASSED ({pass_rate:.1f}%)")
print(f"All logs saved to: {OUT_DIR}")
