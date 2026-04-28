# Case 04: Sliding Window Rate Limiter

Implement `rate_limiter.py` so that the test suite passes.

Requirements:

- Export a class `SlidingWindowRateLimiter`.
- Constructor:
  - `SlidingWindowRateLimiter(max_requests: int, window_seconds: float, now_func=None)`
- Methods:
  - `allow(user_id: str) -> bool`
- Behavior:
  - maintain a separate sliding window per `user_id`;
  - allow at most `max_requests` requests inside the last `window_seconds`;
  - timestamps `<= now - window_seconds` are outside the active window and must be pruned;
  - default clock should be monotonic time when `now_func` is not provided;
  - raise `ValueError` when `max_requests <= 0` or `window_seconds <= 0`;
  - use only the Python standard library.

Constraints:

- Do not modify tests.
- Keep the implementation in a single file: `rate_limiter.py`.
