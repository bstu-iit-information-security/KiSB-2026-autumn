"""Утилиты для работы с многочленами над GF(2)."""

def poly_mod(a, b):
    """Остаток от деления a на b (многочлены как битовые маски)."""
    while a.bit_length() >= b.bit_length():
        a ^= b << (a.bit_length() - b.bit_length())
    return a

def poly_mul(a, b):
    """Умножение многочленов (без модуля)."""
    res = 0
    while b:
        if b & 1:
            res ^= a
        a <<= 1
        b >>= 1
    return res

def poly_mul_mod(a, b, mod):
    return poly_mod(poly_mul(a, b), mod)

def poly_pow_mod(base, exp, mod):
    """base^exp mod в GF(2)[x]."""
    res = 1
    while exp:
        if exp & 1:
            res = poly_mul_mod(res, base, mod)
        base = poly_mul_mod(base, base, mod)
        exp >>= 1
    return res

def factor_int(n):
    """Простые делители n."""
    fs = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            fs.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        fs.append(n)
    return fs

def is_irreducible(poly, degree):
    """Тест неприводимости: x^(2^deg) ≡ x (mod poly) и gcd(x^(2^(deg/p))-x, poly)=1 для всех простых p|deg."""
    # 1. x^(2^deg) = x mod poly
    x = 0b10
    if poly_pow_mod(x, 2**degree, poly) != x:
        return False
    # 2. Для каждого простого p | degree: gcd(x^(2^(deg/p)) - x, poly) = 1
    for p in factor_int(degree):
        sub = poly_pow_mod(x, 2**(degree // p), poly) ^ x
        # gcd многочленов — алгоритм Евклида
        a, b = poly, sub
        while b != 0:
            a, b = b, poly_mod(a, b)
        if a.bit_length() > 1:  # gcd != 1
            return False
    return True

def is_primitive(poly, degree):
    """Примитивность: неприводим + порядок корня = 2^deg - 1."""
    if not is_irreducible(poly, degree):
        return False
    order = 2**degree - 1
    x = 0b10
    if poly_pow_mod(x, order, poly) != 1:
        return False
    for p in factor_int(order):
        if poly_pow_mod(x, order // p, poly) == 1:
            return False
    return True