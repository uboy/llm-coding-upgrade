import test from "node:test";
import assert from "node:assert/strict";
import { paginate } from "../solution.mjs";

function makeApi(pages) {
  let i = 0;
  let calls = 0;
  return {
    get calls() { return calls; },
    fetchPage: async () => {
      calls++;
      const p = pages[Math.min(i, pages.length - 1)];
      i++;
      return p;
    },
  };
}

test("for-await yields all", async () => {
  const api = makeApi([
    { items: [1, 2], nextCursor: "b" },
    { items: [3], nextCursor: null },
  ]);
  const got = [];
  for await (const x of paginate(api.fetchPage)) got.push(x);
  assert.deepEqual(got, [1, 2, 3]);
  assert.equal(api.calls, 2);
});

test("lazy fetching", async () => {
  const api = makeApi([{ items: [1, 2, 3], nextCursor: null }]);
  const it = paginate(api.fetchPage)[Symbol.asyncIterator]();
  await it.next();
  assert.equal(api.calls, 1);
  await it.next();
  assert.equal(api.calls, 1);
});

test("empty pages", async () => {
  const api = makeApi([
    { items: [], nextCursor: "b" },
    { items: [7], nextCursor: null },
  ]);
  const got = [];
  for await (const x of paginate(api.fetchPage)) got.push(x);
  assert.deepEqual(got, [7]);
});
