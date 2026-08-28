from collections import Counter

def min_window(events, required):
    if not required:
        return (0, 0)
    need = Counter(required)
    missing = len(required)
    best = None
    i = 0
    for j, tag in enumerate(events):
        if tag in need:
            if need[tag] > 0:
                missing -= 1
            need[tag] -= 1
        while missing == 0:
            if best is None or (j + 1 - i) < (best[1] - best[0]):
                best = (i, j + 1)
            if events[i] in need:
                need[events[i]] += 1
                if need[events[i]] > 0:
                    missing += 1
            i += 1
    return best
