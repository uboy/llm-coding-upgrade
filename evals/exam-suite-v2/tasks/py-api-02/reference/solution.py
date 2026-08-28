import re

def validate(numbers):
    pat = re.compile(r"^G(\d{2,6})-(\d{1,4})$")
    valid, normalized, errors = [], {}, {}
    for n in numbers:
        m = pat.match(n)
        if not m:
            errors[n] = "format"
        elif m.group(2).startswith("0"):
            errors[n] = "group"
        else:
            valid.append(n)
            normalized[n] = "g" + m.group(1) + m.group(2)
    return {"valid": valid, "normalized": normalized, "errors": errors}
