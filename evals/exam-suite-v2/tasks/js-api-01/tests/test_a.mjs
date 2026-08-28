import test from "node:test";
import assert from "node:assert/strict";
import { parseQuery, stringify } from "../solution.mjs";

test("simple", () => assert.deepEqual(parseQuery("a=1&b=2"), { a: "1", b: "2" }));
test("plus is space", () => assert.equal(parseQuery("q=hello+world").q, "hello world"));
test("percent", () => assert.equal(parseQuery("s=%D1%8F").s, "я"));
test("array", () => assert.deepEqual(parseQuery("t[]=a&t[]=b"), { t: ["a", "b"] }));
test("nested one level", () => assert.deepEqual(parseQuery("u[name]=ann"), { u: { name: "ann" } }));
test("last wins", () => assert.deepEqual(parseQuery("k=1&k=2"), { k: "2" }));
test("bad percent", () => assert.throws(() => parseQuery("x=%ZZ")));
test("stringify", () => assert.equal(stringify({ a: "1", b: "2" }), "a=1&b=2"));
test("stringify array", () => assert.equal(stringify({ t: ["a", "b"] }), "t[]=a&t[]=b"));
test("stringify null", () => assert.equal(stringify({ flag: null }), "flag"));
