"""Лабораторная работа №1, вариант 4: LFSR (часть 1) + тест Рабина-Миллера (часть 2).

Консольное приложение:
    python main.py poly                      - какие из многочленов примитивны
    python main.py lfsr --poly 7,1,0 --seed 1 --count 40
    python main.py stats                     - статистические исследования (Этап 1)
    python main.py prime --bits 256 --count 3
    python main.py bench                     - таблицы и графики Этапа 2
    python main.py all                       - всё сразу, результаты в results/
"""

from __future__ import annotations
import argparse
import csv
import os
import statistics

from lfsr import (LFSR, poly_from_exponents, poly_str, is_irreducible, is_primitive,
                  factor_gf2, deg)
from stats import full_report, block_frequency, monobit
from primes import generate_prime, DEFAULT_POLY, is_probable_prime

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# Три многочлена варианта 4
POLYS = {
    "f1": poly_from_exponents(7, 1, 0),
    "f2": poly_from_exponents(7, 5, 3, 0),
    "f3": poly_from_exponents(7, 6, 5, 2, 0),
}


def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        print("matplotlib не установлен - графики пропущены (pip install matplotlib)")
        return None


def _save_csv(name: str, header: list, rows: list):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)


# ------------------------------------------------------------------ Этап 1
def cmd_poly(_args=None):
    print("Какие многочлены примитивны по модулю 2:\n")
    rows = []
    for name, p in POLYS.items():
        irr, prim = is_irreducible(p), is_primitive(p)
        fac = " * ".join(f"({poly_str(q)})" for q in factor_gf2(p))
        print(f"{name}(x) = {poly_str(p)}")
        print(f"   неприводим: {irr}; примитивен: {prim}; разложение: {fac}")
        rows.append([name, poly_str(p), irr, prim, fac])
    _save_csv("stage1_polys.csv", ["name", "poly", "irreducible", "primitive", "factorization"], rows)


def period_distribution(p: int) -> dict[int, int]:
    """Сколько ненулевых начальных состояний даёт каждый период (все состояния обходим по циклам)."""
    n = deg(p)
    seen = bytearray(1 << n)
    res: dict[int, int] = {}
    for s in range(1, 1 << n):
        if seen[s]:
            continue
        g = LFSR(p, s)
        length = 0
        while True:
            seen[g.state] = 1
            g.next_bit()
            length += 1
            if g.state == s:
                break
        res[length] = res.get(length, 0) + length
    return res


def cmd_lfsr(args):
    p = poly_from_exponents(*[int(x) for x in args.poly.split(",")])
    g = LFSR(p, args.seed)
    print(f"f(x) = {poly_str(p)}, seed = {args.seed:0{g.n}b}, период = {g.period()}")
    print("".join(map(str, g.bits(args.count))))


