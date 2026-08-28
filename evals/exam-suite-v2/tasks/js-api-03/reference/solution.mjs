const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const IDX = new Map(DAYS.map((d, i) => [d, i]));

function parseTime(t) {
  const m = /^(\d{2}):(\d{2})$/.exec(t);
  if (!m) throw new Error("bad time " + t);
  const h = Number(m[1]), min = Number(m[2]);
  if (h > 23 || min > 59) throw new Error("bad time " + t);
  return h * 60 + min;
}

function expandDays(part) {
  const dash = part.indexOf("-");
  if (dash === -1) {
    if (!IDX.has(part)) throw new Error("bad day " + part);
    return [part];
  }
  const a = part.slice(0, dash), b = part.slice(dash + 1);
  if (!IDX.has(a) || !IDX.has(b)) throw new Error("bad range " + part);
  const ia = IDX.get(a), ib = IDX.get(b);
  if (ia > ib) throw new Error("bad range " + part);
  const out = [];
  for (let i = ia; i <= ib; i++) out.push(DAYS[i]);
  return out;
}

export function expandSchedule(expr) {
  const out = new Set();
  for (const group of expr.split(",")) {
    const at = group.indexOf("@");
    if (at === -1) throw new Error("bad group " + group);
    const daysPart = group.slice(0, at);
    const range = group.slice(at + 1);
    const dash = range.indexOf("-");
    if (dash === -1) throw new Error("bad range");
    const t1 = parseTime(range.slice(0, dash));
    const t2 = parseTime(range.slice(dash + 1));
    if (t2 <= t1) throw new Error("end must be after start");
    const slot = range.slice(0, dash) + "-" + range.slice(dash + 1);
    for (const d of expandDays(daysPart)) out.add(d + " " + slot);
  }
  return [...out].sort((x, y) => {
    const [dx, tx] = x.split(" ");
    const [dy, ty] = y.split(" ");
    const w = IDX.get(dx) - IDX.get(dy);
    if (w !== 0) return w;
    return tx.localeCompare(ty);
  });
}
