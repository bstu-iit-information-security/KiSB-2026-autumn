"""Этап 1. Генератор на основе LFSR (линейного регистра сдвига с обратной связью).

Модель из методички (формула (8)):
    S_i(t+1) = S_{i+1}(t),                  i = 0..n-2
    S_{n-1}(t+1) = sum_j a_j * S_j(t) mod 2
    выход: s_t = S_0(t)
Коэффициенты a_j - это коэффициенты многочлена f(x) = x^n + a_{n-1}x^{n-1} + ... + a_1 x + a_0
(над GF(2) знак "минус" совпадает с "плюс").

Состояние хранится в одном целом числе: бит j = ячейка S_j.
Многочлен тоже хранится как целое число: бит j = коэффициент при x^j.
"""

from __future__ import annotations


# ---------------------------------------------------------------- многочлены над GF(2)

def poly_from_exponents(*exps: int) -> int:
    """poly_from_exponents(7, 1, 0) -> x^7 + x + 1 в виде битовой маски."""
    p = 0
    for e in exps:
        p ^= 1 << e
    return p


def poly_str(p: int) -> str:
    terms = []
    for e in range(p.bit_length() - 1, -1, -1):
        if (p >> e) & 1:
            terms.append("1" if e == 0 else "x" if e == 1 else f"x^{e}")
    return " + ".join(terms)


def deg(p: int) -> int:
    return p.bit_length() - 1


def gf2_mod(a: int, m: int) -> int:
    dm = deg(m)
    while a and deg(a) >= dm:
        a ^= m << (deg(a) - dm)
    return a


def gf2_mul_mod(a: int, b: int, m: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if deg(a) >= deg(m):
            a ^= m
    return gf2_mod(r, m)


def gf2_pow_mod(base: int, e: int, m: int) -> int:
    result, base = 1, gf2_mod(base, m)
    while e:
        if e & 1:
            result = gf2_mul_mod(result, base, m)
        base = gf2_mul_mod(base, base, m)
        e >>= 1
    return result


def gf2_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, gf2_mod(a, b)
    return a


def is_irreducible(f: int) -> bool:
    """Тест Рабина неприводимости над GF(2): f | x^(2^n) - x и gcd(f, x^(2^(n/q)) - x) = 1."""
    n = deg(f)
    if n < 1:
        return False
    x = 2
    # x^(2^k) mod f
    def frob(k: int) -> int:
        r = x
        for _ in range(k):
            r = gf2_mul_mod(r, r, f)
        return r

    if frob(n) != gf2_mod(x, f):
        return False
    for q in prime_factors(n):
        h = frob(n // q) ^ x
        if gf2_gcd(f, h) != 1:
            return False
    return True


def prime_factors(n: int) -> list[int]:
    res, d = [], 2
    while d * d <= n:
        if n % d == 0:
            res.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        res.append(n)
    return res


def is_primitive(f: int) -> bool:
    """f примитивен над GF(2) <=> f неприводим и порядок x по модулю f равен 2^n - 1."""
    n = deg(f)
    if n < 1 or not (f & 1) or not is_irreducible(f):
        return False
    order = (1 << n) - 1
    if gf2_pow_mod(2, order, f) != 1:
        return False
    return all(gf2_pow_mod(2, order // q, f) != 1 for q in prime_factors(order))


def factor_gf2(f: int) -> list[int]:
    """Разложение на неприводимые множители (перебором; для малых степеней)."""
    res, d = [], 2
    while deg(f) > 0 and deg(d) * 2 <= deg(f):
        while gf2_mod(f, d) == 0 and is_irreducible(d):
            res.append(d)
            f = gf2_div(f, d)
        d += 1
    if deg(f) > 0:
        res.append(f)
    return res


def gf2_div(a: int, b: int) -> int:
    q, db = 0, deg(b)
    while a and deg(a) >= db:
        s = deg(a) - db
        q ^= 1 << s
        a ^= b << s
    return q


# ---------------------------------------------------------------- сам генератор

class LFSR:
    def __init__(self, poly: int, seed: int):
        self.n = deg(poly)
        if self.n < 1 or not (poly & 1):
            raise ValueError("многочлен должен иметь степень >= 1 и a_0 = 1")
        self.taps = poly & ((1 << self.n) - 1)   # a_0 .. a_{n-1}
        self.mask = (1 << self.n) - 1
        self.state = seed & self.mask
        if self.state == 0:
            raise ValueError("нулевое состояние - вырожденное (выдаёт одни нули)")
        self.seed = self.state

    def next_bit(self) -> int:
        out = self.state & 1
        fb = (self.state & self.taps).bit_count() & 1
        self.state = (self.state >> 1) | (fb << (self.n - 1))
        return out

    def bits(self, count: int) -> list[int]:
        return [self.next_bit() for _ in range(count)]

    def random_int(self, nbits: int) -> int:
        """nbits подряд идущих бит выхода как целое число (первый бит - старший)."""
        v = 0
        for _ in range(nbits):
            v = (v << 1) | self.next_bit()
        return v

    def period(self, limit: int | None = None) -> int:
        """Период последовательности: число шагов до возврата в начальное состояние.
        Так как a_0 = 1, отображение состояний обратимо и последовательность чисто периодична."""
        limit = limit or (1 << self.n)
        saved = self.state
        self.state = self.seed
        t = 0
        while True:
            self.next_bit()
            t += 1
            if self.state == self.seed or t >= limit:
                break
        self.state = saved
        return t
