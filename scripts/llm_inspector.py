#!/usr/bin/env python3
"""
llm_inspector.py — Transparent proxy for LLM API traffic inspection.

Sits between your client (Claude Code, Cursor, OpenWebUI, scripts) and any
OpenAI-compatible LLM server. Logs all raw request/response data so you can:
  - See exactly what tokens are being sent and received
  - Track prompt_tokens, completion_tokens, cache_read_tokens per request
  - Measure actual decode tok/s from server timings
  - Identify oversized system prompts and optimization opportunities
  - Debug unexpected model behavior with full request context

Architecture:
  Client → Inspector (port 4002) → Real backend (port 4001)

Usage:
  python scripts/llm_inspector.py \\
    --backend http://127.0.0.1:4001 \\
    --port 4002 \\
    [--log-dir runs/inspector-TIMESTAMP] \\
    [--no-color] \\
    [--quiet]

  # Then point your client to http://127.0.0.1:4002 instead of 4001
  # All traffic is logged without any client changes needed.

Supports:
  - Streaming (SSE) responses: collected, forwarded, and logged
  - Non-streaming responses
  - Any HTTP method (GET, POST, OPTIONS)
  - CORS headers pass-through

Output:
  - Colorized summary per request to stdout
  - Full JSON log per request in --log-dir
  - Running token usage statistics
"""

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import socket

ANSI_GREEN  = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RED    = "\033[91m"
ANSI_CYAN   = "\033[96m"
ANSI_BLUE   = "\033[94m"
ANSI_BOLD   = "\033[1m"
ANSI_DIM    = "\033[2m"
ANSI_RESET  = "\033[0m"

USE_COLOR = sys.stdout.isatty()


def c(text: str, color: str) -> str:
    if not USE_COLOR:
        return text
    return f"{color}{text}{ANSI_RESET}"


class Stats:
    """Thread-safe running statistics."""
    def __init__(self):
        self._lock = threading.Lock()
        self.total_requests = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cached_tokens = 0
        self.total_errors = 0

    def record(self, prompt_tokens: int, completion_tokens: int, cached_tokens: int):
        with self._lock:
            self.total_requests += 1
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_cached_tokens += cached_tokens

    def record_error(self):
        with self._lock:
            self.total_requests += 1
            self.total_errors += 1

    def summary(self) -> dict:
        with self._lock:
            return {
                "requests": self.total_requests,
                "prompt_tokens": self.total_prompt_tokens,
                "completion_tokens": self.total_completion_tokens,
                "cached_tokens": self.total_cached_tokens,
                "errors": self.total_errors,
                "cache_rate_pct": round(
                    self.total_cached_tokens / max(self.total_prompt_tokens, 1) * 100, 1
                ),
            }


STATS = Stats()
LOG_DIR: Path | None = None
BACKEND_URL: str = "http://127.0.0.1:4001"
QUIET: bool = False
REQUEST_COUNTER = 0
COUNTER_LOCK = threading.Lock()


def next_request_id() -> int:
    global REQUEST_COUNTER
    with COUNTER_LOCK:
        REQUEST_COUNTER += 1
        return REQUEST_COUNTER


def format_messages_preview(messages: list) -> str:
    """Show first 100 chars of each message for quick identification."""
    if not messages:
        return "(no messages)"
    parts = []
    for m in messages:
        role = m.get("role", "?")
        content = m.get("content", "")
        if isinstance(content, str):
            preview = content[:100].replace("\n", "↵")
            if len(content) > 100:
                preview += f"… [{len(content):,} chars total]"
        else:
            preview = f"[complex content: {type(content).__name__}]"
        parts.append(f"  {c(role, ANSI_CYAN)}: {preview}")
    return "\n".join(parts)


def parse_sse_chunks(raw_bytes: bytes) -> tuple[str, dict]:
    """
    Parse SSE (Server-Sent Events) stream from llama.cpp / OpenAI.
    Returns (full_text_content, aggregated_usage_dict).
    """
    text = raw_bytes.decode("utf-8", errors="replace")
    full_content = ""
    usage = {}
    timings = {}

    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            continue
        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        # Accumulate content
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            content = delta.get("content", "")
            if content:
                full_content += content

        # Last chunk often contains usage
        if "usage" in chunk:
            usage = chunk["usage"]
        if "timings" in chunk:
            timings = chunk["timings"]

    return full_content, {"usage": usage, "timings": timings}


