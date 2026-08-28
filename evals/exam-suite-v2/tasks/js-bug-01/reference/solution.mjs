export function makeTotaler() {
  const state = { sum: 0 };
  return {
    add: (kopecks) => { state.sum += kopecks; },
    get total() { return state.sum; },
  };
}
