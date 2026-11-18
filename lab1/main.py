"""Лабораторная работа №1 (вариант 10): консольное приложение.

Часть 1: комбинирование LFSR псевдослучайным прореживанием (SG-генератор).
Часть 2: генерация доказуемо простых чисел методом Михалеску (e = 1/2).

Примеры:
  python main.py part1 --g1 1 --g2 7 --length 40 --alphabet 10
  python main.py part2 --bits 256 --count 3
  python main.py selftest
  python main.py report          # все эксперименты, графики, таблицы -> results/
"""
import argparse
import sys
import time

from lfsr import poly, poly_str, degree, is_primitive
from shrinking import ShrinkingGenerator, theoretical_period
from stats import chi_square_uniform, smallest_period, bits_to_symbols
from mihailescu import Mihailescu, Journal, verify_certificate

# многочлены G1 из задания (вариант 10) и кандидаты для селектора G2
G1_POLYS = {1: poly(5, 2, 0), 2: poly(5, 4, 3, 2, 0), 3: poly(5, 0)}
G2_POLYS = {4: poly(4, 1, 0), 5: poly(5, 2, 0), 6: poly(6, 1, 0), 7: poly(7, 3, 0)}
# большие регистры для источника случайности этапа 2 (проверены is_primitive)
BIG_A, BIG_S = poly(31, 3, 0), poly(32, 22, 2, 1, 0)


def make_big_rng(seed=None):
    import random
    rnd = random.Random(seed if seed is not None else time.time_ns())
    return ShrinkingGenerator(BIG_A, rnd.getrandbits(31) | 1, BIG_S, rnd.getrandbits(32) | 1)


def cmd_part1(args):
    fa, fs = G1_POLYS[args.g1], G2_POLYS[args.g2]
    print(f"G1: {poly_str(fa)}   примитивен: {is_primitive(fa)}")
    print(f"G2: {poly_str(fs)}   примитивен: {is_primitive(fs)}")
    g = ShrinkingGenerator(fa, args.seed_a, fs, args.seed_s)
    print("Последовательность:", *g.symbols(args.length, args.alphabet))
    g = ShrinkingGenerator(fa, args.seed_a, fs, args.seed_s)
    per, ok = smallest_period(g.bits(40000))
    print(f"Измеренный период (бит): {per}  (надёжно: {ok});"
          f" теоретический (2^n-1)*2^(m-1): {theoretical_period(degree(fa), degree(fs))}")
    g = ShrinkingGenerator(fa, args.seed_a, fs, args.seed_s)
    k = (args.alphabet - 1).bit_length()
    cnt = max(per // k, 10)
    r = chi_square_uniform(g.symbols(cnt, args.alphabet), args.alphabet)
    print(f"хи-квадрат по {cnt} символам (<= 1 периода): chi2={r['chi2']:.2f}, "
          f"df={r['df']}, крит.(5%)={r['crit']:.2f}, p={r['p']:.3f} -> "
          f"{'равномерна' if r['ok'] else 'НЕ равномерна'}")


def cmd_part2(args):
    rng = make_big_rng(args.seed)
    gen = Mihailescu(rng, B=args.B, s=args.s, A=args.A)
    for k in range(args.count):
        j = Journal()
        t0 = time.perf_counter()
        n, cert = gen.generate(args.bits, j)
        dt = time.perf_counter() - t0
        print(f"\n=== простое число #{k + 1}: {n.bit_length()} бит, {dt:.3f} с ===")
        print(f"n = {n}" if n.bit_length() <= 512 else f"n (hex) = {n:x}")
        print(f"сертификат Поклингтона проверен: {verify_certificate(cert)}")
        print(f"{'уровень m':>10}{'F, бит':>8}{'попыток t':>11}{'кандидатов':>12}"
              f"{'отсеяно дел.':>14}{'отсеяно РМ':>12}{'время, с':>10}")
        for r in reversed(j.levels):
            print(f"{r.m:>10}{r.F_bits:>8}{r.t_attempts:>11}{r.candidates:>12}"
                  f"{r.rej_trial:>14}{r.rej_rm:>12}{r.seconds:>10.4f}")


def cmd_selftest(_):
    import unittest
    import test_lab1
    res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(test_lab1))
    sys.exit(0 if res.wasSuccessful() else 1)


def cmd_report(_):
    import experiments
    experiments.run_all()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("part1", help="SG-генератор")
    a.add_argument("--g1", type=int, choices=G1_POLYS, default=1, help="многочлен G1 (1..3 из задания)")
    a.add_argument("--g2", type=int, choices=G2_POLYS, default=7, help="степень многочлена G2")
    a.add_argument("--length", type=int, default=50)
    a.add_argument("--alphabet", type=int, default=2)
    a.add_argument("--seed-a", type=int, default=0b10110)
    a.add_argument("--seed-s", type=int, default=0b1011)
    a.set_defaults(fn=cmd_part1)
    b = sub.add_parser("part2", help="простые числа методом Михалеску")
    b.add_argument("--bits", type=int, default=256)
    b.add_argument("--count", type=int, default=1)
    b.add_argument("--B", type=int, default=32)
    b.add_argument("--s", type=int, default=4)
    b.add_argument("--A", type=int, default=2000)
    b.add_argument("--seed", type=int, default=None)
    b.set_defaults(fn=cmd_part2)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