def log_request(req_id: int, method: str, path: str, req_body: bytes,
                resp_status: int, resp_body: bytes, wall_s: float,
                is_streaming: bool):
    """Parse, display, and save a request/response pair."""

    ts = datetime.now().isoformat()

    # Parse request
    req_json = None
    if req_body:
        try:
            req_json = json.loads(req_body)
        except Exception:
            pass

    # Parse response
    resp_json = None
    stream_content = ""
    if resp_body:
        if is_streaming:
            stream_content, extra = parse_sse_chunks(resp_body)
            # Build a synthetic response for logging
            resp_json = {
                "_streamed": True,
                "content_assembled": stream_content[:500] + ("…" if len(stream_content) > 500 else ""),
                **extra,
            }
        else:
            try:
                resp_json = json.loads(resp_body)
            except Exception:
                pass

    # Extract usage stats
    usage = {}
    timings = {}
    if resp_json:
        usage = resp_json.get("usage", {})
        timings = resp_json.get("timings", {})
    prompt_tokens     = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    cached_tokens     = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    pp_tps     = timings.get("prompt_per_second", 0)
    dec_tps    = timings.get("predicted_per_second", 0)

    # Update stats
    if resp_status < 400:
        STATS.record(prompt_tokens, completion_tokens, cached_tokens)
    else:
        STATS.record_error()

    cumulative = STATS.summary()

    if not QUIET:
        # --- Terminal output ---
        cache_pct = cached_tokens / max(prompt_tokens, 1) * 100
        cache_color = ANSI_GREEN if cache_pct > 60 else ANSI_YELLOW if cache_pct > 20 else ANSI_DIM
        status_color = ANSI_GREEN if resp_status < 400 else ANSI_RED
        dec_color = ANSI_GREEN if dec_tps > 35 else ANSI_YELLOW if dec_tps > 10 else ANSI_DIM

        stream_tag = c("[SSE]", ANSI_BLUE) + " " if is_streaming else ""
        print(
            f"\n{c(f'#{req_id:04d}', ANSI_BOLD)} {c(method, ANSI_CYAN)} {path}  "
            f"{stream_tag}"
            f"{c(str(resp_status), status_color)}  "
            f"wall={wall_s:.2f}s"
        )

        if req_json:
            model = req_json.get("model", "?")
            messages = req_json.get("messages", [])
            max_tok = req_json.get("max_tokens", "?")
            temp = req_json.get("temperature", "?")
            n_msg = len(messages)
            total_chars = sum(
                len(m.get("content", "")) if isinstance(m.get("content"), str) else 0
                for m in messages
            )
            print(
                f"  {c('→', ANSI_DIM)} model={c(model, ANSI_CYAN)}  "
                f"messages={n_msg}  "
                f"total_chars={total_chars:,}  "
                f"max_tokens={max_tok}  "
                f"temp={temp}"
            )
            if messages:
                # Show last user message preview
                last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
                if last_user:
                    content = last_user.get("content", "")
                    if isinstance(content, str):
                        preview = content[:120].replace("\n", "↵")
                        print(f"  {c('user:', ANSI_CYAN)} {preview}{'…' if len(content) > 120 else ''}")

        if prompt_tokens or completion_tokens:
            print(
                f"  {c('←', ANSI_DIM)} "
                f"prompt={c(str(prompt_tokens), ANSI_YELLOW)}  "
                f"completion={c(str(completion_tokens), ANSI_CYAN)}  "
                f"cached={c(f'{cached_tokens} ({cache_pct:.0f}%)', cache_color)}  "
                + (f"PP={pp_tps:.0f} tok/s  " if pp_tps else "")
                + (f"decode={c(f'{dec_tps:.1f}', dec_color)} tok/s" if dec_tps else "")
            )

            cumul_cache_color = ANSI_GREEN if cumulative["cache_rate_pct"] > 30 else ANSI_YELLOW
            cache_rate_str = f"{cumulative['cache_rate_pct']:.0f}%"
            print(
                f"  {c('Σ', ANSI_DIM)} session: "
                f"req={cumulative['requests']}  "
                f"prompt={cumulative['prompt_tokens']:,}  "
                f"compl={cumulative['completion_tokens']:,}  "
                f"cache_rate={c(cache_rate_str, cumul_cache_color)}"
            )

    # Save to log file
    if LOG_DIR:
        log_entry = {
            "id": req_id,
            "timestamp": ts,
            "method": method,
            "path": path,
            "wall_s": round(wall_s, 3),
            "is_streaming": is_streaming,
            "response_status": resp_status,
            "request": req_json if req_json else req_body.decode("utf-8", errors="replace")[:2000],
            "response": resp_json if resp_json else resp_body.decode("utf-8", errors="replace")[:2000],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cached_tokens": cached_tokens,
                "cache_rate_pct": round(cache_pct if prompt_tokens else 0, 1),
            },
            "timings": {
                "pp_tps": round(pp_tps, 1),
                "dec_tps": round(dec_tps, 1),
            },
        }
        log_file = LOG_DIR / f"req-{req_id:04d}.json"
        log_file.write_text(json.dumps(log_entry, indent=2, ensure_ascii=False), encoding="utf-8")


