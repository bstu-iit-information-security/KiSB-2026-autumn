

def poly_degree(poly: int) -> int:
    return poly.bit_length() - 1


def poly_mod(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("деление на нулевой многочлен")
    db = poly_degree(b)
    while a and poly_degree(a) >= db:
        a ^= b << (poly_degree(a) - db)
    return a


def poly_mulmod(a: int, b: int, mod: int) -> int:
    result = 0
    dmod = poly_degree(mod)
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if poly_degree(a) >= dmod:
            a ^= mod << (poly_degree(a) - dmod)
    return poly_mod(result, mod)


def poly_powmod(base: int, exp: int, mod: int) -> int:
    result = 1
    base = poly_mod(base, mod)
    while exp:
        if exp & 1:
            result = poly_mulmod(result, base, mod)
        base = poly_mulmod(base, base, mod)
        exp >>= 1
    return result


def _poly_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, poly_mod(a, b)
    return a


def _prime_factors(n: int) -> list[int]:
    factors = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            factors.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def is_irreducible(poly: int) -> bool:
    n = poly_degree(poly)
    if n < 1:
        return False
    if n == 1:
        return True

    x = 0b10

    if poly_powmod(x, 1 << n, poly) != x:
        return False

    for d in range(1, n):
        if n % d != 0:
            continue
        h = poly_powmod(x, 1 << d, poly) ^ x
        if h == 0:
            return False
        if _poly_gcd(h, poly) != 1:
            return False
    return True


def is_primitive(poly: int) -> bool:
    n = poly_degree(poly)
    if not is_irreducible(poly):
        return False
    if n == 1:
        return True
    order = (1 << n) - 1
    x = 0b10  # ← и здесь тоже
    for p in _prime_factors(order):
        if poly_powmod(x, order // p, poly) == 1:
            return False
    return True


class LFSR:

    __slots__ = ("_state", "_mask", "_tap_mask", "_n")

    def __init__(self, poly: int, seed: int):
        if not is_primitive(poly):
            raise ValueError(f"Многочлен 0b{poly:b} не примитивен")
        n = poly_degree(poly)
        self._n = n
        self._mask = (1 << n) - 1
        self._tap_mask = poly & self._mask
        if seed == 0 or seed > self._mask:
            raise ValueError("seed должен быть в [1, 2^n − 1]")
        self._state = seed & self._mask

    def next_bit(self) -> int:
        out = self._state & 1
        feedback = (self._state & self._tap_mask).bit_count() & 1
        self._state = (self._state >> 1) | (feedback << (self._n - 1))
        return out

    def next_bits(self, count: int) -> list[int]:
        return [self.next_bit() for _ in range(count)]

    @property
    def period(self) -> int:
        return (1 << self._n) - 1