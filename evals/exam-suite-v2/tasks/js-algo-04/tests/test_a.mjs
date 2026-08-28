import test from "node:test";
import assert from "node:assert/strict";
import { minWindow } from "../solution.mjs";

test("basic", () => assert.deepEqual(minWindow(["a","x","b","y","a","b"], ["a","b"]), [4, 6]));
test("empty required", () => assert.deepEqual(minWindow(["a"], []), [0, 0]));
test("no cover", () => assert.equal(minWindow(["a","b"], ["a","c"]), null));
test("tie leftmost", () => assert.deepEqual(minWindow(["a","b","a","b"], ["a","b"]), [0, 2]));
test("single", () => assert.deepEqual(minWindow(["z","q","z"], ["z"]), [0, 1]));
