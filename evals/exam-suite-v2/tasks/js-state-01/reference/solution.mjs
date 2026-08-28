import { EventEmitter } from "node:events";

const PHASES = ["red", "red-yellow", "green", "yellow"];

export class TrafficLight extends EventEmitter {
  #phase = 0;
  constructor() {
    super();
  }
  get state() {
    return PHASES[this.#phase];
  }
  tick() {
    this.#phase = (this.#phase + 1) % PHASES.length;
    this.emit("change", this.state);
    if (this.state === "red") this.emit("red");
  }
  onRed(cb) {
    this.once("red", cb);
  }
}
