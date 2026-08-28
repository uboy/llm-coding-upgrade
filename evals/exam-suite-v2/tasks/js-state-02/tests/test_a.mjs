import test from "node:test";
import assert from "node:assert/strict";
import { createManualClock, createDebounce } from "../solution.mjs";

test("fires after wait", () => {
  const clock = createManualClock();
  let got = null;
  const d = createDebounce((x) => { got = x; }, 100, clock);
  d.call(1);
  clock.advance(50); d.tick();
  assert.equal(got, null);
  clock.advance(50); d.tick();
  assert.equal(got, 1);
});

test("last args win", () => {
  const clock = createManualClock();
  let got = null;
  const d = createDebounce((x) => { got = x; }, 100, clock);
  d.call(1); clock.advance(60); d.tick();
  d.call(2); clock.advance(100); d.tick();
  assert.equal(got, 2);
});

test("flush immediate", () => {
  const clock = createManualClock();
  let got = null;
  const d = createDebounce((x) => { got = x; }, 100, clock);
  d.call(7);
  d.flush();
  assert.equal(got, 7);
});

test("cancel", () => {
  const clock = createManualClock();
  let got = null;
  const d = createDebounce((x) => { got = x; }, 100, clock);
  d.call(7); d.cancel();
  clock.advance(500); d.tick();
  assert.equal(got, null);
});
