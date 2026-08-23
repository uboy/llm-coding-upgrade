#!/usr/bin/env python3
"""Needle-style long-ctx test against OpenAI chat API (FreeToken). Usage: needle-ft.py <url> <pos|neg> <ctx>"""
import json, sys, time, urllib.request
url = sys.argv[1].rstrip("/") + "/chat/completions"
mode = sys.argv[2] if len(sys.argv) > 2 else "pos"
target = int(sys.argv[3]) if len(sys.argv) > 3 else 131072
paras = [
 "The quarterly infrastructure review covered rack allocations, cooling curves, firmware versions for the redundant power controllers, and the migration schedule for the legacy inventory database. Engineers presented latency histograms and capacity forecasts for the next three fiscal quarters. ",
 "Vendor negotiations with the storage supplier progressed through pricing tiers, support response commitments, and spare part logistics for the eastern warehouse. The legal team reviewed liability clauses while finance modeled depreciation across five year horizons. ",
 "Network telemetry from the border routers showed periodic congestion during evening peaks, correlated with backup jobs and replication traffic between the primary and secondary sites. QoS policies were adjusted after the packet loss incident on link seven. ",
 "Application teams migrated legacy services to the new runtime gradually, canarying each release through staging and shadow traffic. Error budgets, alert thresholds, and rollback playbooks were revised following the postmortem of the March outage. ",
 "Security audits covered credential rotation schedules, least privilege enforcement in the deploy pipeline, and anomaly detection rules for unusual administrative logins from new geographic regions. Two findings were closed, one remains open. ",
 "Capacity planning for the database cluster involved sharding proposals, replica lag measurements under synthetic load, and storage headroom projections. The committee deferred the hardware refresh until quarterly results arrive. ",
]
out, cnt = [], 0
i = 0
while cnt < target:
    p = paras[i % len(paras)]; out.append(p); cnt += len(p) // 4; i += 1
filler = "".join(out)
secret = "The secret access code for the build server is ZX9-4471-QQ."
q = "What is the secret access code for the build server mentioned at the very beginning? Give only the code."
content = (secret + "\n\n" + filler + "\n\n" + q) if mode == "pos" else (filler + "\n\n" + q)
model_id = json.load(urllib.request.urlopen(url.replace("/chat/completions", "/models")))["data"][0]["id"]
body = json.dumps({"model": model_id, "messages": [{"role": "user", "content": content}], "max_tokens": 512, "temperature": 0, "stream": True}).encode()
req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
t0 = time.time()
chunks, text, ttft = 0, "", None
with urllib.request.urlopen(req, timeout=3600) as r:
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
            chunks += 1; text += c
dt = time.time() - t0
gen = dt - (ttft or 0)
print(json.dumps({"mode": mode, "est_tokens": cnt, "wall_s": round(dt,1), "ttft_s": round(ttft or -1,2),
  "gen_chunks": chunks, "gen_tps": round(chunks/gen,2) if gen > 0 else None, "found_secret": "ZX9-4471-QQ" in text,
  "answer_head": text.strip()[:100]}))
