export const PLANS = { light: true, standard: true, premium: true };

export function calc(plan, minutes) {
  switch (plan) {
    case "light":
      return minutes <= 30 ? 0 : (minutes - 30) * 1.5;
    case "standard":
      return minutes <= 100 ? 0 : (minutes - 100) * 1.0;
    case "premium":
      return minutes <= 300 ? 0 : (minutes - 300) * 0.8;
    default:
      throw new Error("unknown plan");
  }
}
