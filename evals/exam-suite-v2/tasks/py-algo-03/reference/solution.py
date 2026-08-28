import heapq

def cooking_order(deps):
    nodes = set(deps)
    for lst in deps.values():
        nodes.update(lst)
    indeg = {n: 0 for n in nodes}
    adj = {n: [] for n in nodes}
    for dish, needs in deps.items():
        for need in needs:
            adj[need].append(dish)
            indeg[dish] += 1
    heap = [n for n in nodes if indeg[n] == 0]
    heapq.heapify(heap)
    order = []
    while heap:
        n = heapq.heappop(heap)
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                heapq.heappush(heap, m)
    if len(order) != len(nodes):
        raise ValueError("cycle")
    return order
