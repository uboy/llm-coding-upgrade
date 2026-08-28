export function cookingOrder(deps) {
  const nodes = new Set(Object.keys(deps));
  for (const lst of Object.values(deps)) for (const n of lst) nodes.add(n);
  const indeg = new Map([...nodes].map((n) => [n, 0]));
  const adj = new Map([...nodes].map((n) => [n, []]));
  for (const [dish, needs] of Object.entries(deps)) {
    for (const need of needs) {
      adj.get(need).push(dish);
      indeg.set(dish, indeg.get(dish) + 1);
    }
  }
  const heap = [...nodes].filter((n) => indeg.get(n) === 0).sort();
  const order = [];
  while (heap.length) {
    const n = heap.shift();
    order.push(n);
    for (const m of adj.get(n)) {
      indeg.set(m, indeg.get(m) - 1);
      if (indeg.get(m) === 0) {
        heap.push(m);
        heap.sort();
      }
    }
  }
  if (order.length !== nodes.size) throw new Error("cycle");
  return order;
}
