"""
Модуль решета Эратосфена и предварительного просеивания (пробных делений)
на малые простые числа.
"""

from typing import List, Tuple, Optional


def sieve_eratosthenes(limit: int = 256) -> List[int]:
    """
    Решето Эратосфена: генерация списка простых чисел, не превосходящих limit.
    Для limit=256 возвращает список из 54 простых чисел (от 2 до 251).
    """
    if limit < 2:
        return []
    is_prime = bytearray([1]) * (limit + 1)
    is_prime[0:2] = b"\x00\x00"
    for p in range(2, int(limit ** 0.5) + 1):
        if is_prime[p]:
            is_prime[p * p : limit + 1 : p] = b"\x00" * (((limit - p * p) // p) + 1)
    return [i for i, val in enumerate(is_prime) if val]


# Глобальный кэш малых простых чисел до 256 (согласно заданию лаб. работы)
SMALL_PRIMES_256: List[int] = sieve_eratosthenes(256)


def trial_division_filter(n: int, primes_list: Optional[List[int]] = None) -> Tuple[bool, Optional[int]]:
    """
    Предварительное просеивание: проверка делимости кандидата n на малые простые числа.

    Отсекает ~80% нечетных составных чисел до запуска вычислительно тяжелых тестов.

    :param n: Проверяемое нечетное натуральное число.
    :param primes_list: Список простых делителей (по умолчанию SMALL_PRIMES_256).
    :return: (passed, divisor) — passed=True, если число пережило сито;
             если составное — passed=False и divisor равен первому найденному делителю.
    """
    if n < 2:
        return False, None
    if primes_list is None:
        primes_list = SMALL_PRIMES_256

    for p in primes_list:
        if n == p:
            return True, None
        if n % p == 0:
            return False, p
    return True, None

