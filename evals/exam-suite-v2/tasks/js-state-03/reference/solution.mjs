import { EventEmitter } from "node:events";

export class LRUCache extends EventEmitter {
  #map = new Map();
  constructor(capacity) {
    super();
    this.capacity = capacity;
  }
  get size() {
    return this.#map.size;
  }
  keys() {
    return [...this.#map.keys()].reverse();
  }
  get(key) {
    if (!this.#map.has(key)) return undefined;
    const v = this.#map.get(key);
    this.#map.delete(key);
    this.#map.set(key, v);
    return v;
  }
  set(key, value) {
    if (this.#map.has(key)) this.#map.delete(key);
    this.#map.set(key, value);
    this.emit("set", key);
    if (this.#map.size > this.capacity) {
      const oldest = this.#map.keys().next().value;
      const ov = this.#map.get(oldest);
      this.#map.delete(oldest);
      this.emit("evict", oldest, ov);
    }
  }
}
