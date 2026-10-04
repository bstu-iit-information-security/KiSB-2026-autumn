"""Генерация простых чисел: просеивание малыми простыми + тест Рабина-Миллера.
 
Схема (по методичке):
  1. сгенерировать случайное p-битовое число n (генератор Фибоначчи);
  2. старший и младший биты = 1;
  3. проверить делимость на малые простые (< 256 или < 2000);
  4. выполнить 5 раундов теста Рабина-Миллера со случайными малыми a.
"""
from __future__ import annotations
 
import math
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Counter as CounterT, List, Optional, Tuple
 
from fibonacci import FibonacciGenerator
 
 
# ---------------------------------------------------------------- вспомогательное
def sieve(limit: int) -> List[int]:
    """Решето Эратосфена: все простые <= limit."""
    if limit < 2:
        return []
    flags = bytearray([1]) * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for i in range(2, int(limit ** 0.5) + 1):
        if flags[i]:
            flags[i * i::i] = bytearray(len(flags[i * i::i]))
    return [i for i, f in enumerate(flags) if f]
 
 
def mod_pow(base: int, exp: int, mod: int) -> int:
    """Быстрое возведение в степень по модулю (квадрат-и-умножить)."""
    result, base = 1, base % mod
    while exp > 0:
        if exp & 1:
            result = result * base % mod
        base = base * base % mod
        exp >>= 1
    return result
 
 
def theory_survival(z: int) -> float:
    """Доля нечётных чисел, не делящихся на простые < z: ~ 1.12 / ln z."""
    return 1.12 / math.log(z)
 
 
# ---------------------------------------------------------------- Рабин-Миллер
def miller_rabin(n: int, rounds: int = 5, rng: Optional[FibonacciGenerator] = None) -> bool:
    """True - n вероятно простое (ошибка <= 4^-rounds); False - n точно составное.
 
    Шаги соответствуют методичке: n-1 = 2^s * t; выбираем a, проверяем
    НОД(a, n) = 1; считаем a^t mod n; если +-1 - раунд пройден; иначе
    возводим в квадрат до появления -1.
    """
    if n < 4:
        return n >= 2
    if n % 2 == 0:
        return False
    if rng is None:
        rng = FibonacciGenerator(31, 3, 1, seed=0x5EED1234)
 
    s, t = 0, n - 1
    while t % 2 == 0:
        t //= 2
        s += 1
 
    for _ in range(rounds):
        # малое случайное a из [2, n-2] (малые a ускоряют вычисления)
        a = 2 + rng.getrandbits(16) % min(n - 3, 1 << 16)
        if math.gcd(a, n) != 1:                 # шаги 1-2
            return False
        y = mod_pow(a, t, n)                    # шаг 3
        if y == 1 or y == n - 1:                # шаг 4 -> следующий раунд
            continue
        for _ in range(s - 1):                  # шаг 5
            y = y * y % n
            if y == n - 1:
                break
            if y == 1:                          # дошли до 1 без -1
                return False
        else:
            return False                        # шаг 6: -1 не появилась
    return True                                 # шаг 7: "вероятно простое"
 
 
# ---------------------------------------------------------------- просеивание
def find_small_divisor(n: int, small_primes: List[int]) -> Optional[int]:
    """Возвращает малый простой делитель n (n != делитель) или None."""
    for p in small_primes:
        if p * p > n:
            break
        if n % p == 0:
            return p if n != p else None
    return None
 
 
# ---------------------------------------------------------------- лог поиска
@dataclass
class PrimeSearchLog:
    bits: int
    small_limit: int
    sequential: bool
    rounds: int
    candidates: int = 0
    rejected_small: int = 0
    rejected_mr: int = 0
    time_s: float = 0.0
    by_prime: CounterT[int] = field(default_factory=Counter)
 
    def summary(self) -> str:
        mode = "последовательный перебор (n += 2)" if self.sequential else "новый случайный кандидат"
        top = ", ".join(f"{p}: {c}" for p, c in sorted(self.by_prime.items())[:8])
        return (
            f"бит: {self.bits}, просеивание простыми < {self.small_limit or 'нет'}, режим: {mode}\n"
            f"кандидатов проверено: {self.candidates}\n"
            f"отсеяно делением на малые простые: {self.rejected_small}"
            f" (по первым простым -> {top})\n"
            f"отсеяно тестом Рабина-Миллера: {self.rejected_mr}\n"
            f"время: {self.time_s:.4f} с"
        )
 
 
def make_candidate(bits: int, rng: FibonacciGenerator) -> int:
    n = rng.getrandbits(bits)
    return n | (1 << (bits - 1)) | 1            # старший и младший биты = 1
 
 
def generate_prime(bits: int, rng: FibonacciGenerator, small_limit: int = 2000,
                   rounds: int = 5, sequential: bool = False) -> Tuple[int, PrimeSearchLog]:
    """Генерация вероятно простого числа из `bits` бит. Возвращает (n, лог)."""
    if bits < 16:
        raise ValueError("bits должно быть >= 16")
    small = sieve(small_limit) if small_limit else []
    log = PrimeSearchLog(bits, small_limit, sequential, rounds)
    start = time.perf_counter()
 
    n = make_candidate(bits, rng)
    while True:
        log.candidates += 1
        d = find_small_divisor(n, small)
        if d is not None:
            log.rejected_small += 1
            log.by_prime[d] += 1
        elif not miller_rabin(n, rounds, rng):
            log.rejected_mr += 1
        else:
            break
        n += 2 if sequential else 0
        if not sequential or n.bit_length() > bits:
            n = make_candidate(bits, rng)
 
    log.time_s = time.perf_counter() - start
    return n, log
 
