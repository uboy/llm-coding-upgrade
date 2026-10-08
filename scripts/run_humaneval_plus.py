import evalplus.data
import subprocess
import urllib.request
import urllib.error
import json
import time
import re
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJECT_ROOT, "runs/humaneval_plus_benchmark")
os.makedirs(OUT_DIR, exist_ok=True)

ENDPOINT = "http://v100-host:8022/v1/chat/completions"

# Load HumanEval+ (164 tasks)
dataset = evalplus.data.get_human_eval_plus()
task_ids = list(dataset.keys())

# Select 20 representative tasks (every 8th task across the entire spectrum)
sampled_ids = task_ids[::8]  # 21 tasks spanning easy, medium, and hard algorithms

def extract_code(prompt, text, entry_point):
    # If standard markdown python block
    matches = re.findall(r"```(?:python|py)?\n(.*?)```", text, re.DOTALL)
    code = ""
    if matches:
        code = max(matches, key=len).strip()
    else:
        # Strip backticks
        lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
        code = "\n".join(lines).strip()
        
    # If code doesn't define the entry_point, fallback
    if f"def {entry_point}" not in code:
        code = prompt + "\n" + code
    return code

def query_qwen38(prompt_text):
    payload = {
        "model": "qwen38",
        "messages": [
            {"role": "system", "content": "You are an expert Python developer. Complete the function according to the docstring. Return ONLY valid Python code in a ```python ... ``` block."},
            {"role": "user", "content": f"Complete this Python function:\n\n```python\n{prompt_text}\n```"}
        ],
        "temperature": 0.0,
        "max_tokens": 1024
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            wall = time.time() - start
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            return {"success": True, "wall": round(wall, 2), "content": content}
    except Exception as e:
        return {"success": False, "wall": round(time.time() - start, 2), "error": str(e)}

def query_opus(prompt_text):
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = os.environ.get("CLAUDE_CONFIG_DIR", os.path.join(os.path.expanduser("~"), ".claude"))
    cmd = [
        "claude.exe", "-p",
        "--model", "opus",
        f"Complete this Python function. Return ONLY valid Python code in a ```python ... ``` block:\n\n{prompt_text}"
    ]
    start = time.time()
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=90, input="")
        wall = time.time() - start
        if proc.returncode == 0 and len(proc.stdout) > 0:
            return {"success": True, "wall": round(wall, 2), "content": proc.stdout}
        return {"success": False, "wall": round(wall, 2), "error": proc.stderr[:200]}
    except Exception as e:
        return {"success": False, "wall": round(time.time() - start, 2), "error": str(e)}

def execute_test(code, test_code, entry_point):
    full_script = f"{code}\n\n{test_code}\n\ncheck({entry_point})\n"
    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", full_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        passed = (proc.returncode == 0)
        return {"passed": passed, "err": proc.stderr.strip()[:200] if not passed else ""}
    except subprocess.TimeoutExpired:
        return {"passed": False, "err": "Execution timeout (>10s)"}
    except Exception as e:
        return {"passed": False, "err": str(e)}

print("=" * 80)
print(f"STARTING EXTERNAL BENCHMARK: HumanEval+ (EvalPlus 164 Suite, Sampled {len(sampled_ids)} Tasks)")
print(f"Contenders: Qwen3.8-27B (Fast Mode, V100) vs Claude Opus (work3)")
print("=" * 80)

qwen_results = []
opus_results = []

for idx, tid in enumerate(sampled_ids, 1):
    task = dataset[tid]
    prompt_text = task["prompt"]
    entry_point = task["entry_point"]
    test_code = task["test"]
    
    print(f"\n[{idx}/{len(sampled_ids)}] {tid} (entry: {entry_point})...")
    
    # 1. Test Qwen3.8
    q_res = query_qwen38(prompt_text)
    if q_res["success"]:
        q_code = extract_code(prompt_text, q_res["content"], entry_point)
        q_test = execute_test(q_code, test_code, entry_point)
        stat = "PASS" if q_test["passed"] else "FAIL"
        print(f"  -> [Qwen3.8] {stat} ({q_res['wall']}s) {q_test.get('err', '')[:60]}")
        qwen_results.append({"tid": tid, "passed": q_test["passed"], "wall": q_res["wall"], "err": q_test.get("err")})
    else:
        print(f"  -> [Qwen3.8] ERROR: {q_res.get('error')}")
        qwen_results.append({"tid": tid, "passed": False, "wall": q_res["wall"], "err": q_res.get("error")})
        
    # 2. Test Claude Opus
    o_res = query_opus(prompt_text)
    if o_res["success"]:
        o_code = extract_code(prompt_text, o_res["content"], entry_point)
        o_test = execute_test(o_code, test_code, entry_point)
        stat = "PASS" if o_test["passed"] else "FAIL"
        print(f"  -> [Opus]    {stat} ({o_res['wall']}s) {o_test.get('err', '')[:60]}")
        opus_results.append({"tid": tid, "passed": o_test["passed"], "wall": o_res["wall"], "err": o_test.get("err")})
    else:
        print(f"  -> [Opus]    ERROR: {o_res.get('error')}")
        opus_results.append({"tid": tid, "passed": False, "wall": o_res["wall"], "err": o_res.get("error")})

with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
    json.dump({"qwen38": qwen_results, "opus": opus_results}, f, indent=2, ensure_ascii=False)

print("\n\n" + "=" * 80)
print("HUMANEVAL+ (EVALPLUS) BENCHMARK SUMMARY")
print("=" * 80)
header = "{:<16} | {:<12} | {:<8} | {:<12} | {:<8}".format("Task ID", "Qwen3.8", "Time", "Claude Opus", "Time")
print(header)
print("-" * len(header))
for q, o in zip(qwen_results, opus_results):
    q_stat = "PASS" if q["passed"] else "FAIL"
    o_stat = "PASS" if o["passed"] else "FAIL"
    print("{:<16} | {:<12} | {:<8} | {:<12} | {:<8}".format(
        q["tid"],
        q_stat,
        f"{q['wall']}s",
        o_stat,
        f"{o['wall']}s"
    ))

q_pass = sum(1 for q in qwen_results if q["passed"])
o_pass = sum(1 for o in opus_results if o["passed"])
q_pct = (q_pass / len(qwen_results) * 100) if qwen_results else 0
o_pct = (o_pass / len(opus_results) * 100) if opus_results else 0

print("-" * len(header))
print(f"QWEN3.8-27B (Fast Mode, V100): {q_pass}/{len(qwen_results)} PASSED ({q_pct:.1f}%)")
print(f"CLAUDE OPUS (work3, Anthropic): {o_pass}/{len(opus_results)} PASSED ({o_pct:.1f}%)")
print(f"Results saved to: {OUT_DIR}")
