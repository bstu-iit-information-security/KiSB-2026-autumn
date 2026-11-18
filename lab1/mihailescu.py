"""Метод Михалеску: генерация доказуемо простых чисел (вариант 10, e = 1/2).

Схема (m - требуемое число двоичных разрядов):
  1. m < B  -> простое число генерируется пробными делениями.
  2. Рекурсивно строим простое F длины ceil(e*m)+1 бит (2^(e m) < F < 2^(c e m)),
     его факторизация известна тривиально (F простое).
  3. Выбираем t из интервала (2^(m-2)/F, 2^(m-1)/F - s*m).
  4. Ищем простое в прогрессии  n_i = t*a + 1 + i*a,  a = 2F,  i = 0..s*m:
        этап 1 - пробные деления на простые <= A;
        этап 2 - тест Рабина–Миллера;
        доказательство - достаточное условие Поклингтона при e = 1/2:
        n - 1 = 2F(t+i), F > sqrt(n),  существует a:
        a^(n-1) = 1 (mod n)  и  НОД(a^((n-1)/F) - 1, n) = 1   =>   n простое.
Источник случайности - SG-генератор из этапа 1 (shrinking.py).
"""
import math
import time
from dataclasses import dataclass, field


def sieve(limit):
    flags = bytearray([1]) * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for i in range(2, int(limit ** 0.5) + 1):
        if flags[i]:
            flags[i * i::i] = bytearray(len(flags[i * i::i]))
    return [i for i, f in enumerate(flags) if f]


SMALL_PRIMES = sieve(2000)


def is_prime_trial(n):
    """Детерминированная проверка пробными делениями (для малых n)."""
    if n < 2:
        return False
    for p in SMALL_PRIMES:
        if p * p > n:
            return True
        if n % p == 0:
            return n == p
    d = SMALL_PRIMES[-1] + 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def has_small_factor(n, limit=2000):
    """Этап 1: делится ли n на простое число <= limit (n > limit)."""
    for p in SMALL_PRIMES:
        if p > limit:
            break
        if n % p == 0:
            return True
    return False


def rabin_miller(n, rng, rounds=5):
    """Тест Рабина–Миллера с `rounds` случайными малыми основаниями a."""
    if n < 4:
        return n in (2, 3)
    if n % 2 == 0:
        return False
    t, s = n - 1, 0
    while t % 2 == 0:
        t //= 2
        s += 1
    for _ in range(rounds):
        a = 2 + rng.randbelow(min(n - 3, 1 << 16))
        if math.gcd(a, n) != 1:
            return False
        x = pow(a, t, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def pocklington_witness(n, F):
    """Свидетель a для достаточного условия Поклингтона (F - простое, F | n-1,
    F^2 > n).  Возвращает a либо None (n составное / свидетель не найден)."""
    for a in SMALL_PRIMES[:60]:
        if a >= n:
            break
        if pow(a, n - 1, n) != 1:
            return None  # нарушена малая теорема Ферма -> n составное
        if math.gcd(pow(a, (n - 1) // F, n) - 1, n) == 1:
            return a
    return None


@dataclass
class LevelRecord:
    """Строка журнала: один уровень рекурсии."""
    m: int
    method: str = "Михалеску"
    F_bits: int = 0
    t_attempts: int = 0
    candidates: int = 0
    rej_trial: int = 0
    rej_rm: int = 0
    rej_pock: int = 0
    seconds: float = 0.0
    witness: int = 0


@dataclass
class Journal:
    levels: list = field(default_factory=list)

    def totals(self):
        return {k: sum(getattr(r, k) for r in self.levels)
                for k in ("candidates", "rej_trial", "rej_rm", "rej_pock", "seconds")}


class Mihailescu:
    def __init__(self, rng, B=32, s=4, A=2000, e=(1, 2), mr_rounds=5):
        self.rng, self.B, self.s, self.A, self.mr_rounds = rng, B, s, A, mr_rounds
        self.e_num, self.e_den = e
        if e != (1, 2):
            raise NotImplementedError("реализован вариант e = 1/2 (условие Поклингтона)")

    # --- простое малой длины: пробные деления -----------------------------------
    def _small_prime(self, m, rec):
        t0 = time.perf_counter()
        while True:
            n = (1 << (m - 1)) | self.rng.getrandbits(m - 1) | 1
            rec.candidates += 1
            if is_prime_trial(n):
                break
            rec.rej_trial += 1
        rec.seconds = time.perf_counter() - t0
        return n

    def generate(self, m, journal=None):
        """Возвращает (n, сертификат). Сертификат - цепочка шагов Поклингтона."""
        journal = journal if journal is not None else Journal()
        rec = LevelRecord(m=m)
        if m < self.B:
            rec.method = "пробные деления"
            n = self._small_prime(m, rec)
            journal.levels.append(rec)
            return n, [{"m": m, "n": n, "F": None, "t": None, "a": None}]

        # шаг 2: F - простое, длина ceil(e*m)+1  =>  F > 2^(m/2) >= sqrt(n)
        f_bits = -(-m * self.e_num // self.e_den) + 1
        F, cert = self.generate(f_bits, journal)
        rec.F_bits = f_bits

        # шаги 3–4
        steps = self.s * m
        lo = (1 << (m - 2)) // F + 1
        hi = (1 << (m - 1)) // F - steps - 1
        t0 = time.perf_counter()
        while True:
            rec.t_attempts += 1
            t = lo + self.rng.randbelow(hi - lo + 1)
            for i in range(steps + 1):
                n = 2 * F * (t + i) + 1
                rec.candidates += 1
                if has_small_factor(n, self.A):
                    rec.rej_trial += 1
                    continue
                if not rabin_miller(n, self.rng, self.mr_rounds):
                    rec.rej_rm += 1
                    continue
                a = pocklington_witness(n, F)
                if a is None:
                    rec.rej_pock += 1
                    continue
                rec.seconds = time.perf_counter() - t0
                rec.witness = a
                journal.levels.append(rec)
                return n, cert + [{"m": m, "n": n, "F": F, "t": t + i, "a": a}]


def verify_certificate(cert):
    """Независимая проверка цепочки: каждое n_k доказуемо просто."""
    first = cert[0]
    if first["F"] is not None or not is_prime_trial(first["n"]):
        return False
    for prev, step in zip(cert, cert[1:]):
        n, F, a = step["n"], step["F"], step["a"]
        if F != prev["n"]:
            return False
        if (n - 1) % F != 0 or F * F <= n:
            return False
        if pow(a, n - 1, n) != 1 or math.gcd(pow(a, (n - 1) // F, n) - 1, n) != 1:
            return False
    return True
