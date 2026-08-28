import re

def render(template, ctx):
    def repl(m):
        inner = m.group(1)
        parts = [p.strip() for p in inner.split("|")]
        name, filters = parts[0], parts[1:]
        if any(f.startswith("default:") for f in filters[1:]):
            raise ValueError("default must be first")
        if filters and filters[0].startswith("default:"):
            text = filters[0][len("default:"):]
            if name not in ctx:
                value = text
            else:
                value = ctx[name]
            filters = filters[1:]
        else:
            if name not in ctx:
                raise ValueError(f"missing key {name}")
            value = ctx[name]
        for f in filters:
            if f == "up":
                value = value.upper()
            elif f == "low":
                value = value.lower()
            elif f.startswith("trunc:"):
                n = int(f[6:])
                value = value[:n]
            else:
                raise ValueError(f"unknown filter {f}")
        return str(value)
    return re.sub(r"\{\{(.*?)\}\}", repl, template)
