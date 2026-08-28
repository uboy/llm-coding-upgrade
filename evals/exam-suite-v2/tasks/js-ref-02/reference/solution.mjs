export const PLANS = {
  light: { included: 30, perMinute: 1.5 },
  standard: { included: 100, perMinute: 1.0 },
  premium: { included: 300, perMinute: 0.8 },
};

export function calc(plan, minutes) {
  const p = PLANS[plan];
  if (!p) throw new Error("unknown plan");
  const over = Math.max(0, minutes - p.included);
  return Math.round(over * p.perMinute * 2) / 2;
}
