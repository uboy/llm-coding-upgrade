import test from "node:test";
import assert from "node:assert/strict";
import { monthName } from "../solution.mjs";

test("march", () => assert.equal(monthName("2024-03-09"), "март"));
test("january", () => assert.equal(monthName("2024-01-31"), "январь"));
test("december", () => assert.equal(monthName("2024-12-01"), "декабрь"));
test("bad month", () => assert.throws(() => monthName("2024-13-01")));
test("bad day", () => assert.throws(() => monthName("2024-03-32")));
test("bad format", () => assert.throws(() => monthName("20240301")));
