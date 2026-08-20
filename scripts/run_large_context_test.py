#!/usr/bin/env python3
"""
Large-context stress test for Qwen3.8-27B Fast Mode (ctx=32768).
Fills ~80% of the context window with a realistic multi-module codebase,
then asks the model for a comprehensive code review.

Measures:
  - Time to first token (TTFT)
  - Total generation time
  - Output token count
  - Whether the model completes or stalls
"""

import json
import time
import sys
import urllib.request
import urllib.error

API_URL = "http://v100-host:8001"
TARGET_FILL_TOKENS = 26000   # ~80% of 32768 ctx
MAX_NEW_TOKENS     = 2048
TIMEOUT_SECONDS    = 300

# ── Synthetic codebase ──────────────────────────────────────────────────────
# Each module is ~200-400 tokens. We stack them until we reach TARGET_FILL_TOKENS.

MODULE_TEMPLATE = '''
# ════════════════════════════════════════════════════════════════════════════
# Module: {name}
# ════════════════════════════════════════════════════════════════════════════

import threading
import time
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, auto

logger = logging.getLogger(__name__)


class {name}State(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FAILED = auto()
    DONE = auto()


@dataclass
class {name}Config:
    """Configuration for {name}."""
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    batch_size: int = 64
    queue_maxsize: int = 1024
    enable_metrics: bool = True
    tags: Dict[str, str] = field(default_factory=dict)


class {name}Error(Exception):
    """Base exception for {name}."""
    def __init__(self, message: str, code: int = 0, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class {name}:
    """
    {name} — manages the lifecycle of {name_lower} operations.

    Thread-safe. Supports graceful shutdown via context manager.

    Example::

        config = {name}Config(max_retries=5, timeout=60.0)
        with {name}(config) as mgr:
            result = mgr.process(payload)
    """

    def __init__(self, config: Optional[{name}Config] = None):
        self._config = config or {name}Config()
        self._state = {name}State.IDLE
        self._lock = threading.RLock()
        self._metrics: Dict[str, int] = defaultdict(int)
        self._handlers: List[Callable] = []
        self._shutdown_event = threading.Event()
        self._worker: Optional[threading.Thread] = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def __enter__(self) -> "{name}":
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    def start(self) -> None:
        """Start the {name_lower} manager."""
        with self._lock:
            if self._state != {name}State.IDLE:
                raise {name}Error(f"Cannot start: state={{self._state.name}}")
            self._state = {name}State.RUNNING
            self._worker = threading.Thread(
                target=self._run_loop, daemon=True, name="{name}-worker"
            )
            self._worker.start()
            logger.info("[{name}] started (batch=%d, timeout=%.1fs)",
                        self._config.batch_size, self._config.timeout)

    def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stop; waits up to *timeout* seconds for the worker."""
        with self._lock:
            if self._state not in ({name}State.RUNNING, {name}State.PAUSED):
                return
            self._state = {name}State.DONE
        self._shutdown_event.set()
        if self._worker:
            self._worker.join(timeout=timeout)
        logger.info("[{name}] stopped. metrics=%s", dict(self._metrics))

    # ── Core logic ───────────────────────────────────────────────────────────

    def process(self, payload: Any) -> Any:
        """Process a single payload with retry logic."""
        for attempt in range(1, self._config.max_retries + 1):
            try:
                return self._do_process(payload)
            except {name}Error as exc:
                if not exc.retryable or attempt == self._config.max_retries:
                    raise
                wait = self._config.retry_delay * (2 ** (attempt - 1))
                logger.warning("[{name}] attempt %d failed (%s), retrying in %.1fs",
                               attempt, exc, wait)
                time.sleep(wait)
                self._metrics["retries"] += 1
        raise {name}Error("Exhausted retries", code=-1)

    def _do_process(self, payload: Any) -> Any:
        """Internal processing — override in subclass."""
        if self._state != {name}State.RUNNING:
            raise {name}Error("Not running", retryable=False)
        self._metrics["processed"] += 1
        return payload   # identity transform — subclass should override

    def _run_loop(self) -> None:
        """Background worker loop."""
        while not self._shutdown_event.is_set():
            try:
                self._tick()
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("[{name}] worker error: %s", exc, exc_info=True)
                self._metrics["errors"] += 1
            self._shutdown_event.wait(timeout=0.1)

    def _tick(self) -> None:
        """Called every ~100ms by the worker loop."""

    # ── Handlers ─────────────────────────────────────────────────────────────

    def register_handler(self, fn: Callable) -> None:
        """Register a callback invoked after each successful process()."""
        with self._lock:
            self._handlers.append(fn)

    def _notify(self, result: Any) -> None:
        for fn in self._handlers:
            try:
                fn(result)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("[{name}] handler error: %s", exc)

    # ── Metrics ──────────────────────────────────────────────────────────────

    @property
    def metrics(self) -> Dict[str, int]:
        """Return a snapshot of current metrics."""
        with self._lock:
            return dict(self._metrics)

    def reset_metrics(self) -> None:
        """Reset all counters to zero."""
        with self._lock:
            self._metrics.clear()
'''

