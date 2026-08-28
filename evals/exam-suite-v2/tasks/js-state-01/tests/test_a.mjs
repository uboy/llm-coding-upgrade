import test from "node:test";
import assert from "node:assert/strict";
import { TrafficLight } from "../solution.mjs";

test("cycle", () => {
  const t = new TrafficLight();
  assert.equal(t.state, "red");
  t.tick(); assert.equal(t.state, "red-yellow");
  t.tick(); assert.equal(t.state, "green");
  t.tick(); assert.equal(t.state, "yellow");
  t.tick(); assert.equal(t.state, "red");
});

test("change event", () => {
  const t = new TrafficLight();
  const seen = [];
  t.on("change", (s) => seen.push(s));
  t.tick(); t.tick();
  assert.deepEqual(seen, ["red-yellow", "green"]);
});

test("onRed once", () => {
  const t = new TrafficLight();
  let calls = 0;
  t.onRed(() => calls++);
  t.tick(); t.tick(); t.tick(); // red-yellow, green, yellow
  assert.equal(calls, 0);
  t.tick(); // red
  assert.equal(calls, 1);
  t.tick(); t.tick(); t.tick(); t.tick(); // полный цикл снова red
  assert.equal(calls, 1);
});
