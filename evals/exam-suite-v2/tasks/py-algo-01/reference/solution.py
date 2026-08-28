def first_free_slot(busy, duration, day_start, day_end):
    if duration <= 0:
        raise ValueError("duration must be positive")
    iv = sorted((s, e) for s, e in busy if e > s)
    merged = []
    for s, e in iv:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    t = day_start
    for s, e in merged:
        if s - t >= duration:
            return (t, t + duration)
        t = max(t, e)
    if day_end - t >= duration:
        return (t, t + duration)
    return None