MODULES = [
    "EventBus", "TaskScheduler", "RateLimiter", "CacheManager",
    "ConnectionPool", "CircuitBreaker", "DataPipeline", "MetricsCollector",
    "AlertDispatcher", "HealthMonitor", "AuditLogger", "SessionManager",
    "TokenBucket", "LeakyBucket", "PriorityQueue", "WorkerPool",
    "RetryPolicy", "Backoff", "FeatureFlag", "ConfigLoader",
    "SecretManager", "ServiceRegistry", "LoadBalancer", "Tracer",
]

def build_codebase(target_tokens: int) -> str:
    """Approximate: 1 token ≈ 4 chars in code."""
    target_chars = target_tokens * 4
    parts = []
    total = 0
    i = 0
    while total < target_chars:
        mod = MODULES[i % len(MODULES)]
        chunk = MODULE_TEMPLATE.format(
            name=mod,
            name_lower=mod.lower()
        )
        parts.append(chunk)
        total += len(chunk)
        i += 1
        if i > 500:
            break
    code = "\n".join(parts)
    return code[:target_chars]


def count_approx_tokens(text: str) -> int:
    return len(text) // 4


def stream_completion(prompt: str) -> tuple[str, float, float, int]:
    """
    Returns: (full_output, ttft_seconds, total_seconds, output_tokens)
    """
    payload = json.dumps({
        "model": "qwen38-fast",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_NEW_TOKENS,
        "temperature": 0.2,
        "stream": True,
    }).encode()

    req = urllib.request.Request(
        f"{API_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t_start = time.monotonic()
    ttft = None
    output_parts = []
    output_tokens = 0

    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                if ttft is None:
                    ttft = time.monotonic() - t_start
                    print(f"\n[TTFT: {ttft:.2f}s]", flush=True)
                output_parts.append(content)
                print(content, end="", flush=True)
                output_tokens += 1

            # Check for finish_reason
            finish = chunk.get("choices", [{}])[0].get("finish_reason")
            if finish:
                print(f"\n[finish_reason: {finish}]", flush=True)

    total_time = time.monotonic() - t_start
    return "".join(output_parts), ttft or total_time, total_time, output_tokens


def main():
    print("=" * 70)
    print("LARGE CONTEXT STRESS TEST — Qwen3.8-27B Fast Mode (ctx=32768)")
    print("=" * 70)

    # ── Build codebase ───────────────────────────────────────────────────────
    print(f"\n[1/3] Building synthetic codebase (~{TARGET_FILL_TOKENS} tokens)...")
    codebase = build_codebase(TARGET_FILL_TOKENS)
    approx_tokens = count_approx_tokens(codebase)
    print(f"      Codebase size: {len(codebase):,} chars ≈ {approx_tokens:,} tokens")

    # ── Build prompt ─────────────────────────────────────────────────────────
    prompt = f"""You are a senior software architect. Below is a multi-module Python codebase.

Your task: write a comprehensive code review covering ALL of the following:
1. **Architecture & design patterns** — identify what patterns are used, what's good, what's missing
2. **Thread safety** — spot any race conditions or locking issues across the modules
3. **Error handling** — evaluate retry logic, exception hierarchy, and propagation
4. **Performance bottlenecks** — identify any O(n) or blocking operations in hot paths
5. **Missing abstractions** — what interfaces or protocols should be extracted
6. **Top 5 concrete refactoring recommendations** — with specific code examples

=== CODEBASE START ===
{codebase}
=== CODEBASE END ===

Begin your review now. Be thorough and specific. Reference exact class and method names."""

    total_prompt_tokens = count_approx_tokens(prompt)
    print(f"      Total prompt: ≈{total_prompt_tokens:,} tokens "
          f"({total_prompt_tokens/32768*100:.1f}% of 32k ctx)")

    if total_prompt_tokens > 31000:
        print(f"      WARNING: prompt may exceed ctx limit, trimming...")
        # trim codebase to fit
        trim = (31000 - count_approx_tokens(prompt) + approx_tokens) * 4
        codebase = codebase[:trim]
        prompt = prompt.replace(codebase + "\n=== CODEBASE END ===",
                                codebase[:trim] + "\n=== CODEBASE END ===")

    # ── Send request ─────────────────────────────────────────────────────────
    print(f"\n[2/3] Sending to {API_URL} (timeout={TIMEOUT_SECONDS}s)...")
    print("-" * 70)
    print("MODEL OUTPUT:")
    print("-" * 70)

    try:
        output, ttft, total, out_tokens = stream_completion(prompt)
    except urllib.error.URLError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except TimeoutError:
        print(f"\nTIMEOUT after {TIMEOUT_SECONDS}s — model did not finish!")
        sys.exit(2)

    # ── Results ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[3/3] RESULTS")
    print("=" * 70)
    print(f"  Prompt tokens (approx):  {total_prompt_tokens:,}")
    print(f"  Output tokens (approx):  {out_tokens:,}")
    print(f"  Time to first token:     {ttft:.2f}s")
    print(f"  Total generation time:   {total:.2f}s")
    if out_tokens > 0 and total > 0:
        tok_per_sec = out_tokens / total
        print(f"  Output speed:            {tok_per_sec:.1f} tok/s")
    print(f"  Output length:           {len(output):,} chars")
    status = "COMPLETE" if len(output) > 100 else "STALLED/EMPTY"
    print(f"  Status:                  {status}")
    print("=" * 70)


if __name__ == "__main__":
    main()
