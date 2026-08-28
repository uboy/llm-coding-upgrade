import test from "node:test";
import assert from "node:assert/strict";
import { loadProfile } from "../solution.mjs";

const api = {
  getProfile: (id, cb) => cb(null, { id, name: "Ann" }),
  getSettings: (id, cb) => cb(null, { theme: "dark" }),
  getAvatar: (id, cb) => cb(new Error("no avatar")),
};

test("full flow", (_, done) => {
  loadProfile(1, api, (err, res) => {
    assert.equal(err, null);
    assert.deepEqual(res, { profile: { id: 1, name: "Ann" }, settings: { theme: "dark" }, avatar: null });
    done();
  });
});

test("profile error", (_, done) => {
  const badApi = { ...api, getProfile: (id, cb) => cb(new Error("gone")) };
  loadProfile(2, badApi, (err) => {
    assert.ok(err instanceof Error);
    done();
  });
});
