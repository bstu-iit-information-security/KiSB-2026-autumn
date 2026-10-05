"""Генератор по модулю 10, статистика, полиномиальный тест AKS и поиск простых.

Все численные алгоритмы реализованы здесь на Python. Никаких вызовов C++,
SymPy, готовых функций проверки простоты или вероятностных замен AKS нет.
Python выделяет память динамически и не обеспечивает constant-time.
"""
from dataclasses import dataclass, field
from math import gcd, isqrt, log2, sqrt
from time import perf_counter
from typing import Optional, TextIO
import csv

MAX_BITS = 32
MAX_R = 4096


@dataclass(frozen=True)
class Parameters:
    d: int = 5
    a: int = 6
    c: int = 1
    seed: int = 0

    def __post_init__(self):
        values = (self.d, self.a, self.c, self.seed)
        if any(type(value) is not int for value in values):
            raise ValueError('Параметры должны быть целыми числами.')
        if not (1 <= self.d <= 9 and all(0 <= x <= 9 for x in values[1:])):
            raise ValueError('Требуются d=1..9, a,c,x0=0..9.')


class Generator:
    """Потоковый генератор: x0 — начальное состояние, первый выход — x1."""

    def __init__(self, params: Parameters = Parameters()):
        self.params = params
        self.state = params.seed

    def next(self) -> int:
        p, x = self.params, self.state
        self.state = (p.d * x * x + p.a * x + p.c) % 10
        return self.state

    def sequence(self, length: int):
        if type(length) is not int or length < 0:
            raise ValueError('Длина должна быть неотрицательным целым числом.')
        for _ in range(length):
            yield self.next()


@dataclass(frozen=True)
class Cycle:
    transient: int
    period: int


def cycle(params: Parameters) -> Cycle:
    seen = [-1] * 10
    generator = Generator(params)
    count = 0
    while seen[generator.state] < 0:
        seen[generator.state] = count
        count += 1
        generator.next()
    transient = seen[generator.state]
    return Cycle(transient, count - transient)


@dataclass
class Statistics:
    counts: list = field(default_factory=lambda: [0] * 10)
    pairs: list = field(default_factory=lambda: [0] * 100)
    chi_square: float = 0.0
    pair_chi_square: float = 0.0
    entropy: float = 0.0
    serial_correlation: Optional[float] = None


def statistics(params: Parameters, length: int) -> Statistics:
    if type(length) is not int or length < 1:
        raise ValueError('Для статистики нужна положительная целая длина.')
    result = Statistics()
    previous = None
    sx = sy = sxx = syy = sxy = 0
    for value in Generator(params).sequence(length):
        result.counts[value] += 1
        if previous is not None:
            result.pairs[previous * 10 + value] += 1
            sx += previous
            sy += value
            sxx += previous * previous
            syy += value * value
            sxy += previous * value
        previous = value
    expected = length / 10
    result.chi_square = sum((count - expected) ** 2 / expected for count in result.counts)
    result.entropy = -sum((count / length) * log2(count / length) for count in result.counts if count)
    if length > 1:
        pairs = length - 1
        expected = pairs / 100
        result.pair_chi_square = sum((count - expected) ** 2 / expected for count in result.pairs)
        denominator_squared = (pairs * sxx - sx * sx) * (pairs * syy - sy * sy)
        if denominator_squared > 0:
            result.serial_correlation = (pairs * sxy - sx * sy) / sqrt(denominator_squared)
    return result


