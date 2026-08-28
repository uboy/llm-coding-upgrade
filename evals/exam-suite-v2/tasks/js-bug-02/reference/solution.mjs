export async function loadAll(fetchers) {
  const settled = await Promise.allSettled(fetchers.map((f) => f()));
  return settled.map((r) => (r.status === "fulfilled" ? r.value : null));
}
