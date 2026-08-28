import re
from datetime import date

def balance(entries):
    balances, skipped = {}, []
    for e in entries:
        parts = e.split("|")
        ok = len(parts) == 4
        if ok:
            ds, acc, op, amt = parts
            ok = bool(re.fullmatch(r"\d+", amt)) and int(amt) >= 0
        if ok:
            try:
                d = date.fromisoformat(ds[6:10] + "-" + ds[3:5] + "-" + ds[0:2])
                ok = bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", ds))
            except ValueError:
                ok = False
        if ok and op not in ("D", "C"):
            ok = False
        if not ok:
            skipped.append(e)
            continue
        delta = int(amt) if op == "C" else -int(amt)
        balances[acc] = balances.get(acc, 0) + delta
    return {"balances": balances, "skipped": skipped}