def cmd_stats(_args=None):
    plt = _plt()
    # 1. периоды
    print("\n=== Периоды (по всем ненулевым начальным состояниям) ===")
    rows = []
    for name, p in POLYS.items():
        dist = period_distribution(p)
        txt = ", ".join(f"T={t}: {c} сост." for t, c in sorted(dist.items(), reverse=True))
        print(f"{name} ({poly_str(p)}): {txt}")
        rows.append([name, poly_str(p), txt])
    _save_csv("stage1_periods.csv", ["name", "poly", "periods"], rows)

    # 2. статистика по многочленам / начальным состояниям
    print("\n=== Статистические тесты, длина = 12700 бит (100 периодов m-последовательности) ===")
    L = 12700
    cases = [("f1", 1), ("f1", 0b1010101), ("f2", 1), ("f2", 0b1010101), ("f2", 0b1111111), ("f3", 1),
             ("f3", 0b1010101)]
    hdr = ["poly", "seed", "T", "ones", "monobit_chi2", "monobit_p", "blocks4_chi2", "blocks4_p",
           "runs_z", "runs_p", "autocorr_1", "autocorr_7"]
    rows = []
    for name, seed in cases:
        p = POLYS[name]
        g = LFSR(p, seed)
        T = g.period()
        bits = g.bits(L)
        r = full_report(bits, 4)
        rows.append([name, f"{seed:07b}", T, r["monobit"]["ones"], round(r["monobit"]["chi2"], 3),
                     round(r["monobit"]["p"], 4), round(r["blocks"]["chi2"], 2), round(r["blocks"]["p"], 4),
                     round(r["runs"]["z"], 2), round(r["runs"]["p"], 4),
                     round(r["autocorr_1"], 4), round(r["autocorr_7"], 4)])
    for row in rows:
        print(row)
    _save_csv("stage1_stats.csv", hdr, rows)

    # 3. зависимость от длины
    print("\n=== Зависимость хи-квадрат (блоки по 4 бита) от длины выборки ===")
    lengths = [127, 254, 508, 1016, 2032, 4064, 8128, 16256, 32512]
    series = {}
    rows = []
    for name in POLYS:
        g = LFSR(POLYS[name], 1)
        allbits = g.bits(max(lengths))
        series[name] = []
        for Lc in lengths:
            b = block_frequency(allbits[:Lc], 4)
            series[name].append(b["p"])
            rows.append([name, Lc, round(b["chi2"], 2), round(b["p"], 4)])
    _save_csv("stage1_length.csv", ["poly", "L", "chi2", "p"], rows)
    for r in rows:
        print(r)

    if plt:
        os.makedirs(OUT, exist_ok=True)
        # гистограммы 7-битных слов (окно со сдвигом 1) за один период
        fig, axes = plt.subplots(1, 3, figsize=(14, 3.6), sharey=True)
        for ax, (name, p) in zip(axes, POLYS.items()):
            g = LFSR(p, 1)
            T = g.period()
            seq = g.bits(T + 6)
            cnt = [0] * 128
            for i in range(T):
                v = 0
                for b in seq[i:i + 7]:
                    v = (v << 1) | b
                cnt[v] += 1
            ax.bar(range(128), cnt, width=1.0)
            ax.set_title(f"{name}: {poly_str(p)}\nT={T}, разных слов: {sum(c > 0 for c in cnt)}", fontsize=9)
            ax.set_xlabel("7-битное слово")
        axes[0].set_ylabel("частота за период")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "stage1_words.png"), dpi=130)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 4))
        for name in POLYS:
            ax.plot(lengths, series[name], marker="o", label=f"{name}: {poly_str(POLYS[name])}")
        ax.axhline(0.05, color="gray", ls="--", label="уровень значимости 0.05")
        ax.set_xscale("log")
        ax.set_xlabel("длина последовательности, бит")
        ax.set_ylabel("p-value (хи-квадрат, блоки по 4 бита)")
        ax.legend(fontsize=8)
        ax.grid(alpha=.3)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "stage1_length.png"), dpi=130)
        plt.close(fig)


# ------------------------------------------------------------------ Этап 2
def cmd_prime(args):
    rng = LFSR(DEFAULT_POLY, args.seed)
    for _ in range(args.count):
        st = generate_prime(args.bits, rng, args.rounds, args.sieve)
        print(f"{st.bits} бит, кандидатов {st.candidates} (отсеяно делением {st.rejected_sieve}, "
              f"Рабином-Миллером {st.rejected_mr}), {st.seconds * 1000:.1f} мс")
        print(st.prime)


