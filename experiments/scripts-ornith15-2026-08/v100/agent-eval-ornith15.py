#!/usr/bin/env python3
"""Agentic quality mini-eval (фаза 10 методика) для Ornith-1.5: 5 машинных проверок.
Отличия от scripts-bigmodel-2026-08/v100/agent-eval.py:
  - max_tokens 4000 (G-D3: reasoning-модель сжигает бюджет на think -> пустой content);
  - strip_think(): вынос <think>...</think> из content перед парсингом JSON/кода;
  - задачи T1-T5 идентичны - числа сравнимы с фазой 10 (Qwen Q4 5/5, Qwen Q6 5/5, gpt-oss 4/5).
Usage: agent-eval-ornith15.py <base_url_v1> <label> [max_tokens]
"""
import json, re, sys, time, urllib.request, ast

BASE = sys.argv[1].rstrip("/")
LABEL = sys.argv[2]
MAXTOK = int(sys.argv[3]) if len(sys.argv) > 3 else 4000

def strip_think(text):
    # llama.cpp может вернуть think инлайном в content (зависит от шаблона/reasoning-format)
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()

def chat(system, user, max_tokens=MAXTOK):
    body = json.dumps({"model": "x", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}],
        "max_tokens": max_tokens, "temperature": 0.6, "stream": False}).encode()
    req = urllib.request.Request(BASE + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=1800))
    m = d["choices"][0]["message"]
    content = strip_think(m.get("content") or "")
    reasoning = (m.get("reasoning_content") or "")
    return content, reasoning, d.get("usage", {}), time.time() - t0

def first_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

RESULTS = []
def record(task, ok, detail):
    RESULTS.append({"task": task, "label": LABEL, "pass": bool(ok), "detail": detail[:200]})
    print(json.dumps(RESULTS[-1], ensure_ascii=False), flush=True)

# T1: tool-call JSON discipline
c, r, u, dt = chat(
    "You are an agent that must answer ONLY with a JSON tool call, no prose. Tool schema: get_weather(location: string, unit: \"celsius\"|\"fahrenheit\"). Output format: {\"name\": \"...\", \"arguments\": {...}}",
    "What is the weather in Kazan right now? Use the tool.")
j = first_json(c)
t1 = bool(j) and j.get("name") == "get_weather" and isinstance(j.get("arguments", {}).get("location"), str) and len(j["arguments"]["location"]) > 0
record("T1_toolcall_json", t1, f"dt={dt:.0f}s usage={u.get('completion_tokens','?')}tok; {c[:120]}")

# T2: strict format extraction
c, r, u, dt = chat(
    "Extract data and answer ONLY with JSON with exactly keys city and temp_c. No other text.",
    "Weather report: Yesterday in Novosibirsk the thermometer showed minus 18 degrees Celsius at noon.")
j = first_json(c)
t2 = bool(j) and set(j.keys()) == {"city", "temp_c"} and "novosibirsk" in str(j.get("city", "")).lower()
record("T2_strict_json", t2, f"dt={dt:.0f}s; {c[:120]}")

# T3: bug fix by failing assert (code actually executed)
buggy = "def remove_duplicates(xs):\n    return list(set(xs))\n\n# requirement: preserve original order of first occurrences\nassert remove_duplicates([3,1,3,2,1]) == [3,1,2]\nassert remove_duplicates([]) == []\n"
c, r, u, dt = chat(
    "You are a coding agent. Fix the function so the asserts pass. Output ONLY the corrected Python function in a ```python code block, nothing else.",
    buggy)
m = re.search(r"```python\n(.*?)```", c, re.S) or re.search(r"```\n(.*?)```", c, re.S)
t3 = False; t3d = "no code block"
if m:
    code = m.group(1)
    try:
        ns = {}
        exec(code, ns)
        fn = ns.get("remove_duplicates")
        ok = fn([3,1,3,2,1]) == [3,1,2] and fn([]) == [] and fn(["a","b","a"]) == ["a","b"]
        t3 = ok; t3d = f"executed, asserts {'PASS' if ok else 'FAIL'}, dt={dt:.0f}s"
    except Exception as e:
        t3d = "exec error: " + str(e)[:80]
record("T3_bugfix_exec", t3, t3d)

# T4: multi-step plan JSON
c, r, u, dt = chat(
    "You are a coding agent. Produce ONLY a JSON array of steps. Each step is an object with keys: step (int), action (string), file (string). No prose.",
    "Task: add input validation with clear error messages to an existing CLI tool config.py and write tests in test_config.py.")
try:
    arr = json.loads(re.search(r"\[.*\]", c, re.S).group(0))
    t4 = isinstance(arr, list) and len(arr) >= 3 and all(isinstance(s.get("step"), int) and isinstance(s.get("action"), str) and isinstance(s.get("file"), str) for s in arr)
except Exception:
    arr = None; t4 = False
record("T4_plan_json", t4, ((str(len(arr)) + " steps") if arr else "unparseable") + f", dt={dt:.0f}s")

# T5: generation discipline (valid code, tests present, no degenerate loops)
c, r, u, dt = chat(
    "You are a coding agent. Write a Python function binary_search(a, x) returning the index or -1, with type hints and 4 unit tests using assert. Output ONLY the code block.",
    "Proceed.")
m = re.search(r"```python\n(.*?)```", c, re.S) or re.search(r"```\n(.*?)```", c, re.S)
t5 = False; t5d = "no code block"
if m:
    code = m.group(1)
    try:
        ast.parse(code)
        lines = [l.strip() for l in code.splitlines() if l.strip()]
        uniq = len(set(lines)) / max(1, len(lines))
        has_assert = "assert" in code
        ns = {}
        exec(code, ns)
        runs = ns.get("binary_search")([1,3,5,7], 5) == 2 and ns.get("binary_search")([1,3,5,7], 4) == -1
        t5 = has_assert and uniq > 0.6 and runs
        t5d = f"parse=OK asserts={has_assert} uniq_ratio={uniq:.2f} exec={runs} dt={dt:.0f}s"
    except Exception as e:
        t5d = "error: " + str(e)[:80]
record("T5_gen_discipline", t5, t5d)

score = sum(1 for x in RESULTS if x["pass"])
print(json.dumps({"label": LABEL, "score": f"{score}/{len(RESULTS)}"}, ensure_ascii=False), flush=True)
