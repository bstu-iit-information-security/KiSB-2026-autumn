import random
from math import gcd

def sieve(limit):
    """Решето Эратосфена (массив простых чисел до limit)."""
    s = [True] * (limit + 1)
    s[0] = s[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if s[i]:
            for j in range(i*i, limit + 1, i):
                s[j] = False
    return [i for i, v in enumerate(s) if v]

# ВОТ ЭТА СТРОЧКА БЫЛА ПРОПУЩЕНА:
SMALL_PRIMES = sieve(2000)

def trial_division(n):
    """Пробные деления на малые простые. True, если n не делится ни на одно."""
    for p in SMALL_PRIMES:
        if p * p > n:
            return True
        if n % p == 0:
            return n == p
    return True

def miller_rabin(n, k=20):
    """Вероятностный тест Рабина-Миллера (быстрый фильтр)."""
    if n < 2: return False
    if n in (2, 3): return True
    if n % 2 == 0: return False
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2; s += 1
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def factor_small(n):
    """Факторизация числа n с помощью массива SMALL_PRIMES."""
    f = {}
    for p in SMALL_PRIMES:
        if p * p > n: break
        while n % p == 0:
            f[p] = f.get(p, 0) + 1
            n //= p
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f