def trial_prime(n: int) -> bool:
    """Независимый эталон для тестов и построения таблицы малых простых."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    return all(n % d for d in range(3, isqrt(n) + 1, 2))


def perfect_power(n: int) -> bool:
    """Точная проверка n=a**b без округлений вещественных корней."""
    if n < 4:
        return False
    for exponent in range(2, n.bit_length()):
        low, high = 2, 1 << ((n.bit_length() + exponent - 1) // exponent)
        while low <= high:
            middle = (low + high) // 2
            value = middle ** exponent
            if value == n:
                return True
            if value < n:
                low = middle + 1
            else:
                high = middle - 1
    return False


def multiply(left: list, right: list, n: int) -> list:
    """Точная циклическая свёртка в (Z/nZ)[X]/(X**r-1).

    Подстановка Кронекера: коэффициенты упакованы в цифры большого целого.
    Основание Q строго больше r*(n-1)**2, поэтому переносов между
    коэффициентами обычного полиномиального произведения нет.
    Умножение Python int вычисляет эту свёртку, после распаковки старшие
    степени складываются с младшими (X**r=1), коэффициенты сокращаются по n.
    """
    r = len(left)
    if not 2 <= r <= MAX_R or len(right) != r or type(n) is not int or n < 2:
        raise ValueError('Нужны 2<=r<=4096, одинаковые длины полиномов и n>=2.')
    if any(type(c) is not int or not 0 <= c < n for c in left + right):
        raise ValueError('Коэффициенты должны быть целыми вычетами 0..n-1.')
    width = ((r * (n - 1) ** 2).bit_length() + 7) // 8
    packed_left = int.from_bytes(b''.join(c.to_bytes(width, 'little') for c in left), 'little')
    packed_right = int.from_bytes(b''.join(c.to_bytes(width, 'little') for c in right), 'little')
    raw = (packed_left * packed_right).to_bytes(2 * r * width, 'little')
    ordinary = [int.from_bytes(raw[i:i + width], 'little') for i in range(0, len(raw), width)]
    return [(ordinary[k] + ordinary[k + r]) % n for k in range(r)]


def polynomial_congruence(n: int, r: int, a: int) -> bool:
    if n < 2 or not 2 <= r <= MAX_R:
        raise ValueError('Нужны n>=2 и 2<=r<=4096.')
    result = [1] + [0] * (r - 1)
    a %= n
    for bit in bin(n)[2:]:
        result = multiply(result, result, n)
        if bit == '1':
            # Умножение на X+a — сдвиг и масштабирование, O(r).
            result = [(a * result[k] + result[k - 1]) % n for k in range(r)]
    expected = [0] * r
    expected[0] = a
    expected[n % r] = (expected[n % r] + 1) % n
    return result == expected


def phi(n: int) -> int:
    value = n
    p = 2
    while p * p <= n:
        if n % p == 0:
            while n % p == 0:
                n //= p
            value -= value // p
        p += 1
    if n > 1:
        value -= value // n
    return value


@dataclass
class PrimeResult:
    verdict: str = 'composite'
    reason: str = 'below_two'
    r: int = 0
    checks: int = 0
    witness: int = 0


def aks(n: int, capacity: int = MAX_R) -> PrimeResult:
    if type(n) is not int or not 0 <= n < 1 << MAX_BITS:
        raise ValueError('Поддерживается диапазон 0..4294967295.')
    if type(capacity) is not int or not 2 <= capacity <= MAX_R:
        raise ValueError('Ёмкость r должна быть в диапазоне 2..4096.')
    if n < 2:
        return PrimeResult()
    if perfect_power(n):
        return PrimeResult(reason='perfect_power')
    bits = (n - 1).bit_length()  # ceil(log2(n)), точная целая граница.
    order_bound = bits * bits
    for r in range(2, capacity + 1):
        divisor = gcd(n, r)
        if 1 < divisor < n:
            return PrimeResult(reason='gcd_factor', r=r, witness=divisor)
        if n == r:
            return PrimeResult('prime', 'small_prime', r)
        if divisor != 1:
            continue
        value = 1
        for _ in range(order_bound):
            value = value * n % r
            if value == 1:
                break
        else:
            break
    else:
        return PrimeResult('capacity_exceeded', 'r_capacity')
    totient = phi(r)
    root = isqrt(totient)
    limit = (root + (root * root < totient)) * bits
    for a in range(1, limit + 1):
        if not polynomial_congruence(n, r, a):
            return PrimeResult(reason='polynomial_witness', r=r, checks=a, witness=a)
    return PrimeResult('prime', 'aks_proven', r, limit)


def candidate(generator: Generator, bits: int) -> int:
    if type(bits) is not int or not 2 <= bits <= MAX_BITS:
        raise ValueError('Разрядность должна быть от 2 до 32.')
    value = 0
    for _ in range(bits):
        value = (value << 1) | int(generator.next() >= 5)
    return value | (1 << (bits - 1)) | 1


@dataclass
class Generation:
    found: bool = False
    capacity_error: bool = False
    start: int = 0
    prime: int = 0
    candidates: int = 0
    sieve_rejected: int = 0
    aks_rejected: int = 0
    aks_calls: int = 0
    elapsed_ms: float = 0.0


def generate(params: Parameters, bits: int, sieve_bound: int = 256,
             attempts: int = 100000, log: Optional[TextIO] = None) -> Generation:
    if type(sieve_bound) is not int or not 0 <= sieve_bound <= 2000:
        raise ValueError('Граница просеивания должна быть от 0 до 2000.')
    if type(attempts) is not int or attempts < 1:
        raise ValueError('Лимит попыток должен быть положительным целым числом.')
    n = candidate(Generator(params), bits)
    small_primes = [p for p in range(2, sieve_bound + 1) if trial_prime(p)]
    out = Generation(start=n)
    begin = perf_counter()
    writer = csv.writer(log, lineterminator='\n') if log is not None else None
    if writer:
        writer.writerow(['index', 'candidate', 'status', 'divisor', 'r', 'polynomial_checks', 'candidate_ms', 'elapsed_ms'])
    highest, lowest = (1 << bits) - 1, (1 << (bits - 1)) | 1
    for _ in range(min(attempts, 1 << (bits - 2))):
        candidate_begin = perf_counter()
        out.candidates += 1
        divisor = next((p for p in small_primes if n != p and n % p == 0), 0)
        result = PrimeResult()
        if divisor:
            status = 'sieve_rejected'
            out.sieve_rejected += 1
        else:
            out.aks_calls += 1
            result = aks(n)
            status = result.verdict
            if status == 'prime':
                out.found, out.prime = True, n
            elif status == 'composite':
                out.aks_rejected += 1
            else:
                out.capacity_error = True
        if writer:
            writer.writerow([out.candidates, n, status, divisor, result.r, result.checks,
                             f'{(perf_counter()-candidate_begin)*1000:.6f}', f'{(perf_counter()-begin)*1000:.6f}'])
        if out.found or out.capacity_error:
            break
        n = lowest if n + 2 > highest else n + 2
    out.elapsed_ms = (perf_counter() - begin) * 1000
    return out
