import urllib.request
import urllib.error
import json
import time
import subprocess
import sys
import os

OUT_DIR = "/data/home/<user>/runs/qwen38_vs_qwen36_3scenarios"
os.makedirs(OUT_DIR, exist_ok=True)

TASKS = [
    {
        "id": "Q01",
        "name": "LRU Cache с TTL",
        "difficulty": "hard",
        "prompt": "Реализуй класс LRU кэша с поддержкой TTL (time-to-live) на Python. Класс должен быть thread-safe. Интерфейс: get(key), put(key, value, ttl_seconds), delete(key). При превышении capacity удаляется LRU элемент. При истечении TTL элемент считается отсутствующим. Напиши также полный набор unit-тестов."
    },
    {
        "id": "Q02",
        "name": "Bug fix: race condition",
        "difficulty": "medium",
        "prompt": "Найди и исправь все race conditions в следующем коде:\n\nclass Counter:\n    def __init__(self):\n        self.value = 0\n        self.history = []\n\n    def increment(self):\n        current = self.value\n        self.value = current + 1\n        self.history.append(self.value)\n\n    def get_and_reset(self):\n        val = self.value\n        self.value = 0\n        self.history.clear()\n        return val\n\nimport threading\nc = Counter()\nthreads = [threading.Thread(target=lambda: [c.increment() for _ in range(1000)]) for _ in range(10)]\nfor t in threads: t.start()\nfor t in threads: t.join()\nprint(c.value, len(c.history))\n\nПокажи исправленную версию и объясни каждую найденную проблему."
    },
    {
        "id": "Q03",
        "name": "Sliding window rate limiter",
        "difficulty": "medium",
        "prompt": "Реализуй sliding window rate limiter на Python. Класс RateLimiter с методом allow_request(user_id) -> bool. Параметры: max_requests=100, window_seconds=60. Используй sliding window (не fixed window). Каждый user_id имеет отдельный лимит. Реализация должна быть O(1) по памяти на request (храним только timestamp'ы внутри окна). Покажи пример использования и тест."
    },
    {
        "id": "Q04",
        "name": "Async producer-consumer",
        "difficulty": "hard",
        "prompt": "Реализуй async producer-consumer очередь на Python с asyncio. Класс AsyncQueue с методами: async put(item), async get() -> item, task_done(), join(). Поддержка maxsize (bounded queue). Метод put блокируется при полной очереди, get — при пустой. Также добавь graceful shutdown: метод close() и __aenter__/__aexit__. Напиши пример с 3 producers и 2 consumers."
    },
    {
        "id": "Q06",
        "name": "Code review: найти баги",
        "difficulty": "medium",
        "prompt": "Найди ВСЕ баги в этом коде:\n\ndef merge_dicts(*dicts):\n    result = {}\n    for d in dicts:\n        result.update(d)\n    return result\n\ndef flatten(lst):\n    return [item for sublist in lst for item in sublist]\n\ndef safe_divide(a, b=0):\n    return a / b if b != 0 else float('inf')\n\nclass Singleton:\n    _instance = None\n    def __new__(cls):\n        if cls._instance is None:\n            cls._instance = super().__new__(cls)\n        return cls._instance\n    def __init__(self):\n        self.data = []\n\ndef retry(func, max_retries=3):\n    for i in range(max_retries):\n        try:\n            return func()\n        except Exception:\n            continue\n    return None\n\nДля каждого бага: укажи строку, опиши проблему, покажи исправление."
    }
]

def run_cmd(cmd_list):
    res = subprocess.run(cmd_list, capture_output=True, text=True)
    return res

def wait_healthy(port, timeout=90):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"http://localhost:{port}/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    d = json.loads(resp.read().decode())
                    if d.get("status") == "ok":
                        return True
        except Exception:
            pass
        time.sleep(2)
    return False

