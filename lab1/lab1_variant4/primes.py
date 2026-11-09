"""Этап 2. Генерация простых чисел: LFSR-кандидат + просеивание + тест Рабина-Миллера (вариант 4)."""

from __future__ import annotations
import math
import time
from dataclasses import dataclass

from lfsr import LFSR, poly_from_exponents

# Многочлен из списка методички (п. 11, №15): g(x) = x^19 + x^5 + x^2 + x + 1.
# 2^19 - 1 = 524287 простое, поэтому неприводимый многочлен степени 19 сразу примитивен.
DEFAULT_POLY = poly_from_exponents(19, 5, 2, 1, 0)


def small_primes(limit: int) -> list[int]:
    """Простые < limit (решето Эратосфена), без двойки: кандидат уже нечётный."""
    sieve = bytearray([1]) * limit
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(limit ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(3, limit) if sieve[i]]


def miller_rabin_round(n: int, a: int, s: int, t: int) -> bool:
    """Один раунд. True = "не известно" (a не свидетель), False = n точно составное."""
    x = pow(a, t, n)
    if x == 1 or x == n - 1:
        return True
    for _ in range(s - 1):
        x = x * x % n
        if x == n - 1:
            return True
    return False


def is_probable_prime(n: int, rounds: int = 5, rng: LFSR | None = None) -> bool:
    """Тест Рабина-Миллера. n - 1 = 2^s * t, t нечётное.
    Основания a берутся небольшими (< 2^16), как советует методичка."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False
    s, t = 0, n - 1
    while t % 2 == 0:
        t //= 2
        s += 1
    for r in range(rounds):
        if rng is not None:
            a = 2 + rng.random_int(16) % min(n - 3, 65535)
        else:
            a = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29][r % 10]
        if a >= n - 1:
            a = 2
        if math.gcd(a, n) != 1:            # шаги 1-2 алгоритма из методички
            return False
        if not miller_rabin_round(n, a, s, t):
            return False
    return True


@dataclass
class GenStats:
    bits: int
    sieve_limit: int
    candidates: int = 0          # всего сгенерировано кандидатов
    rejected_sieve: int = 0      # отсеяно пробными делениями
    rejected_mr: int = 0         # отсеяно тестом Рабина-Миллера
    seconds: float = 0.0
    prime: int = 0


def generate_prime(bits: int, rng: LFSR, rounds: int = 5, sieve_limit: int = 256,
                   _primes_cache: dict = {}) -> GenStats:
    if bits < 8:
        raise ValueError("bits >= 8")
    if sieve_limit not in _primes_cache:
        _primes_cache[sieve_limit] = small_primes(sieve_limit) if sieve_limit > 2 else []
    sp = _primes_cache[sieve_limit]
    st = GenStats(bits, sieve_limit)
    t0 = time.perf_counter()
    while True:
        n = rng.random_int(bits)
        n |= (1 << (bits - 1)) | 1                      # старший и младший биты = 1
        st.candidates += 1
        if any(n % p == 0 and n != p for p in sp):      # просеивание
            st.rejected_sieve += 1
            continue
        if is_probable_prime(n, rounds, rng):
            st.prime = n
            break
        st.rejected_mr += 1
    st.seconds = time.perf_counter() - t0
    return st
