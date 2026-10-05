#!/usr/bin/env python3
"""Лабораторная №1, вариант 11. Самостоятельный файл; только стандартная библиотека."""

# Алгоритмы
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


# Эксперименты
from pathlib import Path
import csv
import json
import platform
import sys
from datetime import datetime, timezone

CASES = [
    ('c0_best', Parameters(5, 2, 0, 1)),
    ('c0_zero_seed', Parameters(5, 2, 0, 0)),
    ('mixed_best', Parameters()),
    ('mixed_seed7', Parameters(seed=7)),
    ('mixed_c2', Parameters(5, 6, 2, 0)),
    ('nonlinear_short', Parameters(1, 1, 1, 0)),
]


def run(directory='results', include_32=False):
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    with (target / 'period_search.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['d', 'a', 'c', 'seed', 'transient', 'period'])
        for d in range(1, 10):
            for a in range(10):
                for c in range(10):
                    for seed in range(10):
                        cy = cycle(Parameters(d, a, c, seed))
                        writer.writerow([d, a, c, seed, cy.transient, cy.period])
    print('Полный перебор 9000 конфигураций завершён.', flush=True)
    with (target / 'statistics.csv').open('w', newline='') as f, (target / 'pairs.csv').open('w', newline='') as pf:
        writer, pair_writer = csv.writer(f), csv.writer(pf)
        writer.writerow(['case', 'd', 'a', 'c', 'seed', 'length', 'transient', 'period', 'chi_square', 'entropy',
                         'serial_correlation', 'pair_chi_square'] + [f'count_{i}' for i in range(10)])
        pair_writer.writerow(['case', 'first', 'second', 'count'])
        for name, params in CASES:
            for length in (100, 1000, 10000):
                s, cy = statistics(params, length), cycle(params)
                writer.writerow([name, params.d, params.a, params.c, params.seed, length, cy.transient, cy.period,
                                 s.chi_square, s.entropy, s.serial_correlation, s.pair_chi_square] + s.counts)
                if length == 10000:
                    pair_writer.writerows([name, x, y, s.pairs[10*x+y]] for x in range(10) for y in range(10))
    with (target / 'prime_generation.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['bits', 'seed', 'sieve_bound', 'start', 'prime', 'candidates', 'sieve_rejected',
                         'aks_rejected', 'aks_calls', 'elapsed_ms'])
        for bits in (8, 10, 12, 16):
            for sieve in (0, 256, 2000):
                with (target / f'candidates_{bits}bit_sieve{sieve}.csv').open('w', newline='') as log:
                    result = generate(Parameters(), bits, sieve, log=log)
                if not result.found or not trial_prime(result.prime):
                    raise RuntimeError('Генерация не завершилась проверенным простым числом.')
                writer.writerow([bits, 0, sieve, result.start, result.prime, result.candidates,
                                 result.sieve_rejected, result.aks_rejected, result.aks_calls, f'{result.elapsed_ms:.6f}'])
                print(f'{bits} бит, просев {sieve}: p={result.prime}, кандидатов={result.candidates}, '
                      f'{result.elapsed_ms:.2f} мс', flush=True)
    if include_32:
        print('Выполняется отдельный 32-битный запуск...', flush=True)
        with (target / 'check_32bit.csv').open('w', newline='') as log:
            result = generate(Parameters(), 32, 256, log=log)
        if not result.found or not trial_prime(result.prime):
            raise RuntimeError('Ошибка 32-битной генерации.')
        # Keep the same plain-text data format as CLI; no dependency on CLI module.
        summary = ' '.join(f'{key}={int(value) if isinstance(value, bool) else value}' for key, value in vars(result).items())
        (target / 'check_32bit_summary.txt').write_text(summary + '\n')
        print(summary, flush=True)
    environment = {'implementation': 'Python', 'python': sys.version, 'platform': platform.platform(),
                   'machine': platform.machine(), 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                   'include_32': include_32}
    (target / 'environment.json').write_text(json.dumps(environment, ensure_ascii=False, indent=2) + '\n')


# Консольный интерфейс
import argparse
import sys
from time import perf_counter


