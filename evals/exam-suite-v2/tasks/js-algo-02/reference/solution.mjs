export function decode(stream) {
  const hashAt = stream.lastIndexOf("#");
  if (hashAt === -1 || !/^\d+$/.test(stream.slice(hashAt + 1))) throw new Error("missing checksum");
  const body = stream.slice(0, hashAt);
  const cs = Number(stream.slice(hashAt + 1));
  let total = 0, out = "";
  const re = /(\d+)([^\d!])(!*)/y;
  let m;
  while ((m = re.exec(body)) !== null) {
    const n = Number(m[1]) + m[3].length;
    total += n;
    out += m[2].repeat(n);
  }
  if (total % 97 !== cs % 97) throw new Error("checksum mismatch");
  return out;
}
