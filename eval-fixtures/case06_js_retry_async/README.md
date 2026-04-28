# Case 06: JavaScript Async Retry Helper

Implement `retry_async.js` so that the test suite passes.

Requirements:

- Export `async function retryAsync(fn, options)`.
- `options` fields:
  - `retries` – total attempts, minimum `1`;
  - `delayMs` – base delay between retries;
  - `factor` – optional multiplier, default `1`;
  - `shouldRetry(error, attempt)` – optional hook.
- Behavior:
  - call `fn` until it resolves or attempts are exhausted;
  - wait `delayMs * factor^(attempt-1)` before each retry;
  - if `shouldRetry` exists and returns `false`, stop immediately;
  - rethrow the last error when retries are exhausted;
  - use only Node.js standard APIs.

Constraints:

- Do not modify tests.
- Keep the implementation in a single file: `retry_async.js`.
