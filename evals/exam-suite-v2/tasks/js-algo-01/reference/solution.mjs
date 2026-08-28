export function firstFreeSlot(busy, duration, dayStart, dayEnd) {
  if (duration <= 0) throw new Error("duration must be positive");
  const iv = busy.filter(([s, e]) => e > s).sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const [s, e] of iv) {
    if (merged.length && s <= merged[merged.length - 1][1]) {
      merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], e);
    } else merged.push([s, e]);
  }
  let t = dayStart;
  for (const [s, e] of merged) {
    if (s - t >= duration) return [t, t + duration];
    t = Math.max(t, e);
  }
  if (dayEnd - t >= duration) return [t, t + duration];
  return null;
}
