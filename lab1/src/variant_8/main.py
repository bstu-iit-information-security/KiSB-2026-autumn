"""ЛР №1, вариант 8: аддитивный генератор и тест Ферма.

Запуск:
    python main.py all
    python main.py analyze
    python main.py prime --bits 32 --rounds 10
    python main.py test

Программа использует только стандартную библиотеку Python.
"""

from __future__ import annotations

import argparse
import csv
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


MODULUS = 30
DEFAULT_SEED = (0, 1)
RESULTS_DIR = Path(__file__).resolve().parent / "results"


class AdditiveGenerator:
    """Аддитивный генератор варианта 8.

    x[t+1] = (x[t] + x[t-1]) mod N, где N = 30.
    """

    def __init__(self, x0: int = 0, x1: int = 1, modulus: int = MODULUS) -> None:
        if modulus < 2:
            raise ValueError("Модуль N должен быть не меньше 2.")
        self.modulus = modulus
        self.previous = x0 % modulus
        self.current = x1 % modulus

    def next(self) -> int:
        """Вернуть очередной элемент последовательности."""
        value = self.previous
        self.previous, self.current = self.current, (self.previous + self.current) % self.modulus
        return value

    def sequence(self, length: int) -> list[int]:
        if length < 0:
            raise ValueError("Длина последовательности не может быть отрицательной.")
        return [self.next() for _ in range(length)]


def period_length(x0: int, x1: int, modulus: int = MODULUS) -> int:
    """Найти период по повторению состояния (x[t-1], x[t])."""
    generator = AdditiveGenerator(x0, x1, modulus)
    start_state = (generator.previous, generator.current)
    period = 0
    while True:
        generator.next()
        period += 1
        if (generator.previous, generator.current) == start_state:
            return period


def find_max_period(modulus: int = MODULUS) -> tuple[int, list[tuple[int, int]]]:
    """Перебрать все начальные пары и найти фактический максимум периода."""
    maximum = 0
    seeds: list[tuple[int, int]] = []
    for x0 in range(modulus):
        for x1 in range(modulus):
            current_period = period_length(x0, x1, modulus)
            if current_period > maximum:
                maximum = current_period
                seeds = [(x0, x1)]
            elif current_period == maximum:
                seeds.append((x0, x1))
    return maximum, seeds


def randbelow(generator: AdditiveGenerator, upper_bound: int) -> int:
    """Случайное число [0, upper_bound) из цифр генератора, без смещения."""
    if upper_bound <= 0:
        raise ValueError("Верхняя граница должна быть положительной.")

    base = generator.modulus
    range_size = 1
    while range_size < upper_bound:
        range_size *= base

    accepted_limit = range_size - range_size % upper_bound
    while True:
        value = 0
        remaining = range_size
        while remaining > 1:
            value = value * base + generator.next()
            remaining //= base
        if value < accepted_limit:
            return value % upper_bound


def random_odd_candidate(bits: int, generator: AdditiveGenerator) -> int:
    """Создать нечётный кандидат точно заданной битовой длины."""
    if bits < 3:
        raise ValueError("Для генерации кандидата нужно не менее 3 бит.")
    middle = randbelow(generator, 1 << (bits - 2))
    return (1 << (bits - 1)) | (middle << 1) | 1


def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)


@dataclass(frozen=True)
class FermatResult:
    is_probable_prime: bool
    tested_bases: tuple[int, ...]
    reason: str


def fermat_test(n: int, rounds: int, generator: AdditiveGenerator) -> FermatResult:
    """Вероятностный тест на основе малой теоремы Ферма.

    При нахождении свидетеля составности возвращает False. Если все раунды
    пройдены, число называется *вероятно простым*, а не доказанно простым.
    """
    if n < 2:
        return FermatResult(False, (), "n < 2")
    if n in (2, 3):
        return FermatResult(True, (), "малое простое число")
    if n % 2 == 0:
        return FermatResult(False, (), "чётное число")
    if rounds < 1:
        raise ValueError("Число раундов должно быть не меньше 1.")

    bases: list[int] = []
    for _ in range(rounds):
        a = randbelow(generator, n - 3) + 2  # 2 <= a <= n - 2
        bases.append(a)
        if gcd(a, n) != 1:
            return FermatResult(False, tuple(bases), f"НОД({a}, n) != 1")
        if pow(a, n - 1, n) != 1:
            return FermatResult(False, tuple(bases), f"основание {a} - свидетель составности")
    return FermatResult(True, tuple(bases), "все раунды Ферма пройдены")


def small_primes(limit: int = 256) -> list[int]:
    sieve = [True] * (limit + 1)
    sieve[0:2] = [False, False]
    for value in range(2, math.isqrt(limit) + 1):
        if sieve[value]:
            sieve[value * value : limit + 1 : value] = [False] * len(sieve[value * value : limit + 1 : value])
    return [value for value, is_prime in enumerate(sieve) if is_prime]


