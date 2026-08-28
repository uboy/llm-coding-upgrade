COIN_VALUES = (1, 2, 5, 10)
_COIN_SET = frozenset(COIN_VALUES)

def vend(coins, price):
    total = sum(c for c in coins if c in _COIN_SET)
    return "ok" if total >= price else "need:%d" % (price - total)
