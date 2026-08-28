export function createManualClock() {
  let t = 0;
  return {
    now: () => t,
    advance: (ms) => { t += ms; },
  };
}

export function createDebounce(fn, waitMs, clock = null) {
  const c = clock ?? { now: () => performance.now() };
  let pendingArgs = null;
  let dueAt = null;
  return {
    call(...args) {
      pendingArgs = args;
      dueAt = c.now() + waitMs;
    },
    tick() {
      if (pendingArgs !== null && c.now() >= dueAt) {
        const args = pendingArgs;
        pendingArgs = null;
        dueAt = null;
        fn(...args);
      }
    },
    flush() {
      if (pendingArgs !== null) {
        const args = pendingArgs;
        pendingArgs = null;
        dueAt = null;
        fn(...args);
      }
    },
    cancel() {
      pendingArgs = null;
      dueAt = null;
    },
  };
}
