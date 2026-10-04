#!/usr/bin/env python3
"""IFEval generator: send google-research/instruction_following_eval prompts to an
OpenAI-compatible endpoint and write the response jsonl their evaluation_main.py expects.

Usage (from llm-coding-upgrade repo):
  python3 scripts/run_ifeval_api.py \
    --base-url http://127.0.0.1:8033/v1 --model gemma4-26b-base \
    --input /data/home/<user>/proj/external-benchmarks/google-research/instruction_following_eval/data/input_data.jsonl \
    --limit 50 --out /tmp/ifeval-responses.jsonl

Then score with their binary (PYTHONPATH=the google-research clone):
  cd <clone>/google-research && python3 -m instruction_following_eval.evaluation_main \
    --input_data=.../data/input_data.jsonl --input_response_data=<out> --output_dir=<dir>
"""
import argparse, json, time
from openai import OpenAI


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=50, help="first N prompts (fixed order = reproducible)")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args()

    client = OpenAI(api_key="dummy", base_url=a.base_url, timeout=a.timeout)
    rows = []
    with open(a.input, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
            if len(rows) >= a.limit:
                break
    print(f"{len(rows)} prompts, temp={a.temperature}")
    done = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            for attempt in range(1, 4):
                try:
                    resp = client.chat.completions.create(
                        model=a.model, temperature=a.temperature, max_tokens=a.max_tokens,
                        messages=[{"role": "user", "content": r["prompt"]}])
                    text = resp.choices[0].message.content or ""
                    break
                except Exception as e:
                    print(f"retry {attempt} key={r['key']}: {e}")
                    time.sleep(5 * attempt)
            else:
                text = ""
            f.write(json.dumps({"key": r["key"], "prompt": r["prompt"], "response": text},
                               ensure_ascii=False) + "\n")
            f.flush()
            done += 1
            if done % 10 == 0:
                print(f"{done}/{len(rows)}")
    print(f"wrote {done} responses -> {a.out}")


if __name__ == "__main__":
    main()
