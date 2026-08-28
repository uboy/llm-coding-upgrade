def apply_rate(amount_kopecks, permille):
    prod = amount_kopecks * permille
    q, r = divmod(prod, 1000)
    # divmod с отрицательными: python округляет вниз, r всегда >= 0
    twice = 2 * r
    if twice > 1000 or (twice == 1000 and q % 2 == 1):
        q += 1
    return q