def parser():
    result = argparse.ArgumentParser(description='ЛР №1, вариант 11: генератор N=10 и тест AKS (Python).')
    commands = result.add_subparsers(dest='command', required=True)
    for name in ('sequence', 'stats'):
        command = commands.add_parser(name, help='Последовательность' if name == 'sequence' else 'Статистика')
        command.add_argument('length', type=int)
        command.add_argument('parameters', nargs='*', type=int, metavar='d a c x0')
    check = commands.add_parser('check', help='Проверка числа на простоту')
    check.add_argument('n', type=int)
    generation = commands.add_parser('generate', help='Поиск простого числа заданной разрядности')
    generation.add_argument('bits', type=int)
    generation.add_argument('seed', nargs='?', type=int, default=0)
    generation.add_argument('sieve', nargs='?', type=int, default=256)
    generation.add_argument('attempts', nargs='?', type=int, default=100000)
    experiment = commands.add_parser('experiments', help='Воспроизвести измерения и CSV')
    experiment.add_argument('directory', nargs='?', default='results')
    experiment.add_argument('--include-32', action='store_true', help='Добавить 32-битный контрольный запуск')
    return result


def demonstration():
    """Запуск всей лабораторной кнопкой Run Python File без аргументов."""
    print('Лабораторная работа №1 — вариант 11\nСавинец М. Д., группа АС-66', flush=True)
    for title, arguments in (
        ('1. Последовательность: c=0, период 4', ['sequence', '20', '5', '2', '0', '1']),
        ('2. Последовательность: c=1, период 10', ['sequence', '20']),
        ('3. Статистика для 10000 чисел', ['stats', '10000']),
        ('4. Проверка простого числа 997 методом AKS', ['check', '997']),
        ('5. Проверка составного числа 1001 методом AKS', ['check', '1001']),
        ('6. Генерация 16-битного простого числа', ['generate', '16']),
    ):
        print('\n' + title, flush=True)
        status = main(arguments)
        if status:
            return status
    directory = Path(__file__).resolve().parent / 'results' / 'latest_run'
    print('\n7. Эксперименты: все 9000 конфигураций, статистика и генерация простых', flush=True)
    status = main(['experiments', str(directory)])
    if status:
        return status
    print('\nЛабораторная выполнена. Результаты этого запуска: ' + str(directory), flush=True)
    print('32-битное измерение запускается отдельно: python3 lab1.py experiments results --include-32')
    return 0


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        return demonstration()
    command_parser = parser()
    args = command_parser.parse_args(arguments)
    try:
        if args.command in ('sequence', 'stats'):
            if args.length < 1 or len(args.parameters) not in (0, 4):
                raise ValueError('Нужна положительная длина и либо 0, либо 4 параметра: d a c x0.')
            p = Parameters(*args.parameters) if args.parameters else Parameters()
            if args.command == 'sequence':
                for i, value in enumerate(Generator(p).sequence(args.length), 1):
                    print(value, end='\n' if i % 40 == 0 or i == args.length else ' ')
            else:
                s, cy = statistics(p, args.length), cycle(p)
                print(f'transient={cy.transient} period={cy.period} chi_square={s.chi_square:.6f} '
                      f'entropy_bits={s.entropy:.6f} pair_chi_square={s.pair_chi_square:.6f}')
                print('serial_correlation=' + ('undefined' if s.serial_correlation is None else f'{s.serial_correlation:.6f}'))
                print('digit,count')
                for digit, count in enumerate(s.counts):
                    print(f'{digit},{count}')
        elif args.command == 'check':
            begin = perf_counter()
            result = aks(args.n)
            print(f'n={args.n} verdict={result.verdict} reason={result.reason} r={result.r} '
                  f'polynomial_checks={result.checks} witness={result.witness} elapsed_ms={(perf_counter()-begin)*1000:.6f}')
            if result.verdict == 'capacity_exceeded':
                return 4
        elif args.command == 'generate':
            result = generate(Parameters(seed=args.seed), args.bits, args.sieve, args.attempts, sys.stdout)
            print(summary(result), file=sys.stderr)
            if not result.found:
                return 4 if result.capacity_error else 5
        else:
            run(args.directory, args.include_32)
        sys.stdout.flush()
        return 0
    except ValueError as error:
        command_parser.error(str(error))
    except OSError as error:
        print(f'Ошибка ввода/вывода: {error}', file=sys.stderr)
        return 3
    except RuntimeError as error:
        print(f'Ошибка вычисления: {error}', file=sys.stderr)
        return 4


def summary(result):
    return (f'found={int(result.found)} prime={result.prime} start={result.start} candidates={result.candidates} '
            f'sieve_rejected={result.sieve_rejected} aks_rejected={result.aks_rejected} '
            f'aks_calls={result.aks_calls} elapsed_ms={result.elapsed_ms:.6f}')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nВыполнение остановлено.', file=sys.stderr)
        raise SystemExit(130)
