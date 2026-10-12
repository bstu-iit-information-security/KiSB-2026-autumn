"""
Просеивание кандидатов пробным делением на малые простые числа
(методичка ЛР №6, п. "Этап 1: пробные деления на простые числа, не превосходящие A").
Список простых до 256 приведён в методичке явно; до 2000 - решетом Эратосфена.
"""
from __future__ import annotations


def sieve_of_eratosthenes(limit: int) -> list[int]:
    """Решето Эратосфена (§6.2): все простые числа, не превосходящие limit."""
    if limit < 2:
        return []
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    p = 2
    while p * p <= limit:
        if is_prime[p]:
            for multiple in range(p * p, limit + 1, p):
                is_prime[multiple] = False
        p += 1
    return [i for i, prime in enumerate(is_prime) if prime]


# Явно приведённые в методичке (до 256) - используем как контрольный список.
SMALL_PRIMES_256 = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79,
    83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157,
    163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239,
    241, 251,
]

assert SMALL_PRIMES_256 == sieve_of_eratosthenes(256), (
    "Список малых простых из методички разошёлся с решетом Эратосфена"
)

# Наиболее эффективный вариант отсева по методичке - деление на все простые < 2000.
SMALL_PRIMES_2000 = sieve_of_eratosthenes(2000)


def trial_division_ok(n: int, primes: list[int] | None = None) -> bool:
    """
    True, если n не делится ни на одно малое простое число из списка
    (кроме случая, когда n само является этим простым числом).
    """
    primes = primes if primes is not None else SMALL_PRIMES_2000
    for p in primes:
        if n == p:
            return True
        if n % p == 0:
            return False
    return True