def cmd_bench(args=None):
    plt = _plt()
    sizes = [64, 128, 256, 512, 1024]
    limits = [0, 256, 2000]
    per = 30
    rng = LFSR(DEFAULT_POLY, 0x1ACE5)
    rows, agg = [], {}
    print("\n=== Генерация простых чисел (в среднем по %d числам) ===" % per)
    print("бит | просеивание | кандидатов | отсеяно дел. | отсеяно Р-М | время, мс")
    for bits in sizes:
        for lim in limits:
            sts = [generate_prime(bits, rng, 5, lim) for _ in range(per)]
            m = lambda f: statistics.mean(f(s) for s in sts)
            row = [bits, lim, round(m(lambda s: s.candidates), 1), round(m(lambda s: s.rejected_sieve), 1),
                   round(m(lambda s: s.rejected_mr), 1), round(m(lambda s: s.seconds) * 1000, 2)]
            rows.append(row)
            agg[(bits, lim)] = row
            print(" | ".join(str(x) for x in row))
    _save_csv("stage2_bench.csv", ["bits", "sieve_limit", "avg_candidates", "avg_rejected_sieve",
                                   "avg_rejected_MR", "avg_ms"], rows)

    # доля кандидатов, пережившая просеивание (теория 1.12/ln z для нечётных)
    import math
    print("\nДоля нечётных кандидатов, прошедших просеивание: практика / теория 1.12/ln z")
    rows2 = []
    for lim in (256, 2000):
        c = sum(agg[(b, lim)][2] for b in sizes)
        r = sum(agg[(b, lim)][3] for b in sizes)
        rows2.append([lim, round(1 - r / c, 3), round(1.12 / math.log(lim), 3)])
        print(rows2[-1])
    _save_csv("stage2_sieve_share.csv", ["limit", "practice", "theory"], rows2)

    if plt:
        os.makedirs(OUT, exist_ok=True)
        fig, ax = plt.subplots(figsize=(7, 4))
        for lim in limits:
            ax.plot(sizes, [agg[(b, lim)][5] for b in sizes], marker="o",
                    label="без просеивания" if lim == 0 else f"делители < {lim}")
        ax.set_yscale("log")
        ax.set_xlabel("длина числа, бит")
        ax.set_ylabel("среднее время генерации, мс")
        ax.grid(alpha=.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "stage2_time.png"), dpi=130)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 4))
        w = 0.27
        for i, lim in enumerate(limits):
            xs = [j + (i - 1) * w for j in range(len(sizes))]
            ax.bar(xs, [agg[(b, lim)][3] for b in sizes], w,
                   label="без просеивания" if lim == 0 else f"делители < {lim}")
        ax.set_xticks(range(len(sizes)))
        ax.set_xticklabels(sizes)
        ax.set_xlabel("длина числа, бит")
        ax.set_ylabel("в среднем отсеяно пробными делениями")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "stage2_sieved.png"), dpi=130)
        plt.close(fig)

    # корректность: 5 раундов vs известные случаи
    print("\n=== Проверка корректности теста Рабина-Миллера ===")
    cases = [(561, False, "Кармайкл"), (1105, False, "Кармайкл"), (2047, False, "сильно псевдопростое по осн. 2"),
             (2 ** 61 - 1, True, "Мерсенн"), (2 ** 67 - 1, False, "Мерсенн (составное)"),
             (2 ** 89 - 1, True, "Мерсенн"), (2 ** 127 - 1, True, "Мерсенн")]
    for n, expect, note in cases:
        got = is_probable_prime(n, 5, LFSR(DEFAULT_POLY, 12345))
        print(f"{'OK ' if got == expect else 'ERR'} n={n if n < 10**12 else f'{n.bit_length()}-битное'} -> {got} ({note})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("poly")
    p = sub.add_parser("lfsr")
    p.add_argument("--poly", default="7,1,0", help="показатели степеней через запятую, напр. 7,1,0")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--count", type=int, default=40)
    sub.add_parser("stats")
    p = sub.add_parser("prime")
    p.add_argument("--bits", type=int, default=256)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--sieve", type=int, default=256, help="верхняя граница пробных делений (0 - выкл.)")
    p.add_argument("--seed", type=int, default=0x1ACE5)
    sub.add_parser("bench")
    sub.add_parser("all")
    a = ap.parse_args()
    {"poly": cmd_poly, "lfsr": cmd_lfsr, "stats": cmd_stats, "prime": cmd_prime, "bench": cmd_bench}.get(
        a.cmd, lambda x: (cmd_poly(), cmd_stats(), cmd_bench()))(a)


if __name__ == "__main__":
    main()
