"""Эксперименты для отчёта: таблицы (CSV/JSON) и графики (PNG) в каталоге results/."""
import csv
import json
import math
import os
import random
import statistics
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lfsr import poly_str, degree, is_primitive
from shrinking import ShrinkingGenerator, theoretical_period
from stats import chi_square_uniform, bits_to_symbols, smallest_period
from mihailescu import Mihailescu, Journal, verify_certificate, rabin_miller
from main import G1_POLYS, G2_POLYS, BIG_A, BIG_S, make_big_rng

OUT = "results"
SEED_A, SEED_S = 0b10110, 0b1011


class PyRng:
    """Адаптер: независимый источник (random.Random) для перекрёстной проверки."""
    def __init__(self, seed):
        self.r = random.Random(seed)

    def randbelow(self, n):
        return self.r.randrange(n) if n > 1 else 0


def short(p):
    return poly_str(p).replace(" + ", "+")


def exp1_configs():
    rows = []
    for i, fa in G1_POLYS.items():
        for d, fs in G2_POLYS.items():
            g = ShrinkingGenerator(fa, SEED_A, fs, SEED_S)
            per, ok = smallest_period(g.bits(40000))
            theo = theoretical_period(degree(fa), degree(fs))
            coprime = is_primitive(fa) and is_primitive(fs) and \
                math.gcd((1 << degree(fa)) - 1, (1 << degree(fs)) - 1) == 1
            g = ShrinkingGenerator(fa, SEED_A, fs, SEED_S)
            bits = g.bits(per)  # ровно один период
            ones = sum(bits) / per
            rb = chi_square_uniform(bits, 2)
            nib = bits_to_symbols(bits, 4)
            rn = chi_square_uniform(nib, 16) if len(nib) / 16 >= 5 else None
            rows.append({
                "G1": short(fa), "G1 примитивен": is_primitive(fa),
                "G2": short(fs), "G2 примитивен": is_primitive(fs),
                "НОД периодов=1": coprime,
                "T теор.": theo if coprime else "-", "T изм.": per,
                "доля единиц": round(ones, 4),
                "chi2 бит": round(rb["chi2"], 3), "p бит": round(rb["p"], 4),
                "chi2 тетрад": round(rn["chi2"], 2) if rn else "-",
                "p тетрад": round(rn["p"], 4) if rn else "-"
            })
    return rows


def exp5_big():
    g = make_big_rng(12345)
    L = 1_000_000
    bits = g.bits(L)
    nib, byt = bits_to_symbols(bits, 4), bits_to_symbols(bits, 8)
    return {
        "G1": poly_str(BIG_A) + f"  (примитивен: {is_primitive(BIG_A)})",
        "G2": poly_str(BIG_S) + f"  (примитивен: {is_primitive(BIG_S)})",
        "T теор.": theoretical_period(31, 32), "бит": L,
        "доля единиц": round(sum(bits) / L, 5),
        "chi2 бит": chi_square_uniform(bits, 2), "chi2 тетрад": chi_square_uniform(nib, 16),
        "chi2 байт": chi_square_uniform(byt, 256),
    }


def exp6_primes():
    rows, runs_detail = [], {}
    for m in (32, 64, 128, 256, 512, 1024):
        reps = 20 if m <= 512 else 10
        recs, times, cands, trial, rm, pock, valid = [], [], 0, 0, 0, 0, True
        sample = None
        for r in range(reps):
            gen = Mihailescu(make_big_rng(1000 * m + r))
            j = Journal()
            t0 = time.perf_counter()
            n, cert = gen.generate(m, j)
            times.append(time.perf_counter() - t0)
            tot = j.totals()
            cands += tot["candidates"]; trial += tot["rej_trial"]
            rm += tot["rej_rm"]; pock += tot["rej_pock"]
            ok = (n.bit_length() == m and verify_certificate(cert)
                  and rabin_miller(n, PyRng(r), 40))
            valid &= ok
            if r == 0:
                sample = (n, j, cert)
        rows.append({"m, бит": m, "запусков": reps, "t средн., с": round(statistics.mean(times), 4),
                     "t макс., с": round(max(times), 4),
                     "кандидатов (сумма)": cands, "отсеяно делением": trial,
                     "% делением": round(100 * trial / cands, 1),
                     "отсеяно Р–М": rm, "отсеяно Поклингтоном": pock,
                     "все проверены": valid})
        runs_detail[m] = sample
    return rows, runs_detail


