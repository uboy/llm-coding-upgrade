import test from "node:test";
import assert from "node:assert/strict";
import { LRUCache } from "../solution.mjs";

test("evicts lru", () => {
  const c = new LRUCache(2);
  c.set("a", 1); c.set("b", 2); c.set("c", 3);
  assert.equal(c.get("a"), undefined);
  assert.equal(c.get("b"), 2);
  assert.equal(c.get("c"), 3);
});

test("get refreshes", () => {
  const c = new LRUCache(2);
  c.set("a", 1); c.set("b", 2);
  c.get("a");
  c.set("c", 3);
  assert.equal(c.get("a"), 1);
  assert.equal(c.get("b"), undefined);
});

test("set updates no grow", () => {
  const c = new LRUCache(2);
  c.set("a", 1); c.set("a", 9);
  assert.equal(c.size, 1);
  assert.equal(c.get("a"), 9);
});

test("keys order fresh to old", () => {
  const c = new LRUCache(3);
  c.set("a", 1); c.set("b", 2); c.get("a");
  assert.deepEqual(c.keys(), ["a", "b"]);
});

test("evict event", () => {
  const c = new LRUCache(1);
  const seen = [];
  c.on("evict", (k, v) => seen.push([k, v]));
  c.set("a", 1); c.set("b", 2);
  assert.deepEqual(seen, [["a", 1]]);
});
