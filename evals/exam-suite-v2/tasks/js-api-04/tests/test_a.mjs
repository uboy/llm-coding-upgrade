import test from "node:test";
import assert from "node:assert/strict";
import { looseParse } from "../solution.mjs";

test("plain", () => assert.deepEqual(looseParse('{"a": 1}'), { a: 1 }));
test("single quotes", () => assert.deepEqual(looseParse("{'a': 'x'}"), { a: "x" }));
test("comments", () => assert.deepEqual(looseParse("{ // note\n 'a': 1 /* c */, }"), { a: 1 }));
test("trailing comma array", () => assert.deepEqual(looseParse("[1, 2,]"), [1, 2]));
test("scalar", () => assert.equal(looseParse("42"), 42));
test("string escapes", () => assert.deepEqual(looseParse("['a\nb']"), ["a\nb"]));
test("unclosed", () => assert.throws(() => looseParse("{'a': ")));
test("unclosed comment", () => assert.throws(() => looseParse("{ /* x")));
