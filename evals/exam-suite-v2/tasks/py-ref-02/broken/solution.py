COIN_VALUES = [1, 2, 5, 10]

def vend(coins, price):
    total = 0
    for c in coins:
        if c == 1:
            total += 1
        elif c == 2:
            total += 2
        elif c == 5:
            total += 5
        elif c == 10:
            total += 10
    if total >= price:
        return "ok"
    return "need:" + str(price - total)
