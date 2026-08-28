import re

def decode(stream):
    m = stream.rsplit("#", 1)
    if len(m) != 2 or not m[1].isdigit():
        raise ValueError("missing checksum")
    body, cs = m[0], int(m[1])
    total = 0
    out = []
    for num, sym, bangs in re.findall(r"(\d+)([^\d!])(!*)", body):
        n = int(num) + len(bangs)
        total += int(num) + len(bangs)
        out.append(sym * n)
    if total % 97 != cs % 97:
        raise ValueError("checksum mismatch")
    return "".join(out)
