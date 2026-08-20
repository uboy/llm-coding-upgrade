import urllib.request
import urllib.error
import json
import time
import sys
import os

SUITE_PATH = "/data/home/<user>/proj/llm-coding-upgrade/evals/benchmark-suite.json"
OUT_DIR = "/data/home/<user>/runs/qwen38_vs_qwen36_benchmark"
os.makedirs(OUT_DIR, exist_ok=True)

with open(SUITE_PATH, "r", encoding="utf-8") as f:
    suite = json.load(f)

tasks = suite.get("tasks", [])

MODELS = [
    {
        "id": "qwen36",
        "name": "Qwen3.6-27B-Heretic (Q4_K_M)",
        "port": 8021,
        "max_tokens": 4096,
        "temp": 0.6
    },
    {
        "id": "qwen38",
        "name": "Qwen3.8-27B (Q4_K_M)",
        "port": 8022,
        "max_tokens": 4096,
        "temp": 0.6
    }
]

def query_model(port, prompt, max_tokens=4096, temp=0.6, timeout=180):
    payload = {
        "model": "model",
        "messages": [
            {"role": "system", "content": "Ты опытный инженер-программист. Рассуждай точно и пиши полный, готовый к продакшну рабочий код."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temp,
        "max_tokens": max_tokens
    }
    req = urllib.request.Request(
        f"http://localhost:{port}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            wall_time = time.time() - start
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content", "") or ""
            reasoning = msg.get("reasoning_content", "") or ""
            finish_reason = choice.get("finish_reason", "")
            timings = data.get("timings", {})
            usage = data.get("usage", {})
            
            return {
                "success": True,
                "wall_time": round(wall_time, 2),
                "content": content,
                "reasoning": reasoning,
                "content_len": len(content),
                "reasoning_len": len(reasoning),
                "finish_reason": finish_reason,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "prompt_tok_s": round(timings.get("prompt_per_second", 0), 1),
                "decode_tok_s": round(timings.get("predicted_per_second", 0), 1)
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "wall_time": round(time.time() - start, 2),
            "content": "",
            "reasoning": "",
            "content_len": 0,
            "reasoning_len": 0,
            "finish_reason": "error",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "prompt_tok_s": 0,
            "decode_tok_s": 0
        }

print(f"Starting comparison benchmark on {len(tasks)} tasks...")
all_results = []

for task in tasks:
    t_id = task["id"]
    t_name = task["name"]
    t_prompt = task["prompt"]
    expected_kw = task.get("expected_keywords", [])
    
    print("\n" + "=" * 55)
    print(f"[{t_id}] {t_name}")
    print("=" * 55)
    
    task_res = {
        "id": t_id,
        "name": t_name,
        "difficulty": task.get("difficulty", ""),
        "category": task.get("category", ""),
        "models": {}
    }
    
    for m in MODELS:
        m_id = m["id"]
        m_name = m["name"]
        m_port = m["port"]
        print(f"  -> Running on {m_name} (port {m_port})...")
        res = query_model(m_port, t_prompt, max_tokens=m["max_tokens"], temp=m["temp"])
        
        full_text = (res["content"] + " " + res["reasoning"]).lower()
        matched_kw = [kw for kw in expected_kw if kw.lower() in full_text]
        kw_score = f"{len(matched_kw)}/{len(expected_kw)}"
        res["matched_keywords"] = matched_kw
        res["kw_score"] = kw_score
        
        if not res["success"]:
            status = "ERROR"
        elif res["content_len"] == 0 and res["reasoning_len"] > 0:
            status = "OVERFLOW"
        elif res["content_len"] < 200:
            status = "PARTIAL"
        else:
            status = "OK"
        res["status"] = status
        
        print(f"     [{status}] Wall: {res['wall_time']}s | PP: {res['prompt_tok_s']} t/s | Decode: {res['decode_tok_s']} t/s | Code: {res['content_len']} ch | Think: {res['reasoning_len']} ch | KW: {kw_score}")
        
        task_res["models"][m_id] = res
        
        with open(os.path.join(OUT_DIR, f"{t_id}_{m_id}.md"), "w", encoding="utf-8") as f_out:
            f_out.write(f"# Task {t_id}: {t_name} ({m_name})\n\n")
            f_out.write(f"## Status: {status} | Wall: {res['wall_time']}s | Decode: {res['decode_tok_s']} tok/s\n\n")
            f_out.write(f"### Reasoning:\n```\n{res['reasoning']}\n```\n\n")
            f_out.write(f"### Code Content:\n{res['content']}\n")

    all_results.append(task_res)

summary_json_path = os.path.join(OUT_DIR, "summary.json")
with open(summary_json_path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print("\n\n" + "=" * 80)
print("BENCHMARK SUMMARY")
print("=" * 80)
header = "{:<6} | {:<8} | {:<22} | {:<12} | {:<22} | {:<12}".format("Task", "Diff", "Q3.6 Status", "Q3.6 Decode", "Q3.8 Status", "Q3.8 Decode")
print(header)
print("-" * len(header))

for r in all_results:
    m36 = r["models"].get("qwen36", {})
    m38 = r["models"].get("qwen38", {})
    s36 = f"{m36.get('status', 'N/A')} ({m36.get('content_len', 0)} ch)"
    s38 = f"{m38.get('status', 'N/A')} ({m38.get('content_len', 0)} ch)"
    d36 = f"{m36.get('decode_tok_s', 0)} t/s"
    d38 = f"{m38.get('decode_tok_s', 0)} t/s"
    print("{:<6} | {:<8} | {:<22} | {:<12} | {:<22} | {:<12}".format(r['id'], r['difficulty'], s36, d36, s38, d38))

print(f"\nAll results saved to {OUT_DIR}")