def restart_containers(reasoning_mode_36=True, reasoning_mode_38=True):
    print(f"\n[CONFIG] Setting Qwen3.6 reasoning={reasoning_mode_36}, Qwen3.8 reasoning={reasoning_mode_38}...")
    
    # Qwen3.6 on GPU 2, port 8021
    run_cmd(["docker", "stop", "llamacpp-qwen36-heretic"])
    run_cmd(["docker", "rm", "llamacpp-qwen36-heretic"])
    
    r_flag_36 = ["--reasoning", "on"] if reasoning_mode_36 else ["--reasoning", "off"]
    cmd_36 = [
        "docker", "run", "-d",
        "--name", "llamacpp-qwen36-heretic",
        "--restart", "unless-stopped",
        "--gpus", "device=2",
        "-p", "8021:8080",
        "-v", "/data/shared/<user>/models:/models:ro",
        "ghcr.io/ggml-org/llama.cpp:server-cuda",
        "-m", "/models/Qwen3.6-27B-Heretic/Qwen3.6-27B-Heretic-Q4_K_M.gguf",
        "--host", "0.0.0.0",
        "--port", "8080",
        "-ngl", "100",
        "--ctx-size", "32768",
        "--batch-size", "1024",
        "--ubatch-size", "256",
        "--parallel", "1",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--jinja"
    ] + r_flag_36 + [
        "--temp", "0.6",
        "--top-p", "0.95",
        "--top-k", "20",
        "--min-p", "0.0",
        "--repeat-penalty", "1.0"
    ]
    run_cmd(cmd_36)
    
    # Qwen3.8 on GPU 1, port 8022
    run_cmd(["docker", "stop", "llamacpp-qwen38-27b"])
    run_cmd(["docker", "rm", "llamacpp-qwen38-27b"])
    
    r_flag_38 = ["--reasoning", "on"] if reasoning_mode_38 else ["--reasoning", "off"]
    cmd_38 = [
        "docker", "run", "-d",
        "--name", "llamacpp-qwen38-27b",
        "--restart", "unless-stopped",
        "--gpus", "device=1",
        "-p", "8022:8080",
        "-v", "/data/shared/<user>/models:/models:ro",
        "ghcr.io/ggml-org/llama.cpp:server-cuda",
        "-m", "/models/Qwen3.8-27B-GGUF/Qwen3.8-27B-Q4_K_M.gguf",
        "--host", "0.0.0.0",
        "--port", "8080",
        "-ngl", "100",
        "--ctx-size", "196608",
        "--batch-size", "1024",
        "--ubatch-size", "2048",
        "--parallel", "1",
        "--cache-type-k", "q4_0",
        "--cache-type-v", "q4_0",
        "--jinja"
    ] + r_flag_38 + [
        "--temp", "0.6",
        "--top-p", "0.95",
        "--top-k", "20",
        "--min-p", "0.0",
        "--repeat-penalty", "1.0"
    ]
    run_cmd(cmd_38)
    
    ok36 = wait_healthy(8021, 90)
    ok38 = wait_healthy(8022, 90)
    print(f"  -> Qwen3.6 (:8021) ready: {ok36}, Qwen3.8 (:8022) ready: {ok38}")
    return ok36 and ok38

