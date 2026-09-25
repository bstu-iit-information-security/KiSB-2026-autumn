"""
Схема генерации кандидата в простые числа и его проверки (методичка ЛР №6,
Задание, п.1).

generate_prime() не привязан к конкретному источнику случайности - он
принимает make_candidate: Callable[[], int], возвращающий очередное p-битное
нечётное число со старшим битом=1. Это позволяет:
  - naive_candidate_factory   - "буквальная" схема прямо на генераторе
    Этапа 1 (используется, чтобы явно показать нехватку его периода);
  - seeded_candidate_factory  - практическая схема для реальных разрядностей
    (генератор Этапа 1 используется как источник сида, см. src/rng/seeding.py).
"""
from __future__ import annotations

import time
from typing import Callable, Protocol

from .sieve import trial_division_ok
from .solovay_strassen import is_probable_prime


class DigitGenerator(Protocol):
    def next(self) -> int: ...


class BitRandom(Protocol):
    def getrandbits(self, k: int) -> int: ...
    def randrange(self, a: int, b: int) -> int: ...


def naive_candidate_factory(gen: DigitGenerator, p: int) -> Callable[[], int]:
    """
    "Буквальная" схема: бит = чётность очередной цифры генератора Этапа 1
    (среди цифр 0-9 ровно 5 чётных и 5 нечётных => бит равновероятен).
    Годится, только пока период генератора Этапа 1 намного больше p (см.
    tests/test_candidate.py::test_variant1_generator_too_short_for_large_candidates).
    """
    if p < 2:
        raise ValueError("p должно быть не меньше 2")

    def make_candidate() -> int:
        bits = [gen.next() % 2 for _ in range(p)]
        bits[0] = 1
        bits[-1] = 1
        n = 0
        for b in bits:
            n = (n << 1) | b
        return n

    return make_candidate


def seeded_candidate_factory(rng: BitRandom, p: int) -> Callable[[], int]:
    """
    Практическая схема для Этапа 2: p-битный кандидат из качественного
    генератора битов rng (например, random.Random, засеянного значением от
    генератора Этапа 1 - см. src/rng/seeding.py::build_stage2_rng).
    """
    if p < 2:
        raise ValueError("p должно быть не меньше 2")

    def make_candidate() -> int:
        n = rng.getrandbits(p)
        n |= 1 << (p - 1)  # старший бит
        n |= 1              # младший бит
        return n

    return make_candidate


def generate_prime(
    make_candidate: Callable[[], int],
    p: int,
    ss_rounds: int = 5,
    rng: BitRandom | None = None,
    log: list[dict] | None = None,
    max_attempts: int = 1_000_000,
) -> int:
    """
    Полная схема (методичка ЛР №6, Задание п.1):
      1. p-битный кандидат из make_candidate();
      2. просеивание пробным делением на простые < 2000;
      3. финальная проверка тестом Соловея-Штрассена (rounds=ss_rounds).

    Если передан список `log`, в него добавляется диагностическая запись:
    число попыток, сколько кандидатов отсеяно пробным делением, время работы.
    """
    attempts = 0
    sieved_out = 0
    t0 = time.perf_counter()
    while attempts < max_attempts:
        attempts += 1
        n = make_candidate()
        if not trial_division_ok(n):
            sieved_out += 1
            continue
        if is_probable_prime(n, rounds=ss_rounds, rng=rng):
            elapsed = time.perf_counter() - t0
            if log is not None:
                log.append(
                    {
                        "n": n,
                        "bits": p,
                        "attempts": attempts,
                        "sieved_out": sieved_out,
                        "elapsed_sec": elapsed,
                    }
                )
            return n
    raise RuntimeError(f"Не удалось найти простое число за {max_attempts} попыток")
