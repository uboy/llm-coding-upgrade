import assert from "node:assert/strict";
import { createEventBus } from "../event_bus.ts";

type Events = {
  ready: { value: number };
  text: string;
};

const bus = createEventBus<Events>();
let readyCalls = 0;
let textValue = "";
const unsubscribe = bus.on("ready", (payload) => {
  readyCalls += payload.value;
});
bus.once("text", (payload) => {
  textValue = payload;
});

bus.emit("ready", { value: 2 });
bus.emit("ready", { value: 3 });
bus.emit("text", "hello");
bus.emit("text", "ignored");
unsubscribe();
bus.emit("ready", { value: 5 });

assert.equal(readyCalls, 5);
assert.equal(textValue, "hello");
