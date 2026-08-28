export function minWindow(events, required) {
  if (required.length === 0) return [0, 0];
  const need = new Map(required.map((t) => [t, 1]));
  let missing = required.length;
  let best = null;
  let i = 0;
  for (let j = 0; j < events.length; j++) {
    const tag = events[j];
    if (need.has(tag)) {
      if (need.get(tag) > 0) missing--;
      need.set(tag, need.get(tag) - 1);
    }
    while (missing === 0) {
      if (best === null || j + 1 - i < best[1] - best[0]) best = [i, j + 1];
      const left = events[i];
      if (need.has(left)) {
        need.set(left, need.get(left) + 1);
        if (need.get(left) > 0) missing++;
      }
      i++;
    }
  }
  return best;
}