SMALL_PRIMES = small_primes()


@dataclass(frozen=True)
class PrimeSearchResult:
    candidate: int
    bits: int
    attempts: int
    sifted_out: int
    fermat_rejections: int
    elapsed_seconds: float
    fermat: FermatResult


def passes_small_prime_sieve(candidate: int) -> bool:
    for prime in SMALL_PRIMES:
        if candidate == prime:
            return True
        if candidate % prime == 0:
            return False
    return True


def generate_probable_prime(bits: int, rounds: int, seed: tuple[int, int] = DEFAULT_SEED) -> PrimeSearchResult:
    """Искать p-битный вероятно простой кандидат с предварительным просеиванием."""
    generator = AdditiveGenerator(*seed)
    attempts = sifted_out = fermat_rejections = 0
    started = time.perf_counter()

    while True:
        attempts += 1
        candidate = random_odd_candidate(bits, generator)
        if not passes_small_prime_sieve(candidate):
            sifted_out += 1
            continue

        result = fermat_test(candidate, rounds, generator)
        if result.is_probable_prime:
            return PrimeSearchResult(
                candidate=candidate,
                bits=bits,
                attempts=attempts,
                sifted_out=sifted_out,
                fermat_rejections=fermat_rejections,
                elapsed_seconds=time.perf_counter() - started,
                fermat=result,
            )
        fermat_rejections += 1


def chi_square_uniformity(sequence: list[int], modulus: int = MODULUS) -> float:
    expected = len(sequence) / modulus
    counts = Counter(sequence)
    return sum((counts[value] - expected) ** 2 / expected for value in range(modulus))


