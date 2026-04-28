const assert = require("assert");
const { retryAsync } = require("../retry_async.js");

async function main() {
  let attempts = 0;
  const values = [];
  const result = await retryAsync(async () => {
    attempts += 1;
    values.push(attempts);
    if (attempts < 3) {
      throw new Error("boom");
    }
    return "ok";
  }, { retries: 4, delayMs: 1 });
  assert.strictEqual(result, "ok");
  assert.deepStrictEqual(values, [1, 2, 3]);

  let rejectedAttempts = 0;
  await assert.rejects(
    () => retryAsync(async () => {
      rejectedAttempts += 1;
      throw new Error("fatal");
    }, {
      retries: 3,
      delayMs: 1,
      shouldRetry(error, attempt) {
        return attempt < 2 && error.message === "fatal";
      }
    }),
    /fatal/
  );
  assert.strictEqual(rejectedAttempts, 2);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
