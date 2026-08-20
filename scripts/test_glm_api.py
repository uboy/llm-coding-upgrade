import urllib.request
import json

KEY = "2e7bba03d2174dee9d92d8ed0b957a66.F4YvPOyIdpL6gu9H"
URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

models = ["glm-4-flash", "glm-4-air", "glm-5", "glm-5-turbo", "glm-4-plus"]

for m in models:
    payload = {
        "model": m,
        "messages": [{"role": "user", "content": "Ответь одним словом: GLM_OK"}],
        "max_tokens": 50
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {KEY}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[{m}] SUCCESS ->", data["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"[{m}] ERROR ->", e)
