import test from "node:test";
import assert from "node:assert/strict";
import { expandSchedule } from "../solution.mjs";

test("single", () => assert.deepEqual(expandSchedule("mon@09:00-10:00"), ["mon 09:00-10:00"]));
test("range", () => assert.deepEqual(expandSchedule("sat-sun@11:30-12:00"), ["sat 11:30-12:00", "sun 11:30-12:00"]));
test("sort by weekday", () => {
  const got = expandSchedule("sun@09:00-10:00,mon@09:00-10:00");
  assert.deepEqual(got, ["mon 09:00-10:00", "sun 09:00-10:00"]);
});
test("sort by time within day", () => {
  const got = expandSchedule("mon@15:00-16:00,mon@09:00-10:00");
  assert.deepEqual(got, ["mon 09:00-10:00", "mon 15:00-16:00"]);
});
test("example count", () => assert.equal(expandSchedule("mon-fri@09:00-10:00,sat@11:30-12:00").length, 6));
test("bad day", () => assert.throws(() => expandSchedule("monday@09:00-10:00")));
test("bad minute", () => assert.throws(() => expandSchedule("mon@09:75-10:00")));
test("end before start", () => assert.throws(() => expandSchedule("mon@10:00-09:00")));
test("equal", () => assert.throws(() => expandSchedule("mon@10:00-10:00")));
test("dedup", () => assert.deepEqual(expandSchedule("mon@09:00-10:00,mon@09:00-10:00"), ["mon 09:00-10:00"]));
