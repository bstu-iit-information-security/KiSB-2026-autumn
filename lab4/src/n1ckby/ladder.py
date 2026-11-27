from curve import O, add, choose, double


def ladder(k, t):
    """Предусловие: скаляр занимает не более 256 бит."""
    r0, r1 = O, t
    for shift in range(255, -1, -1):
        bit = (k >> shift) & 1
        left = choose(bit, r0, r1)
        total = add(r0, r1)
        twice = double(left)
        r0 = choose(bit, twice, total)
        r1 = choose(bit, total, twice)
    return r0
