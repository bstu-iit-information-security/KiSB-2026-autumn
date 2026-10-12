"""
ЛР №1 «Исследование алгоритмов генерации ПСП и методов тестирования чисел
на простоту», Вариант 1.

Этап 1: комбинирование методом Макларена-Марсальи (N=10, K=5).
Этап 2: генерация большого простого числа с тестом Соловея-Штрассена.

Запуск (из директории lab1/):
    python -m src.main sequence --length 20
    python -m src.main stats --length 2000
    python -m src.main period
    python -m src.main prime --bits 64 --rounds 5
"""
from __future__ import annotations
if __name__ == "__main__" and __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

from src.rng.factory import build_variant1_generator
from src.rng.seeding import build_stage2_rng
from src.stats.tests import frequency_test, uniformity_verdict
from src.primes.candidate import (
    generate_prime,
    naive_candidate_factory,
    seeded_candidate_factory,
)


def cmd_sequence(args: argparse.Namespace) -> None:
    gen = build_variant1_generator()
    seq = gen.sequence(args.length)
    print(f"Последовательность ({args.length} элементов):")
    print(seq)


def cmd_stats(args: argparse.Namespace) -> None:
    gen = build_variant1_generator()
    seq = gen.sequence(args.length)
    freqs = frequency_test(seq, alphabet_size=10)
    verdict = uniformity_verdict(seq, alphabet_size=10)

    print(f"Длина последовательности: {args.length}")
    print("Частоты цифр 0-9:")
    for digit, f in freqs.items():
        bar = "#" * int(f * 200)
        print(f"  {digit}: {f:.4f}  {bar}")
    print()
    print(
        f"Хи-квадрат = {verdict['chi2']:.3f}, df = {verdict['df']}, "
        f"критическое значение (alpha=0.05) = {verdict['critical_95']}"
    )
    ok = verdict["uniform_hypothesis_accepted"]
    print("Вывод:", "H0 не отвергается (равномерно)" if ok else "H0 отвергается (неравномерно)")


def cmd_period(args: argparse.Namespace) -> None:
    gen = build_variant1_generator()
    period, tau = gen.detect_period(max_len=args.max_len)
    print(f"Период комбинированного генератора: T = {period}, предпериод = {tau}")


def cmd_prime(args: argparse.Namespace) -> None:
    gen = build_variant1_generator()
    log: list[dict] = []

    try:
        if args.naive:
            # Буквальная схема прямо на генераторе Этапа 1 - работает только
            # для небольших p (период N=10,K=5 слишком мал для p>=16-20 бит).
            gen.reset()
            make_candidate = naive_candidate_factory(gen, args.bits)
            n = generate_prime(make_candidate, p=args.bits, ss_rounds=args.rounds, log=log)
        else:
            # Практическая схема: генератор Этапа 1 используется как источник
            # сида для качественного генератора битов (см. src/rng/seeding.py).
            rng = build_stage2_rng(gen, digits=64)
            make_candidate = seeded_candidate_factory(rng, args.bits)
            n = generate_prime(
                make_candidate, p=args.bits, ss_rounds=args.rounds, rng=rng, log=log
            )
    except RuntimeError:
        print(
            f"Не удалось найти {args.bits}-битное простое число в буквальном режиме: "
            f"период генератора Этапа 1 (N=10,K=5) слишком мал для такой разрядности. "
            f"Запустите без --naive (генератор Этапа 1 как сид) либо уменьшите --bits."
        )
        return

    entry = log[-1]
    mode = "буквальный (Этап 1 напрямую)" if args.naive else "практический (Этап 1 как сид)"
    print(f"Режим: {mode}")
    print(f"Найдено {args.bits}-битное простое число:")
    print(f"  n = {n}")
    print(
        f"  попыток всего: {entry['attempts']}, "
        f"отсеяно пробным делением: {entry['sieved_out']}"
    )
    print(f"  время: {entry['elapsed_sec'] * 1000:.2f} мс")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ЛР №1 (Вариант 1): PRNG Макларена-Марсальи + тест Соловея-Штрассена"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_seq = sub.add_parser("sequence", help="вывести последовательность генератора")
    p_seq.add_argument("--length", type=int, default=20)
    p_seq.set_defaults(func=cmd_sequence)

    p_stats = sub.add_parser("stats", help="статистическое тестирование равномерности")
    p_stats.add_argument("--length", type=int, default=2000)
    p_stats.set_defaults(func=cmd_stats)

    p_period = sub.add_parser("period", help="определить период генератора")
    p_period.add_argument("--max-len", type=int, default=20000, dest="max_len")
    p_period.set_defaults(func=cmd_period)

    p_prime = sub.add_parser("prime", help="сгенерировать простое число (Этап 2)")
    p_prime.add_argument("--bits", type=int, default=64)
    p_prime.add_argument("--rounds", type=int, default=5)
    p_prime.add_argument(
        "--naive",
        action="store_true",
        help="буквальная схема прямо на генераторе Этапа 1 (только для малых --bits)",
    )
    p_prime.set_defaults(func=cmd_prime)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
