def flatten(items):
    out = []
    for x in items:
        if hasattr(x, "__iter__"):
            out.extend(flatten(x))
        else:
            out.append(x)
    return out
