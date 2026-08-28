export function looseParse(text) {
  let i = 0;
  const n = text.length;

  function ws() {
    while (i < n) {
      const ch = text[i];
      if (ch === " " || ch === "\t" || ch === "\n" || ch === "\r") { i++; continue; }
      if (ch === "/" && text[i + 1] === "/") {
        while (i < n && text[i] !== "\n") i++;
        continue;
      }
      if (ch === "/" && text[i + 1] === "*") {
        const end = text.indexOf("*/", i + 2);
        if (end === -1) throw new Error("unclosed comment");
        i = end + 2;
        continue;
      }
      break;
    }
  }

  function value() {
    ws();
    if (i >= n) throw new Error("unexpected end");
    const ch = text[i];
    if (ch === "{" || ch === "[") return container(ch);
    if (ch === '"' || ch === "'") return string();
    if (text.startsWith("null", i)) { i += 4; return null; }
    if (text.startsWith("true", i)) { i += 4; return true; }
    if (text.startsWith("false", i)) { i += 5; return false; }
    const m = /^-?\d+(\.\d+)?([eE][+-]?\d+)?/.exec(text.slice(i));
    if (m) { i += m[0].length; return Number(m[0]); }
    throw new Error("bad value at " + i);
  }

  function string() {
    const q = text[i++];
    let out = "";
    while (i < n) {
      const ch = text[i];
      if (ch === "\\") {
        const nx = text[i + 1];
        if (nx === "n") out += "\n";
        else if (nx === q || nx === "\\" || nx === '"' || nx === "'") out += nx;
        else out += nx;
        i += 2;
        continue;
      }
      if (ch === q) { i++; return out; }
      out += ch;
      i++;
    }
    throw new Error("unclosed string");
  }

  function container(open) {
    i++; // открыли
    const close = open === "{" ? "}" : "]";
    const isObj = open === "{";
    const out = isObj ? {} : [];
    ws();
    if (text[i] === close) { i++; return out; }
    while (true) {
      if (isObj) {
        ws();
        const key = string();
        ws();
        if (text[i] !== ":") throw new Error("expected :");
        i++;
        out[key] = value();
      } else {
        out.push(value());
      }
      ws();
      if (text[i] === ",") { i++; ws(); if (text[i] === close) { i++; return out; } continue; }
      if (text[i] === close) { i++; return out; }
      throw new Error("expected , or " + close);
    }
  }

  const result = value();
  ws();
  if (i < n) throw new Error("trailing content");
  return result;
}
