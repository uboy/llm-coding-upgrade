import test from "node:test";
import assert from "node:assert/strict";
import { calc, PLANS } from "../solution.mjs";

test("within included", () => assert.equal(calc("light", 10), 0));
test("light over", () => assert.equal(calc("light", 40), 15));
test("standard over", () => assert.equal(calc("standard", 150), 50));
test("premium over", () => assert.equal(calc("premium", 400), 80));
test("plans exported", () => assert.deepEqual(Object.keys(PLANS).sort(), ["light", "premium", "standard"]));
test("unknown plan", () => assert.throws(() => calc("ultra", 10)));
