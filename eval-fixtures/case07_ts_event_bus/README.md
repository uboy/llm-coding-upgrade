# Case 07: Typed TypeScript Event Bus

Implement `event_bus.ts` so that the test suite passes.

Requirements:

- Export `createEventBus<Events extends Record<string, any>>()`.
- Returned object methods:
  - `on(event, listener)` returns unsubscribe function;
  - `once(event, listener)` returns unsubscribe function;
  - `off(event, listener)`;
  - `emit(event, payload)`.
- Behavior:
  - listener payload types must match the event name;
  - preserve listener order;
  - `once` listeners must fire only once;
  - use only standard TypeScript / JavaScript features.

Constraints:

- Do not modify tests.
- Keep the implementation in a single file: `event_bus.ts`.
