# -*- coding: utf-8 -*-
"""Тесты корректности (запуск: python3 tests_lab1.py)"""
from lab1 import *
from sympy import isprime

def t_lcg_formula():
    g = LCG(1, 1664525, 1013904223, 2**32)
    assert g.next() == 1015568748
    # общий член x_t = a^t x0 + (a^t-1)/(a-1) c mod N  (свойство 1)
    N, a, c, x0 = 15, 1, 4, 3
    g = LCG(x0, a, c, N)
    for t in range(1, 40):
        assert g.next() == (x0 + t * c) % N
    N, a, c, x0 = 16, 5, 3, 7
    g = LCG(x0, a, c, N)
    for t in range(1, 40):
        assert g.next() == (pow(a, t, N * (a - 1)) * x0 + (pow(a, t, N * (a - 1)) - 1) // (a - 1) * c) % N

def t_hull_dobell_bruteforce():
    # для малых N теорема Халла-Добелла совпадает с полным перебором
    for N in (6, 9, 10, 12, 15, 16, 20, 30):
        for a in range(1, N):
            for c in range(N):
                th = hull_dobell(a, c, N)[3]
                real = all(find_period(x0, a, c, N)[1] == N for x0 in range(N))
                assert th == real, (N, a, c)

def t_period_n15():
    assert max(find_period(x, a, 0, 15)[1] for a in range(1, 15) for x in range(15)) == 4
    assert find_period(0, 1, 7, 15) == (0, 15)

def t_chi():
    from scipy.stats import chisquare
    seq = [i % 15 for i in range(100)] + [3] * 20
    s = chi_square_uniform(seq, 15)
    r = chisquare(s[2])
    assert abs(s[0] - r.statistic) < 1e-9 and abs(s[1] - r.pvalue) < 1e-9

def t_lehmann():
    rng = BigLCG(1)
    for n in range(3, 20000, 2):
        assert (lehmann(n, rng) == "probably prime") == isprime(n), n
    for n in (561, 1105, 1729, 2465, 2821, 6601, 8911, 10585, 15841, 29341, 41041, 46657, 52633, 62745, 63973, 75361):
        assert lehmann(n, rng) == "composite"

def t_generate():
    rng = BigLCG(123)
    for p in (16, 32, 64, 128, 256, 512):
        for _ in range(5):
            n, st = generate_prime(p, rng)
            assert n.bit_length() == p and n % 2 == 1 and isprime(n)
        n, st = generate_prime(p, rng, sequential=True)
        assert isprime(n) and n.bit_length() == p

for name, f in list(globals().items()):
    if name.startswith("t_"):
        f(); print("OK ", name)
print("Все тесты пройдены")
