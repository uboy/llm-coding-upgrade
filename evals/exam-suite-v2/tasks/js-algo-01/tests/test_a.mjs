import test from "node:test";
import assert from "node:assert/strict";
import { firstFreeSlot } from "../solution.mjs";

test("simple gap", () => assert.deepEqual(firstFreeSlot([[60, 120]], 30, 0, 240), [0, 30]));
test("gap between", () => assert.deepEqual(firstFreeSlot([[0, 60], [90, 240]], 30, 0, 240), [60, 90]));
test("overlap merge", () => assert.deepEqual(firstFreeSlot([[0, 100], [50, 150]], 50, 0, 240), [150, 200]));
test("no room", () => assert.equal(firstFreeSlot([[0, 240]], 10, 0, 240), null));
test("zero len ignored", () => assert.deepEqual(firstFreeSlot([[30, 30]], 40, 0, 100), [0, 40]));
test("bad duration", () => assert.throws(() => firstFreeSlot([], 0, 0, 100)));
