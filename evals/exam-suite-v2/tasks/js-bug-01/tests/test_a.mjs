import test from "node:test";
import assert from "node:assert/strict";
import { makeTotaler } from "../solution.mjs";

test("direct", () => {
  const t = makeTotaler();
  t.add(10); t.add(5);
  assert.equal(t.total, 15);
});

test("as callback", () => {
  const t = makeTotaler();
  [1, 2, 3].map(t.add);
  assert.equal(t.total, 6);
});

test("destructured method", () => {
  const t = makeTotaler();
  const { add } = t;
  add(7);
  assert.equal(t.total, 7);
});