def write_csv(name, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)


def charts(e1, fa, fs, e6):
    # 1. периоды
    fig, ax = plt.subplots(figsize=(9, 4.5))
    labels = [f"G1:{r['G1']}\nG2:{r['G2']}".replace("x^", "x") for r in e1]
    labels = [f"{i // 4 + 1}/{r['G2'].split('+')[0]}" for i, r in enumerate(e1)]
    x = range(len(e1))
    ax.bar([i - 0.2 for i in x], [r["T изм."] for r in e1], 0.4, label="измеренный период")
    ax.bar([i + 0.2 for i in x], [r["T теор."] if r["T теор."] != "-" else 0 for r in e1], 0.4,
           label="теоретический (2ⁿ−1)·2ᵐ⁻¹", alpha=0.6)
    ax.set_yscale("log"); ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=8, rotation=30)
    ax.set_xlabel("номер G1 / старший член G2"); ax.set_ylabel("период, бит")
    ax.set_title("Период SG-генератора для всех сочетаний многочленов"); ax.legend(); ax.grid(alpha=.3, axis="y")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig1_periods.png", dpi=150); plt.close(fig)

    # 2. гистограммы тетрад
    per = theoretical_period(degree(fa), degree(fs))
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, (f1, title) in zip(axs, [(fa, "G1 = x⁵+x²+1 (примитивен)"), (G1_POLYS[3], "G1 = x⁵+1 (НЕ примитивен)")]):
        nib = bits_to_symbols(ShrinkingGenerator(f1, SEED_A, fs, SEED_S).bits(per), 4)
        r = chi_square_uniform(nib, 16)
        ax.bar(range(16), r["counts"]); ax.axhline(r["expected"], color="r", ls="--", label="ожидание")
        ax.set_title(f"{title}\nχ²={r['chi2']:.1f}, p={r['p']:.3g}", fontsize=10)
        ax.set_xlabel("значение тетрады"); ax.legend()
    axs[0].set_ylabel("частота")
    fig.suptitle("Частоты 4-битных символов за один период (G2 = x⁷+x³+1)")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig2_hist.png", dpi=150); plt.close(fig)

    # 3. простые числа
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    ms = [r["m, бит"] for r in e6]
    axs[0].plot(ms, [r["t средн., с"] for r in e6], "o-")
    axs[0].set_xscale("log", base=2); axs[0].set_yscale("log")
    axs[0].set_xlabel("длина m, бит"); axs[0].set_ylabel("среднее время, с"); axs[0].grid(alpha=.3)
    axs[0].set_title("Время генерации доказуемо простого")
    w = 0.25
    xs = range(len(ms))
    axs[1].bar([i - w for i in xs], [r["отсеяно делением"] for r in e6], w, label="пробные деления")
    axs[1].bar(list(xs), [r["отсеяно Р–М"] for r in e6], w, label="Рабин–Миллер")
    axs[1].bar([i + w for i in xs], [r["отсеяно Поклингтоном"] for r in e6], w, label="Поклингтон")
    axs[1].set_xticks(list(xs)); axs[1].set_xticklabels(ms); axs[1].set_yscale("symlog")
    axs[1].set_xlabel("длина m, бит"); axs[1].set_ylabel("отсеяно кандидатов (сумма по запускам)")
    axs[1].set_title("Где отсеиваются кандидаты"); axs[1].legend(); axs[1].grid(alpha=.3, axis="y")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig3_primes.png", dpi=150); plt.close(fig)


def run_all():
    os.makedirs(OUT, exist_ok=True)
    fa, fs = G1_POLYS[1], G2_POLYS[7]
    e1 = exp1_configs(); write_csv("exp1_periods.csv", e1)
    e5 = exp5_big()
    e6, details = exp6_primes(); write_csv("exp6_primes.csv", e6)
    charts(e1, fa, fs, e6)
    log = {}
    for m in (256,):
        n, j, cert = details[m]
        log[m] = {"n": str(n),
                  "levels": [r.__dict__ for r in reversed(j.levels)],
                  "cert": [{k: (str(v) if v is not None else None) for k, v in c.items()} for c in cert]}
    with open(f"{OUT}/all.json", "w", encoding="utf-8") as f:
        json.dump({"e1": e1, "e5": e5, "e6": e6, "log": log}, f, ensure_ascii=False, indent=1, default=str)
    print("готово: результаты в каталоге", OUT)


if __name__ == "__main__":
    run_all()
