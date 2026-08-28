import test from "node:test";
import assert from "node:assert/strict";
import { decode } from "../solution.mjs";

test("basic", () => assert.equal(decode("3a2b#5"), "aaabb"));
test("bang", () => assert.equal(decode("3a!#4"), "aaaa"));
test("multidigit", () => assert.equal(decode("12x#12"), "x".repeat(12)));
test("no checksum", () => assert.throws(() => decode("3a")));
test("bad checksum", () => assert.throws(() => decode("3a#4")));
test("multi bang", () => assert.equal(decode("1a!!#3"), "aaa"));
