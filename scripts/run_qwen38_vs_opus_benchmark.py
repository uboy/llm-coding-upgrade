import urllib.request
import urllib.error
import subprocess
import json
import time
import sys
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs", "qwen38_vs_opus_benchmark")
os.makedirs(OUT_DIR, exist_ok=True)

TASKS = [
    {
        "id": "Q01",
        "name": "LRU Cache с TTL и unit-тестами",
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
        "id": "H01",
        "name": "Thread-safe B-Tree с RWLock и снапшот-итератором",
        "difficulty": "hard",
        "prompt": "Реализуй thread-safe B-Tree на Python. Требования:\n\n1. Класс BTree(order: int) с методами:\n   - insert(key: int, value: Any)\n   - search(key: int) -> Optional[Any]\n   - delete(key: int) -> bool\n   - range_query(min_key: int, max_key: int) -> List[Tuple[int, Any]]\n   - items() -> Iterator[Tuple[int, Any]] — снапшот-итератор, консистентная копия на момент вызова\n\n2. Thread-safety:\n   - read-write lock (RWLock) — множественные читатели или один писатель\n   - range_query и items читают без блокировки записи (через копирование/снапшот)\n   - deadlock-free\n\n3. B-tree invariants:\n   - каждый узел: от order-1 до 2*order-1 ключей\n   - корень: от 1 до 2*order-1 ключей\n   - split при переполнении, merge при underflow\n\n4. Тесты: создание BTree(order=3), вставка 100 элементов, удаление 20, range_query и многопоточные тесты (10 читателей, 1 писатель)."
    },
    {
        "id": "H02",
        "name": "Secure Credential Manager (Crypto + Auto-lock)",
        "difficulty": "hard",
        "prompt": "Реализуй безопасный менеджер credentials на Python.\n\nТребования:\n1. Класс CredentialManager(master_password: str, db_path: str, lock_timeout: int = 300)\n   - add(service: str, username: str, password: str)\n   - get(service: str) -> Optional[Tuple[str, str]]\n   - delete(service: str) -> bool\n   - list_services() -> List[str]\n   - lock() — немедленная блокировка (очистка ключа из памяти)\n2. Хранение:\n   - файл SQLite с шифрованием каждого значения через Fernet (cryptography)\n   - master key: PBKDF2HMAC(sha256, salt, 600000 итераций) или Argon2id\n   - каждая запись: service_name (plaintext index), encrypted_blob (Fernet)\n3. Безопасность:\n   - auto-lock: после lock_timeout секунд бездействия ключ стирается из памяти\n   - secure wipe: перезапись ключа в памяти перед удалением\n   - file permissions: db_path должен иметь permission 0600\n4. Напиши юнит-тесты на корректное шифрование/расшифровку, auto-lock и отказ при неверном пароле."
    }
]

