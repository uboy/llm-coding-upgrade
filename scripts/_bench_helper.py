#!/usr/bin/env python3
"""Helper for v100-benchmark.sh — generates JSON payloads and parses responses."""
import json, sys

def make_request(model, prompt, max_tokens):
    """Generate JSON request body."""
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False
    }
    print(json.dumps(data))

def parse_response(field):
    """Extract a field from the JSON response on stdin."""
    try:
        d = json.load(sys.stdin)
        if field == "content":
            c = d.get("choices", [{}])[0].get("message", {})
            content = c.get("content", "")
            print(content)
        elif field == "reasoning_content":
            c = d.get("choices", [{}])[0].get("message", {})
            rc = c.get("reasoning_content", "") or ""
            print(len(rc))
        elif field == "completion_tokens":
            print(d.get("usage", {}).get("completion_tokens", 0))
        elif field == "prompt_tokens":
            print(d.get("usage", {}).get("prompt_tokens", 0))
    except Exception:
        if field == "reasoning_content":
            print("0")
        else:
            print("0")

def get_task_ids(suite_file):
    """List all task IDs from the suite."""
    with open(suite_file) as f:
        for t in json.load(f)["tasks"]:
            print(t["id"])

def get_task_field(suite_file, task_id, field):
    """Get a specific field from a task."""
    with open(suite_file) as f:
        for t in json.load(f)["tasks"]:
            if t["id"] == task_id:
                val = t.get(field, "")
                sys.stdout.write(str(val))
                break

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "make-request":
        make_request(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif cmd == "parse":
        parse_response(sys.argv[2])
    elif cmd == "task-ids":
        get_task_ids(sys.argv[2])
    elif cmd == "task-field":
        get_task_field(sys.argv[2], sys.argv[3], sys.argv[4])
