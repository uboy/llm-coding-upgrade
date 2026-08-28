import test from "node:test";
import assert from "node:assert/strict";
import { loadAll } from "../solution.mjs";

test("all ok", async () => {
  const r = await loadAll([() => Promise.resolve("a"), () => Promise.resolve("b")]);
  assert.deepEqual(r, ["a", "b"]);
});

test("rejection isolated", async () => {
  const r = await loadAll([
    () => Promise.resolve("a"),
    () => Promise.reject(new Error("x")),
    () => Promise.resolve("c"),
  ]);
  assert.deepEqual(r, ["a", null, "c"]);
});

test("mixed delays keep order", async () => {
  const r = await loadAll([
    () => new Promise((res) => setTimeout(() => res("slow"), 40)),
    () => new Promise((res) => setTimeout(() => res("fast"), 5)),
  ]);
  assert.deepEqual(r, ["slow", "fast"]);
});