def query_qwen38(prompt, timeout=600):
    payload = {
        "model": "qwen38",
        "messages": [
            {"role": "system", "content": "Ты ведущий инженер-программист. Рассуждай глубоко и пиши полный, продакшн-код с обработкой всех edge-кейсов и тестами."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
        "max_tokens": 16384
    }
    req = urllib.request.Request(
        "http://v100-host:8022/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            wall = time.time() - start
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content", "") or ""
            reasoning = msg.get("reasoning_content", "") or ""
            finish_reason = choice.get("finish_reason", "")
            timings = data.get("timings", {})
            return {
                "success": True,
                "model": "Qwen3.8-27B (Q5_K_M)",
                "wall_time": round(wall, 2),
                "finish_reason": finish_reason,
                "decode_tok_s": round(timings.get("predicted_per_second", 0), 1),
                "think_len": len(reasoning),
                "code_len": len(content),
                "reasoning": reasoning,
                "content": content
            }
    except Exception as e:
        return {
            "success": False,
            "model": "Qwen3.8-27B (Q5_K_M)",
            "error": str(e),
            "wall_time": round(time.time() - start, 2),
            "finish_reason": "error",
            "decode_tok_s": 0,
            "think_len": 0,
            "code_len": 0,
            "reasoning": "",
            "content": ""
        }

def query_claude_opus(prompt, timeout=600):
    start = time.time()
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = os.environ.get("CLAUDE_CONFIG_DIR", os.path.join(os.path.expanduser("~"), ".claude"))
    
    cmd = [
        "claude.exe", "-p",
        "--model", "opus",
        prompt
    ]
    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=""
        )
        wall = time.time() - start
        out = proc.stdout
        err = proc.stderr
        if proc.returncode == 0 and len(out) > 0:
            return {
                "success": True,
                "model": "Claude Opus (work3)",
                "wall_time": round(wall, 2),
                "finish_reason": "stop",
                "decode_tok_s": 0,
                "think_len": 0,
                "code_len": len(out),
                "reasoning": "",
                "content": out
            }
        else:
            return {
                "success": False,
                "model": "Claude Opus (work3)",
                "error": err[:300] if err else f"return code {proc.returncode}",
                "wall_time": round(wall, 2),
                "finish_reason": "error",
                "decode_tok_s": 0,
                "think_len": 0,
                "code_len": 0,
                "reasoning": "",
                "content": ""
            }
    except Exception as e:
        return {
            "success": False,
            "model": "Claude Opus (work3)",
            "error": str(e),
            "wall_time": round(time.time() - start, 2),
            "finish_reason": "error",
            "decode_tok_s": 0,
            "think_len": 0,
            "code_len": 0,
            "reasoning": "",
            "content": ""
        }

print("=" * 80)
print("STARTING ADVANCED BENCHMARK: QWEN3.8-27B (Q5_K_M) vs CLAUDE OPUS (work3)")
print("=" * 80)

results = []

for task in TASKS:
    t_id = task["id"]
    t_name = task["name"]
    t_prompt = task["prompt"]
    
    print(f"\n=======================================================")
    print(f"[{t_id}] {t_name} ({task['difficulty']})")
    print(f"=======================================================")
    
    task_res = {
        "id": t_id,
        "name": t_name,
        "difficulty": task["difficulty"],
        "qwen38": {},
        "opus": {}
    }
    
    # 1. Qwen3.8 (Q5_K_M, Full Thinking)
    print("  -> Running on Qwen3.8-27B (Q5_K_M, Local V100, Thinking=ON)...")
    res_qwen = query_qwen38(t_prompt, timeout=600)
    task_res["qwen38"] = res_qwen
    print(f"     [Qwen3.8] Wall: {res_qwen['wall_time']}s | Decode: {res_qwen['decode_tok_s']} t/s | Think: {res_qwen['think_len']} ch | Code: {res_qwen['code_len']} ch | Status: {res_qwen['finish_reason']}")
    
    # 2. Claude Opus (profile work3)
    print("  -> Running on Claude Opus (Profile work3)...")
    res_opus = query_claude_opus(t_prompt, timeout=600)
    task_res["opus"] = res_opus
    print(f"     [Opus]    Wall: {res_opus['wall_time']}s | Code: {res_opus['code_len']} ch | Status: {res_opus['finish_reason']}")
    
    # Save markdown outputs
    with open(os.path.join(OUT_DIR, f"{t_id}_Qwen38.md"), "w", encoding="utf-8") as f:
        f.write(f"# Task {t_id}: {t_name} (Qwen3.8-27B Q5_K_M)\n\n")
        f.write(f"Wall time: {res_qwen['wall_time']}s | Decode: {res_qwen['decode_tok_s']} tok/s\n\n")
        f.write(f"## Reasoning:\n```\n{res_qwen['reasoning']}\n```\n\n")
        f.write(f"## Code Content:\n{res_qwen['content']}\n")
        
    with open(os.path.join(OUT_DIR, f"{t_id}_Opus.md"), "w", encoding="utf-8") as f:
        f.write(f"# Task {t_id}: {t_name} (Claude Opus work3)\n\n")
        f.write(f"Wall time: {res_opus['wall_time']}s\n\n")
        f.write(f"## Code Content:\n{res_opus['content']}\n")

    results.append(task_res)

with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n\n" + "=" * 80)
print("BENCHMARK SUMMARY TABLE")
print("=" * 80)
header = "{:<6} | {:<8} | {:<25} | {:<25}".format("Task", "Diff", "Qwen3.8 (Q5_K_M)", "Claude Opus (work3)")
print(header)
print("-" * len(header))
for r in results:
    q = r["qwen38"]
    o = r["opus"]
    q_str = f"{q.get('finish_reason','err')} ({q.get('code_len',0)}ch, {q.get('wall_time',0)}s)"
    o_str = f"{o.get('finish_reason','err')} ({o.get('code_len',0)}ch, {o.get('wall_time',0)}s)"
    print("{:<6} | {:<8} | {:<25} | {:<25}".format(r["id"], r["difficulty"], q_str, o_str))

print(f"\nAll outputs saved to {OUT_DIR}")
