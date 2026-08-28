import test from "node:test";
import assert from "node:assert/strict";
import { cookingOrder } from "../solution.mjs";

test("chain", () => assert.deepEqual(cookingOrder({ b: ["a"], a: [] }), ["a", "b"]));
test("lex minimal", () => assert.deepEqual(cookingOrder({ z: [], a: [], m: ["a"] }), ["a", "m", "z"]));
test("diamond order", () => {
  const got = cookingOrder({ d: ["b", "c"], b: ["a"], c: ["a"], a: [] });
  assert.ok(got.indexOf("a") < got.indexOf("b") && got.indexOf("a") < got.indexOf("c"));
  assert.ok(got.indexOf("b") < got.indexOf("d") && got.indexOf("c") < got.indexOf("d"));
});
test("cycle", () => assert.throws(() => cookingOrder({ a: ["b"], b: ["a"] })));
test("ingredient only", () => assert.deepEqual(cookingOrder({ a: ["x"] }), ["x", "a"]));
