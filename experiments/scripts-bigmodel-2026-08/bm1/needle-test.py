#!/usr/bin/env python3
"""Needle test: fact at start, filler, question. Usage: needle-test.py <url> <mode: pos|neg> [ctx_tokens_target]"""
import json, sys, time, urllib.request

url = sys.argv[1].rstrip("/") + "/completion"
mode = sys.argv[2] if len(sys.argv) > 2 else "pos"
target = int(sys.argv[3]) if len(sys.argv) > 3 else 65536

paras = [
 "The quarterly infrastructure review covered rack allocations, cooling curves, firmware versions for the redundant power controllers, and the migration schedule for the legacy inventory database. Engineers presented latency histograms and capacity forecasts for the next three fiscal quarters. ",
 "Vendor negotiations with the storage supplier progressed through pricing tiers, support response commitments, and spare part logistics for the eastern warehouse. The legal team reviewed liability clauses while finance modeled depreciation across five year horizons. ",
 "Network telemetry from the border routers showed periodic congestion during evening peaks, correlated with backup jobs and replication traffic between the primary and secondary sites. QoS policies were adjusted after the packet loss incident on link seven. ",
 "Application teams migrated legacy services to the new runtime gradually, canarying each release through staging and shadow traffic. Error budgets, alert thresholds, and rollback playbooks were revised following the postmortem of the March outage. ",
 "Security audits covered credential rotation schedules, least privilege enforcement in the deploy pipeline, and anomaly detection rules for unusual administrative logins from new geographic regions. Two findings were closed, one remains open. ",
 "Capacity planning for the database cluster involved sharding proposals, replica lag measurements under synthetic load, and storage headroom projections. The committee deferred the hardware refresh until quarterly results arrive. ",
]
import itertools
def build_filler(tokens):
    out = []
    cnt = 0
    for i in itertools.count():
        p = paras[i % len(paras)]
        out.append(p); cnt += len(p) // 4
        if cnt >= tokens: break
    return "".join(out), cnt
filler, approx = build_filler(target)
secret = "The secret access code for the build server is ZX9-4471-QQ."
if mode == "pos":
    prompt = (secret + "\n\n" + filler +
              "\n\nQuestion: What is the secret access code for the build server? Give only the code.\nAnswer:")
else:
    prompt = (filler +
              "\n\nQuestion: What is the secret access code for the build server? Give only the code.\nAnswer:")
body = json.dumps({"prompt": prompt, "n_predict": 256, "temperature": 0, "cache_prompt": False}).encode()
req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
t0 = time.time()
resp = json.load(urllib.request.urlopen(req, timeout=1200))
dt = time.time() - t0
text = resp.get("content", "")
found = "ZX9-4471-QQ" in text
print(json.dumps({"mode": mode, "prompt_chars": len(prompt), "est_tokens": approx,
                  "wall_s": round(dt, 1), "found_secret": found, "answer": text.strip()[:120]}))
