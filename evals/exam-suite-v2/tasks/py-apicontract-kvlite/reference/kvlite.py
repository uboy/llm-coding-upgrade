"""Эталонное решение KVLite (проверяет достижимость задачи: все тесты зелёные)."""
import re

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
_BOOL = {"true": True, "false": False, "on": True, "off": False}
_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def _parse_quoted(s, lineno):
    if len(s) < 2 or not s.endswith('"'):
        raise ValueError(f"line {lineno}: unterminated string")
    out = []
    i = 1
    while i < len(s) - 1:
        ch = s[i]
        if ch == "\\":
            if i + 1 >= len(s) - 1 or s[i + 1] not in _ESCAPES:
                raise ValueError(f"line {lineno}: unknown escape")
            out.append(_ESCAPES[s[i + 1]])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _parse_scalar(s, lineno):
    s = s.strip()
    if s.startswith('"'):
        return _parse_quoted(s, lineno)
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip() for p in inner.split(",")]
        return [_parse_scalar(p, lineno) for p in parts]
    if _INT_RE.match(s):
        return int(s)
    if _FLOAT_RE.match(s):
        return float(s)
    if s.lower() in _BOOL:
        return _BOOL[s.lower()]
    return s


def parse(text: str) -> dict:
    result = {}
    sections = set()
    current = result
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]") and "=" not in line:
            name = line[1:-1].strip()
            if name in sections:
                raise ValueError(f"line {lineno}: duplicate section {name!r}")
            sections.add(name)
            current = {}
            result[name] = current
            continue
        if "=" not in line:
            raise ValueError(f"line {lineno}: unrecognized line")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not value:
            raise ValueError(f"line {lineno}: empty value")
        current[key] = _parse_scalar(value, lineno)
    return result
