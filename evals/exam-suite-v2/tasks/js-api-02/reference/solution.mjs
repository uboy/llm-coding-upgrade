function detectDelim(headerLine) {
  const commas = (headerLine.match(/,/g) || []).length;
  const semis = (headerLine.match(/;/g) || []).length;
  return semis > commas ? ";" : ",";
}

function splitLines(text) {
  const lines = [];
  let cur = "";
  let inQ = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') { inQ = !inQ; cur += ch; continue; }
    if ((ch === "\n" || ch === "\r") && !inQ) {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      lines.push(cur); cur = ""; continue;
    }
    cur += ch;
  }
  lines.push(cur);
  return lines;
}

function splitFields(line, delim) {
  const fields = [];
  let cur = "";
  let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQ && line[i + 1] === '"') { cur += '"'; i++; continue; }
      inQ = !inQ; continue;
    }
    if (ch === delim && !inQ) { fields.push(cur); cur = ""; continue; }
    cur += ch;
  }
  fields.push(cur);
  return fields;
}

export function parseTalka(text) {
  const rawLines = splitLines(text).filter((l) => l.trim() !== "");
  if (rawLines.length === 0) return [];
  const delim = detectDelim(rawLines[0]);
  const header = splitFields(rawLines[0], delim);
  return rawLines.slice(1).map((line) => {
    const fields = splitFields(line, delim);
    const obj = {};
    header.forEach((h, i) => { obj[h] = fields[i] ?? ""; });
    return obj;
  });
}
