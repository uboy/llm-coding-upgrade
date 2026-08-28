import test from "node:test";
import assert from "node:assert/strict";
import { makeAudited } from "../solution.mjs";

test("set reports", () => {
  const log = [];
  const o = makeAudited({ a: 1 }, (k, oldV, newV) => log.push([k, oldV, newV]));
  o.a = 2;
  o.b = 3;
  assert.deepEqual(log, [["a", 1, 2], ["b", undefined, 3]]);
});

test("same value no report", () => {
  let calls = 0;
  const o = makeAudited({ a: 1 }, () => calls++);
  o.a = 1;
  assert.equal(calls, 0);
});

test("delete reports", () => {
  const log = [];
  const o = makeAudited({ a: 1 }, (k, oldV, newV) => log.push([k, oldV, newV]));
  delete o.a;
  assert.deepEqual(log, [["a", 1, undefined]]);
  assert.equal(o.a, undefined);
});

test("enumeration works", () => {
  const o = makeAudited({ a: 1, b: 2 }, () => {});
  assert.deepEqual(Object.keys(o), ["a", "b"]);
});
