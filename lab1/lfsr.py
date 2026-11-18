"""Линейные регистры сдвига с обратной связью (LFSR) и работа с многочленами над GF(2).

Многочлен хранится как целое число: бит i равен коэффициенту при x^i.
Например, x^5 + x^2 + 1  ->  0b100101 = 37.
"""


def poly(*exponents):
    """poly(5, 2, 0) -> целое представление x^5 + x^2 + 1."""
    p = 0
    for e in exponents:
        p |= 1 << e
    return p


def poly_str(p):
    """Человекочитаемая запись многочлена."""
    terms = []
    for e in range(p.bit_length() - 1, -1, -1):
        if (p >> e) & 1:
            terms.append("1" if e == 0 else ("x" if e == 1 else f"x^{e}"))
    return " + ".join(terms)


def degree(p):
    return p.bit_length() - 1


# ---------------------------------------------------------------- арифметика GF(2)[x]
def mulmod(a, b, f):
    """(a*b) mod f в GF(2)[x]; a, b должны быть степени < deg f."""
    d = degree(f)
    res = 0
    while b:
        if b & 1:
            res ^= a
        b >>= 1
        a <<= 1
        if (a >> d) & 1:
            a ^= f
    return res


def powmod_x(e, f):
    """x^e mod f в GF(2)[x] (быстрое возведение в степень)."""
    d = degree(f)
    result = 1
    base = 2 if d > 1 else 0  # x mod f; для d == 1 это 1 (x + 1 = 0 => x = 1)
    if d == 1:
        base = 1
    while e:
        if e & 1:
            result = mulmod(result, base, f)
        base = mulmod(base, base, f)
        e >>= 1
    return result


def prime_factors(n):
    """Простые делители n (пробные деления; n <= 2^40 - мгновенно)."""
    res, d = [], 2
    while d * d <= n:
        if n % d == 0:
            res.append(d)
            while n % d == 0:
                n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        res.append(n)
    return res


def is_primitive(f):
    """Примитивен ли многочлен f по модулю 2.

    f примитивен  <=>  порядок элемента x в GF(2)[x]/(f) равен 2^n - 1,
    где n = deg f (из этого следует и неприводимость f).
    Проверка: x^(2^n-1) = 1  и  x^((2^n-1)/p) != 1 для каждого простого p | 2^n-1.
    """
    n = degree(f)
    if n < 1 or not (f & 1):  # свободный член должен быть равен 1
        return False
    N = (1 << n) - 1
    if powmod_x(N, f) != 1:
        return False
    return all(powmod_x(N // p, f) != 1 for p in prime_factors(N))


# ---------------------------------------------------------------- сам регистр
class LFSR:
    """Регистр Фибоначчи длины n, порождённый многочленом
    f(x) = x^n + a_{n-1} x^{n-1} + ... + a_1 x + a_0.

    Рекуррента:  s_{t+n} = a_0 s_t + a_1 s_{t+1} + ... + a_{n-1} s_{t+n-1}  (mod 2).
    Бит j слова `state` равен s_{t+j}; выходной бит - младший (ячейка S0).
    """

    def __init__(self, f, seed):
        self.n = degree(f)
        if self.n < 1 or not (f & 1):
            raise ValueError("свободный член многочлена должен быть равен 1")
        self.taps = f & ((1 << self.n) - 1)
        self.state = seed & ((1 << self.n) - 1)
        if self.state == 0:
            raise ValueError("нулевое начальное состояние недопустимо")

    def step(self):
        out = self.state & 1
        fb = bin(self.state & self.taps).count("1") & 1
        self.state = (self.state >> 1) | (fb << (self.n - 1))
        return out

    def bits(self, count):
        return [self.step() for _ in range(count)]
