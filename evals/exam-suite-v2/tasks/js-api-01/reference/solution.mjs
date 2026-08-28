function decode(s) {
  const r = decodeURIComponent(s.replace(/\+/g, " "));
  if (r.includes("%")) {
    // decodeURIComponent бросил бы SyntaxError на плохой последовательности; дошли сюда - значит ок
  }
  return r;
}

export function parseQuery(qs) {
  const out = {};
  if (!qs) return out;
  for (const pair of qs.split("&")) {
    const eq = pair.indexOf("=");
    const rawK = eq === -1 ? pair : pair.slice(0, eq);
    const rawV = eq === -1 ? "" : pair.slice(eq + 1);
    const k = decode(rawK);
    const v = decode(rawV);
    let m;
    if ((m = k.match(/^(.+)\[\]$/))) {
      const key = m[1];
      (out[key] = Array.isArray(out[key]) ? out[key] : []).push(v);
    } else if ((m = k.match(/^(.+)\[(.+)\]$/))) {
      (out[m[1]] = out[m[1]] && typeof out[m[1]] === "object" ? out[m[1]] : {})[m[2]] = v;
    } else {
      out[k] = v;
    }
  }
  return out;
}

function enc(s) {
  return encodeURIComponent(String(s)).replace(/%20/g, "+");
}

export function stringify(obj) {
  const parts = [];
  for (const [k, v] of Object.entries(obj)) {
    if (v === null || v === undefined) { parts.push(enc(k)); continue; }
    if (Array.isArray(v)) {
      for (const item of v) parts.push(enc(k) + "[]=" + enc(item));
    } else if (typeof v === "object") {
      for (const [ik, iv] of Object.entries(v)) {
        parts.push(enc(k) + "[" + enc(ik) + "]=" + enc(iv));
      }
    } else {
      parts.push(enc(k) + "=" + enc(v));
    }
  }
  return parts.join("&");
}
