import test from "node:test";
import assert from "node:assert/strict";
import { parseTalka } from "../solution.mjs";

test("comma basic", () => assert.deepEqual(parseTalka("a,b\n1,2\n"), [{ a: "1", b: "2" }]));
test("semicolon detected", () => assert.deepEqual(parseTalka("a;b\n1;2"), [{ a: "1", b: "2" }]));
test("quotes", () => assert.deepEqual(parseTalka('a,b\n"x","y"'), [{ a: "x", b: "y" }]));
test("escaped quote", () => assert.deepEqual(parseTalka('a\n"say ""hi"""\n'), [{ a: 'say "hi"' }]));
test("newline in quotes", () => assert.deepEqual(parseTalka('a,b\n"line1\nline2",2'), [{ a: "line1\nline2", b: "2" }]));
test("empty lines skipped", () => assert.deepEqual(parseTalka("a\n\n1\n\n"), [{ a: "1" }]));
