import json, re, urllib.request, sys
url = sys.argv[1]
ok = 0
for i in range(5):
    body = json.dumps({"model":"x","messages":[
     {"role":"system","content":"You are a coding agent. Produce ONLY a JSON array of steps. Each step is an object with keys: step (int), action (string), file (string). No prose."},
     {"role":"user","content":"Task: add input validation with clear error messages to an existing CLI tool config.py and write tests in test_config.py."}],
     "max_tokens":2000,"temperature":0.6,"stream":False}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=900))
    c = d["choices"][0]["message"].get("content") or ""
    m = re.search(r"\[.*\]", c, re.S)
    good = False
    if m:
        try:
            arr = json.loads(m.group(0))
            good = isinstance(arr, list) and len(arr) >= 3 and all(isinstance(s.get("step"), int) for s in arr)
        except Exception:
            pass
    ok += bool(good)
    print("run%d: parse=%s head=%r" % (i+1, "OK" if good else "FAIL", c[:50]))
print("T4 stability: %d/5" % ok)