def write_svg_bar_chart(frequencies: Counter[int], total: int, output: Path) -> None:
    """Сохранить простую SVG-гистограмму без внешних библиотек."""
    width, height = 1100, 520
    left, bottom, top = 65, 60, 55
    chart_height = height - bottom - top
    max_frequency = max(frequencies.values(), default=1)
    bar_width = 28
    gap = 6
    bars: list[str] = []
    labels: list[str] = []
    for value in range(MODULUS):
        frequency = frequencies[value]
        bar_height = frequency / max_frequency * chart_height
        x = left + value * (bar_width + gap)
        y = height - bottom - bar_height
        bars.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" fill="#2563eb"/>')
        labels.append(f'<text x="{x + bar_width / 2:.1f}" y="{height - 35}" text-anchor="middle">{value}</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="white"/>
  <style>text {{ font-family: Arial, sans-serif; font-size: 12px; fill: #111827; }}</style>
  <text x="{width / 2}" y="28" text-anchor="middle" font-size="18">Частоты значений аддитивного генератора (N=30, длина={total})</text>
  <line x1="{left}" y1="{height - bottom}" x2="{width - 30}" y2="{height - bottom}" stroke="#111827"/>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#111827"/>
  {''.join(bars)}
  {''.join(labels)}
  <text x="{width / 2}" y="{height - 8}" text-anchor="middle">Значение последовательности</text>
  <text x="18" y="{height / 2}" transform="rotate(-90 18 {height / 2})" text-anchor="middle">Частота</text>
</svg>'''
    output.write_text(svg, encoding="utf-8")


def run_analysis(length: int = 600) -> dict[str, object]:
    RESULTS_DIR.mkdir(exist_ok=True)
    generator = AdditiveGenerator(*DEFAULT_SEED)
    sequence = generator.sequence(length)
    frequencies = Counter(sequence)
    period = period_length(*DEFAULT_SEED)
    maximum_period, maximum_period_seeds = find_max_period()
    chi_square = chi_square_uniformity(sequence)

    with (RESULTS_DIR / "sequence.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["index", "value"])
        writer.writerows(enumerate(sequence))

    with (RESULTS_DIR / "frequency_table.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["value", "frequency", "relative_frequency"])
        for value in range(MODULUS):
            writer.writerow([value, frequencies[value], f"{frequencies[value] / length:.6f}"])

    # Варианты с разными периодами: это материал для вывода в отчёте о
    # влиянии начальных значений на свойства последовательности.
    seed_pairs = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 5), (0, 6), (10, 10), (15, 15)]
    with (RESULTS_DIR / "period_comparison.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["x0", "x1", "period"])
        for x0, x1 in seed_pairs:
            writer.writerow([x0, x1, period_length(x0, x1)])

    write_svg_bar_chart(frequencies, length, RESULTS_DIR / "frequency_chart.svg")

    summary = (
        "АНАЛИЗ АДДИТИВНОГО ГЕНЕРАТОРА, ВАРИАНТ 8\n"
        f"Формула: x[t+1] = (x[t] + x[t-1]) mod {MODULUS}\n"
        f"Начальные значения: x0={DEFAULT_SEED[0]}, x1={DEFAULT_SEED[1]}\n"
        f"Длина выборки: {length}\n"
        f"Период: {period}\n"
        f"Максимальный период, найденный перебором всех 900 начальных пар: {maximum_period}\n"
        f"Количество пар с максимальным периодом: {len(maximum_period_seeds)}\n"
        f"Покрыто значений алфавита: {len(frequencies)} из {MODULUS}\n"
        f"Критерий хи-квадрат: {chi_square:.4f}\n"
        "Файлы: sequence.csv, frequency_table.csv, period_comparison.csv, frequency_chart.svg\n"
    )
    (RESULTS_DIR / "analysis_summary.txt").write_text(summary, encoding="utf-8")
    return {
        "period": period,
        "maximum_period": maximum_period,
        "chi_square": chi_square,
        "unique_values": len(frequencies),
    }


def run_prime_search(bits: int, rounds: int) -> PrimeSearchResult:
    RESULTS_DIR.mkdir(exist_ok=True)
    result = generate_probable_prime(bits, rounds)
    log = (
        "ПОИСК ВЕРОЯТНО ПРОСТОГО ЧИСЛА, ВАРИАНТ 8\n"
        f"Битовая длина: {result.bits}\n"
        f"Кандидат: {result.candidate}\n"
        f"Кандидат в двоичном виде: {result.candidate:b}\n"
        f"Всего кандидатов: {result.attempts}\n"
        f"Отсеяно малыми простыми (< 256): {result.sifted_out}\n"
        f"Отклонено тестом Ферма: {result.fermat_rejections}\n"
        f"Раундов Ферма: {len(result.fermat.tested_bases)}\n"
        f"Основания Ферма: {', '.join(map(str, result.fermat.tested_bases))}\n"
        f"Результат: вероятно простое ({result.fermat.reason})\n"
        f"Время: {result.elapsed_seconds:.6f} с\n"
        "Примечание: тест Ферма вероятностный и может принять число Кармайкла.\n"
    )
    (RESULTS_DIR / "prime_search_log.txt").write_text(log, encoding="utf-8")
    return result


def run_tests() -> None:
    """Минимальный набор воспроизводимых проверок для отчёта."""
    assert AdditiveGenerator(0, 1).sequence(10) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 4]
    assert period_length(0, 1) == 120
    assert period_length(0, 0) == 1
    assert find_max_period()[0] == 120
    assert len(SMALL_PRIMES) == 54

    test_generator = AdditiveGenerator(0, 1)
    assert fermat_test(2, 5, test_generator).is_probable_prime
    assert fermat_test(97, 5, test_generator).is_probable_prime
    assert not fermat_test(91, 5, test_generator).is_probable_prime
    assert not fermat_test(341, 1, AdditiveGenerator(0, 1)).is_probable_prime  # основание 2 - свидетель

    result = generate_probable_prime(16, 5)
    assert result.candidate.bit_length() == 16
    assert result.candidate % 2 == 1
    assert result.fermat.is_probable_prime

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "test_log.txt").write_text(
        "Все автоматические проверки пройдены.\n"
        "Проверены: формула генератора, период 120, решето, тест Ферма и p-битный кандидат.\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ЛР №1, вариант 8")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="провести статистический анализ генератора")
    analyze.add_argument("--length", type=int, default=600, help="длина последовательности (по умолчанию 600)")

    prime = subparsers.add_parser("prime", help="сгенерировать вероятно простое число")
    prime.add_argument("--bits", type=int, default=32, help="битовая длина кандидата")
    prime.add_argument("--rounds", type=int, default=10, help="число раундов Ферма")

    subparsers.add_parser("test", help="запустить автоматические проверки")
    all_command = subparsers.add_parser("all", help="запустить анализ, поиск и тесты")
    all_command.add_argument("--bits", type=int, default=32, help="битовая длина кандидата")
    all_command.add_argument("--rounds", type=int, default=10, help="число раундов Ферма")
    all_command.add_argument("--length", type=int, default=600, help="длина последовательности")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "analyze":
        result = run_analysis(args.length)
        print(f"Анализ готов: период={result['period']}, chi-square={result['chi_square']:.4f}")
    elif args.command == "prime":
        result = run_prime_search(args.bits, args.rounds)
        print(f"Найден вероятно простой {result.bits}-битный кандидат: {result.candidate}")
    elif args.command == "test":
        run_tests()
        print("Все тесты пройдены.")
    elif args.command == "all":
        analysis = run_analysis(args.length)
        prime = run_prime_search(args.bits, args.rounds)
        run_tests()
        print(f"Готово. Период={analysis['period']}; вероятно простой кандидат={prime.candidate}")


if __name__ == "__main__":
    main()