class InspectorHandler(BaseHTTPRequestHandler):
    """HTTP handler that proxies all requests and logs them."""

    def log_message(self, format, *args):
        pass  # Suppress default access log; we handle logging ourselves

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return self.rfile.read(length)
        return b""

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def _proxy(self, method: str):
        req_id = next_request_id()
        req_body = self._read_body()

        backend_url = BACKEND_URL.rstrip("/") + self.path
        t0 = time.perf_counter()

        # Determine if client wants streaming
        is_streaming = False
        if req_body:
            try:
                parsed = json.loads(req_body)
                is_streaming = bool(parsed.get("stream", False))
            except Exception:
                pass

        # Forward request to backend
        headers = {
            "Content-Type": self.headers.get("Content-Type", "application/json"),
        }
        if self.headers.get("Authorization"):
            headers["Authorization"] = self.headers["Authorization"]

        req = urlrequest.Request(backend_url, data=req_body if req_body else None,
                                 headers=headers, method=method)
        try:
            with urlrequest.urlopen(req, timeout=600) as backend_resp:
                resp_status = backend_resp.status
                resp_headers = dict(backend_resp.headers)
                resp_body = backend_resp.read()
        except HTTPError as e:
            resp_status = e.code
            resp_headers = {}
            resp_body = e.read()
        except URLError as e:
            # Backend unreachable
            wall_s = time.perf_counter() - t0
            print(c(f"\n#{req_id:04d} BACKEND ERROR: {e.reason}", ANSI_RED))
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            err_body = json.dumps({"error": {"message": f"Inspector: backend error: {e.reason}"}}).encode()
            self.wfile.write(err_body)
            STATS.record_error()
            return
        except Exception as e:
            wall_s = time.perf_counter() - t0
            print(c(f"\n#{req_id:04d} PROXY ERROR: {e}", ANSI_RED))
            self.send_response(500)
            self.end_headers()
            STATS.record_error()
            return

        wall_s = time.perf_counter() - t0

        # Forward response to client
        self.send_response(resp_status)
        for key, val in resp_headers.items():
            key_lower = key.lower()
            if key_lower in ("content-length", "transfer-encoding", "connection"):
                continue  # Will be set correctly below
            self.send_header(key, val)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)

        # Log asynchronously so we don't block the response
        threading.Thread(
            target=log_request,
            args=(req_id, method, self.path, req_body, resp_status, resp_body, wall_s, is_streaming),
            daemon=True,
        ).start()

    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")


def print_startup_banner(port: int, backend: str, log_dir: str | None):
    print(f"\n{c('LLM Inspector', ANSI_BOLD + ANSI_CYAN)} started")
    print(f"  Listen   : http://0.0.0.0:{port}")
    print(f"  Backend  : {backend}")
    print(f"  Log dir  : {log_dir or '(disabled)'}")
    print(f"\n  Point your client to: http://127.0.0.1:{port}")
    print(f"  All traffic will be forwarded transparently and logged.")
    print(f"\n  {c('Columns:', ANSI_DIM)} #id method path | status wall_time")
    print(f"  → request: model messages max_tokens temperature")
    print(f"  ← response: prompt_tokens completion cached cache_rate% PP_tps decode_tps")
    print(f"  Σ session totals")
    print(f"\n{c('Waiting for requests...', ANSI_DIM)}\n")


def main():
    global BACKEND_URL, LOG_DIR, QUIET, USE_COLOR

    parser = argparse.ArgumentParser(
        description="Transparent LLM proxy for traffic inspection"
    )
    parser.add_argument("--backend", default="http://127.0.0.1:4001",
                        help="Backend LLM server URL (default: http://127.0.0.1:4001)")
    parser.add_argument("--port", type=int, default=4002,
                        help="Inspector listen port (default: 4002)")
    parser.add_argument("--log-dir", default=None,
                        help="Directory to save request logs (default: runs/inspector-TIMESTAMP)")
    parser.add_argument("--no-log", action="store_true",
                        help="Disable file logging (terminal output only)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-request terminal output (log files only)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI color output")
    args = parser.parse_args()

    BACKEND_URL = args.backend.rstrip("/")
    QUIET = args.quiet
    if args.no_color:
        USE_COLOR = False

    if not args.no_log:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_dir_path = args.log_dir or f"runs/inspector-{ts}"
        LOG_DIR = Path(log_dir_path)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    print_startup_banner(args.port, BACKEND_URL, str(LOG_DIR) if LOG_DIR else None)

    server = ThreadingHTTPServer(("0.0.0.0", args.port), InspectorHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{c('Shutting down...', ANSI_YELLOW)}")
        summary = STATS.summary()
        print(f"\n{c('Session Summary:', ANSI_BOLD)}")
        print(f"  Total requests:     {summary['requests']}")
        print(f"  Total errors:       {summary['errors']}")
        print(f"  Prompt tokens:      {summary['prompt_tokens']:,}")
        print(f"  Completion tokens:  {summary['completion_tokens']:,}")
        print(f"  Cached tokens:      {summary['cached_tokens']:,}")
        rate_str = f"{summary['cache_rate_pct']:.1f}%"
        print(f"  Cache hit rate:     {c(rate_str, ANSI_GREEN)}")
        if LOG_DIR:
            # Save session summary
            summary_file = LOG_DIR / "session-summary.json"
            summary["timestamp"] = datetime.now().isoformat()
            summary["backend"] = BACKEND_URL
            summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(f"\n  Logs saved to: {LOG_DIR}")


if __name__ == "__main__":
    main()