def query_chat(port, prompt, sys_prompt, max_tokens, timeout=240):
    payload = {
        "model": "model",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
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
            d = json.loads(resp.read().decode("utf-8"))
            wall = time.time() - start
            choice = d["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content", "") or ""
            reasoning = msg.get("reasoning_content", "") or ""
            timings = d.get("timings", {})
            return {
                "success": True,
                "finish_reason": choice.get("finish_reason", ""),
                "wall_time": round(wall, 2),
                "content_len": len(content),
                "reasoning_len": len(reasoning),
                "decode_tok_s": round(timings.get("predicted_per_second", 0), 1),
                "pp_tok_s": round(timings.get("prompt_per_second", 0), 1),
                "content": content,
                "reasoning": reasoning
            }
    except Exception as e:
        return {
            "success": False,
            "finish_reason": "error",
            "error": str(e),
            "wall_time": round(time.time() - start, 2),
            "content_len": 0,
            "reasoning_len": 0,
            "decode_tok_s": 0,
            "pp_tok_s": 0,
            "content": "",
            "reasoning": ""
        }

all_scenarios_results = {}

# ==============================================================================
# СЦЕНАРИЙ 1: Reasoning OFF на обоих моделях (Fast / Raw Mode)
# ==============================================================================
print("\n" + "=" * 70)
print(">>> СЦЕНАРИЙ 1: Reasoning OFF на обеих моделях (Fast Mode)")
print("=" * 70)
restart_containers(reasoning_mode_36=False, reasoning_mode_38=False)

s1_results = []
sys_std = "Ты опытный инженер-программист. Пиши чистый, надежный и полный код."

for t in TASKS:
    t_id = t["id"]
    t_name = t["name"]
    print(f"\n--- [{t_id}] {t_name} ---")
    
    r36 = query_chat(8021, t["prompt"], sys_std, max_tokens=4096)
    print(f"  Qwen3.6 (No Think): Wall {r36['wall_time']}s | Decode {r36['decode_tok_s']} t/s | Code {r36['content_len']} ch | Finish: {r36['finish_reason']}")
    
    r38 = query_chat(8022, t["prompt"], sys_std, max_tokens=4096)
    print(f"  Qwen3.8 (No Think): Wall {r38['wall_time']}s | Decode {r38['decode_tok_s']} t/s | Code {r38['content_len']} ch | Finish: {r38['finish_reason']}")
    
    s1_results.append({
        "id": t_id,
        "name": t_name,
        "qwen36": r36,
        "qwen38": r38
    })

all_scenarios_results["scenario_1_no_reasoning"] = s1_results

# ==============================================================================
# СЦЕНАРИЙ 2: Рекомендованный бюджет на размышления (Full Thinking)
# ==============================================================================
print("\n" + "=" * 70)
print(">>> СЦЕНАРИЙ 2: Рекомендованный бюджет Thinking (Q3.6: 8k, Q3.8: 16k)")
print("=" * 70)
restart_containers(reasoning_mode_36=True, reasoning_mode_38=True)

s2_results = []
for t in TASKS:
    t_id = t["id"]
    t_name = t["name"]
    print(f"\n--- [{t_id}] {t_name} ---")
    
    r36 = query_chat(8021, t["prompt"], sys_std, max_tokens=8192)
    print(f"  Qwen3.6 (Full Think): Wall {r36['wall_time']}s | Decode {r36['decode_tok_s']} t/s | Think {r36['reasoning_len']} ch | Code {r36['content_len']} ch | Finish: {r36['finish_reason']}")
    
    r38 = query_chat(8022, t["prompt"], sys_std, max_tokens=16384)
    print(f"  Qwen3.8 (Full Think): Wall {r38['wall_time']}s | Decode {r38['decode_tok_s']} t/s | Think {r38['reasoning_len']} ch | Code {r38['content_len']} ch | Finish: {r38['finish_reason']}")
    
    s2_results.append({
        "id": t_id,
        "name": t_name,
        "qwen36": r36,
        "qwen38": r38
    })

all_scenarios_results["scenario_2_full_thinking"] = s2_results

# ==============================================================================
# СЦЕНАРИЙ 3: Системный промпт для ограничения глубины 3.8 под бюджет 3.6
# ==============================================================================
print("\n" + "=" * 70)
print(">>> СЦЕНАРИЙ 3: Ограничение глубины 3.8 системным промптом (Бюджет 8k)")
print("=" * 70)

s3_results = []
sys_constrained = "Ты опытный инженер-программист. Рассуждай предельно кратко (не более 200-300 слов) и сразу пиши полный рабочий код."

for t in TASKS:
    t_id = t["id"]
    t_name = t["name"]
    print(f"\n--- [{t_id}] {t_name} ---")
    
    r36 = query_chat(8021, t["prompt"], sys_std, max_tokens=8192)
    print(f"  Qwen3.6 (Baseline): Wall {r36['wall_time']}s | Think {r36['reasoning_len']} ch | Code {r36['content_len']} ch")
    
    r38 = query_chat(8022, t["prompt"], sys_constrained, max_tokens=8192)
    print(f"  Qwen3.8 (Constrained): Wall {r38['wall_time']}s | Think {r38['reasoning_len']} ch | Code {r38['content_len']} ch")
    
    s3_results.append({
        "id": t_id,
        "name": t_name,
        "qwen36": r36,
        "qwen38": r38
    })

all_scenarios_results["scenario_3_constrained_thinking"] = s3_results

with open(os.path.join(OUT_DIR, "all_scenarios_summary.json"), "w", encoding="utf-8") as f:
    json.dump(all_scenarios_results, f, indent=2, ensure_ascii=False)

print("\n\n" + "=" * 80)
print("ALL 3 SCENARIOS COMPLETED SUCCESSFULLY!")
print("=" * 80)
