#!/usr/bin/env python3
"""Benchmark an OpenAI-compatible server: TTFT + generation tok/s.
Usage: bench-ft.py <url> <seconds_limit> [prompt_file] [max_tokens]
"""
import json, sys, time, urllib.request

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:1919/v1/chat/completions"
prompt_file = sys.argv[3] if len(sys.argv) > 3 else None
max_tokens = int(sys.argv[4]) if len(sys.argv) > 4 else 256
if prompt_file:
    prompt = open(prompt_file, encoding="utf-8").read().strip()
else:
    prompt = ("Write a short essay about the impact of artificial intelligence on "
              "software development practices, covering productivity, risks, and "
              "what skills remain important for engineers.")

model_id = json.load(urllib.request.urlopen(url.replace("/chat/completions", "/models")))["data"][0]["id"]
body = json.dumps({
    "model": model_id, "max_tokens": max_tokens, "temperature": 0,
    "stream": True,
    "messages": [{"role": "user", "content": prompt}],
}).encode()
req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
t0 = time.time(); ttft = None; chunks = 0; text_len = 0
with urllib.request.urlopen(req, timeout=600) as r:
    for line in r:
        line = line.decode("utf-8", "replace").strip()
        if not line.startswith("data: "): continue
        payload = line[6:]
        if payload == "[DONE]": break
        d = json.loads(payload)
        delta = (d.get("choices") or [{}])[0].get("delta", {})
        c = (delta.get("content") or "") + (delta.get("reasoning_content") or "")
        if c:
            if ttft is None: ttft = time.time() - t0
            chunks += 1; text_len += len(c)
t_end = time.time()
gen_time = t_end - t0 - (ttft or 0)
print(json.dumps({
    "model": model_id, "prompt_chars": len(prompt), "max_tokens": max_tokens,
    "ttft_s": round(ttft or -1, 3), "total_s": round(t_end - t0, 3),
    "gen_chunks": chunks, "gen_time_s": round(gen_time, 3),
    "gen_tps_stream_chunks": round(chunks / gen_time, 2) if gen_time > 0 else None,
    "output_chars": text_len,
}))
