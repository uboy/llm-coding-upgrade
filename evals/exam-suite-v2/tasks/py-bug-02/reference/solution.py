def flatten(items, _seen=None):
    if _seen is None:
        _seen = set()
    marker = id(items)
    if marker in _seen:
        return []
    _seen.add(marker)
    out = []
    for x in items:
        if isinstance(x, (str, bytes)):
            out.append(x)
        elif hasattr(x, "__iter__"):
            out.extend(flatten(x, _seen))
        else:
            out.append(x)
    return out
