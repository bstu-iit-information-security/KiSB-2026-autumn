"""
ЛР №2, вариант 2 — избыточное кодирование.
"""

import argparse
import random

from src.hamming import (encode as h_encode, decode as h_decode,
                         inject_errors as h_inject, hamming_params,
                         self_test as h_self_test)
from src.iterative import (encode as it_encode, decode as it_decode,
                           inject_errors as it_inject,
                           inject_rect_errors as it_inject_rect,
                           self_test as it_self_test)


def text_to_bits(text: str) -> list[int]:
    bits = []
    for ch in text:
        b = ord(ch)
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits


def bits_to_text(bits: list[int]) -> str:
    chars = []
    for i in range(0, len(bits) - 7, 8):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[i + j]
        chars.append(chr(b))
    return "".join(chars)


def run_hamming(dmin: int, text: str, errors: int, block: int, seed: int):
    print("=" * 60)
    print(f"Код Хемминга, d_min = {dmin}")
    print("=" * 60)
    bits = text_to_bits(text)
    while len(bits) % block:
        bits.append(0)
    rng = random.Random(seed)
    print(f"Текст: {text!r}")
    print(f"Биты: {''.join(map(str, bits))} ({len(bits)} бит)")

    total_detected = total_fixed = total_blocks = 0
    n_full, r_full = hamming_params(block, dmin)
    print(f"Блок k={block}, n={n_full}, r={r_full}\n")

    for b in range(0, len(bits), block):
        data = bits[b:b + block]
        cw, H, n, r = h_encode(data, dmin)
        recv, real_err = h_inject(cw, errors, rng)
        corr, s, est_err = h_decode(recv, H, dmin)

        total_blocks += 1
        if errors == 0 or any(s):
            total_detected += 1
        if corr == cw:
            total_fixed += 1

        if b == 0:
            print(f"Пример блока 0:")
            print(f"  X_k      = {''.join(map(str, data))}")
            print(f"  X_n      = {''.join(map(str, cw))}")
            print(f"  Y_n      = {''.join(map(str, recv))}")
            print(f"  S        = {''.join(map(str, s))}")
            print(f"  E_n      = {''.join(map(str, est_err))}")
            print(f"  Y_n'     = {''.join(map(str, corr))}")
            print(f"  Исправлено: {corr == cw}")
            print()

    print(f"Блоков: {total_blocks}")
    print(f"Обнаружено: {total_detected}/{total_blocks} "
          f"({total_detected / total_blocks:.2%})")
    print(f"Исправлено: {total_fixed}/{total_blocks} "
          f"({total_fixed / total_blocks:.2%})")


def run_iterative(text: str, errors: int, seed: int, use_rect: bool = False):
    print("=" * 60)
    print("Итеративный код, вариант 2: k=20, 4×5, 2 группы паритетов")
    print("=" * 60)
    bits = text_to_bits(text)
    block = 20
    while len(bits) % block:
        bits.append(0)
    rng = random.Random(seed)

    total_detected = total_fixed = total_blocks = 0
    for b in range(0, len(bits), block):
        data = bits[b:b + block]
        cw, mat = it_encode(data)
        if use_rect:
            recv, _ = it_inject_rect(cw)
        else:
            recv, _ = it_inject(cw, errors, rng)
        corr, est_err, status = it_decode(recv)
        total_blocks += 1
        if errors == 0 or status in ("fixed", "detected"):
            total_detected += 1
        if status in ("fixed", "ok") and corr == cw:
            total_fixed += 1

        if b == 0:
            print(f"Пример блока 0:")
            print(f"  X_k   = {''.join(map(str, data))}")
            print(f"  X_n   = {''.join(map(str, cw))} (n={len(cw)})")
            print(f"  Y_n   = {''.join(map(str, recv))}")
            print(f"  Статус: {status}")
            print()

    print(f"Блоков: {total_blocks}")
    print(f"Обнаружено: {total_detected}/{total_blocks} "
          f"({total_detected / total_blocks:.2%})")
    print(f"Исправлено: {total_fixed}/{total_blocks} "
          f"({total_fixed / total_blocks:.2%})")


def run_self_test_hamming(k: int, dmin: int, trials: int):
    print(f"\nСтатистика кода Хемминга (k={k}, d_min={dmin}, trials={trials}):")
    print(f"{'кратность':>10} {'обнаружено':>12} {'исправлено':>12}")
    res = h_self_test(k, dmin, trials)
    for i, r in res.items():
        print(f"{i:>10} {r['detect_ratio']:>12.2%} {r['fix_ratio']:>12.2%}")


def run_self_test_iterative(trials: int):
    print(f"\nСтатистика итеративного кода (4×5, trials={trials}):")
    print(f"{'кратность':>10} {'обнаружено':>12} {'исправлено':>12}")
    res = it_self_test(4, 5, trials)
    for i, r in res.items():
        print(f"{i:>10} {r['detect_ratio']:>12.2%} {r['fix_ratio']:>12.2%}")


def main():
    ap = argparse.ArgumentParser(description="ЛР №2, вариант 2")
    ap.add_argument("--mode", choices=["hamming", "iterative"], required=True)
    ap.add_argument("--text", default="Hello")
    ap.add_argument("--errors", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dmin", type=int, choices=[3, 4], default=4)
    ap.add_argument("--block", type=int, default=4)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--trials", type=int, default=1000)
    ap.add_argument("--rect", action="store_true",
                    help="для iterative: явно внести 4 ошибки в вершины прямоугольника")
    args = ap.parse_args()

    if args.mode == "hamming":
        run_hamming(args.dmin, args.text, args.errors, args.block, args.seed)
        if args.self_test:
            run_self_test_hamming(args.block, args.dmin, args.trials)
    else:
        run_iterative(args.text, args.errors, args.seed, args.rect)
        if args.self_test:
            run_self_test_iterative(args.trials)


if __name__ == "__main__":
    main()