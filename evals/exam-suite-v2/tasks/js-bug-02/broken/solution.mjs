export async function loadAll(fetchers) {
  const out = [];
  for (const f of fetchers) {
    f().then((v) => out.push(v)).catch(() => {});
  }
  return out;
}
