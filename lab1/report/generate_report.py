"""
Скрипт формирует данные и графики для отчёта по ЛР №1 (Вариант 1):

  1. Частотный тест и хи-квадрат для комбинированного генератора Этапа 1,
     включая демонстрацию эффекта "длина >> период" (см. п.2 ниже).
  2. Сравнение периода при выполненном и нарушенном условии максимального
     периода (§4.1, свойство 4) - иллюстрация п.4 задания Этапа 1.
  3. Лог работы генератора простых чисел Этапа 2 (практическая схема:
     генератор Этапа 1 как сид) - время и число отсеянных кандидатов.
  4. Сравнение "буквальной" (только Этап 1) и "практической" (Этап 1 как
     сид) схем генерации кандидатов - показывает, зачем нужен посев.

Запуск (из директории lab1/):  python3 report/generate_report.py
Результат: report/report_data.json, report/figures/*.png
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.rng.lcg import LCG
from src.rng.mm_combine import MaclarenMarsaglia
from src.rng.factory import build_variant1_generator
from src.rng.seeding import build_stage2_rng
from src.stats.tests import frequency_test, uniformity_verdict
from src.primes.candidate import (
    generate_prime,
    naive_candidate_factory,
    seeded_candidate_factory,
)

FIG_DIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Частотный тест и эффект "длина >> период"
# ---------------------------------------------------------------------------
def section_frequency() -> dict:
    results = {}
    # 137 не кратно периоду T=10 -> неполный последний цикл, есть за счёт
    # чего увидеть отклонение от идеальной равномерности.
    for length, label in [(50, "50 (=5 полных периодов)"), (137, "137 (5.7 периода)")]:
        gen = build_variant1_generator()
        seq = gen.sequence(length)
        freqs = frequency_test(seq, alphabet_size=10)
        verdict = uniformity_verdict(seq, alphabet_size=10)
        results[label] = {"freqs": freqs, **verdict}

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, (label, data) in zip(axes, results.items()):
        ax.bar(list(data["freqs"].keys()), list(data["freqs"].values()))
        ax.axhline(0.1, linestyle="--", color="gray")
        ax.set_title(f"n={label}\nchi2={data['chi2']:.3f}")
        ax.set_xlabel("Цифра")
        ax.set_ylabel("Частота")
    fig.suptitle("Частоты выхода MM-генератора: эффект длины относительно периода T=10")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "frequency.png"), dpi=150)
    plt.close(fig)
    return results


# ---------------------------------------------------------------------------
# 2. Период при выполненном / нарушенном условии максимального периода
# ---------------------------------------------------------------------------
def section_period_comparison() -> dict:
    cases = {
        "a=1, c=3 (условие выполнено)": LCG(a=1, c=3, N=10, x0=0),
        "a=3, c=1 (b=2 не кратно 5)": LCG(a=3, c=1, N=10, x0=0),
        "a=1, c=2 (НОД(c,N)=2 != 1)": LCG(a=1, c=2, N=10, x0=0),
        "a=7, c=3 (b=6 не кратно 5)": LCG(a=7, c=3, N=10, x0=0),
    }
    results = {}
    for label, g1 in cases.items():
        period, tau = g1.full_period()
        results[label] = {
            "period": period,
            "pre_period": tau,
            "condition_met": g1.satisfies_max_period_condition(),
        }

    fig, ax = plt.subplots(figsize=(7, 4))
    labels = list(results.keys())
    periods = [results[l]["period"] or 0 for l in labels]
    colors = ["tab:green" if results[l]["condition_met"] else "tab:red" for l in labels]
    ax.bar(labels, periods, color=colors)
    ax.axhline(10, linestyle="--", color="gray", label="T_max = N = 10")
    ax.set_ylabel("Период T")
    ax.set_title("Период G1 (N=10) при выполнении/нарушении условия §4.1 (св-во 4)")
    ax.legend()
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "period_comparison.png"), dpi=150)
    plt.close(fig)
    return results


# ---------------------------------------------------------------------------
# 3. Лог генератора простых чисел (практическая схема Этапа 2)
# ---------------------------------------------------------------------------
def section_prime_log(bit_sizes=(32, 64, 96, 128), runs_per_size=8) -> dict:
    log: list[dict] = []
    summary = {}
    for bits in bit_sizes:
        gen = build_variant1_generator()
        rng = build_stage2_rng(gen, digits=64 + bits)  # разный сид под каждый размер
        for _ in range(runs_per_size):
            make_candidate = seeded_candidate_factory(rng, bits)
            generate_prime(make_candidate, p=bits, ss_rounds=5, rng=rng, log=log)
        entries = [e for e in log if e["bits"] == bits]
        summary[bits] = {
            "avg_attempts": sum(e["attempts"] for e in entries) / len(entries),
            "avg_sieved_out": sum(e["sieved_out"] for e in entries) / len(entries),
            "avg_time_ms": sum(e["elapsed_sec"] for e in entries) / len(entries) * 1000,
        }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    bits_list = list(summary.keys())
    ax1.plot(bits_list, [summary[b]["avg_time_ms"] for b in bits_list], marker="o")
    ax1.set_xlabel("Разрядность p, бит")
    ax1.set_ylabel("Среднее время, мс")
    ax1.set_title("Время генерации простого числа")

    ax2.bar([str(b) for b in bits_list], [summary[b]["avg_attempts"] for b in bits_list])
    ax2.set_xlabel("Разрядность p, бит")
    ax2.set_ylabel("Попыток в среднем")
    ax2.set_title("Число кандидатов до успеха")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "prime_generation.png"), dpi=150)
    plt.close(fig)
    return {"summary": summary, "log": log}


# ---------------------------------------------------------------------------
# 4. "Буквальная" (Этап 1 напрямую) vs "практическая" (Этап 1 как сид) схема
# ---------------------------------------------------------------------------
def section_naive_vs_practical(bit_sizes=(8, 12, 16, 20)) -> dict:
    results = {}
    for bits in bit_sizes:
        row = {}
        # буквальная схема
        gen = build_variant1_generator()
        gen.reset()
        make_naive = naive_candidate_factory(gen, bits)
        try:
            generate_prime(make_naive, p=bits, ss_rounds=5, max_attempts=5000)
            row["naive_succeeded"] = True
        except RuntimeError:
            row["naive_succeeded"] = False

        # практическая схема (для сравнения - должна работать всегда)
        gen2 = build_variant1_generator()
        rng = build_stage2_rng(gen2, digits=64)
        make_seeded = seeded_candidate_factory(rng, bits)
        try:
            generate_prime(make_seeded, p=bits, ss_rounds=5, rng=rng, max_attempts=5000)
            row["seeded_succeeded"] = True
        except RuntimeError:
            row["seeded_succeeded"] = False

        results[bits] = row
    return results


def main() -> None:
    report = {
        "frequency_test": section_frequency(),
        "period_comparison": section_period_comparison(),
        "prime_generation": section_prime_log(),
        "naive_vs_practical": section_naive_vs_practical(),
    }
    out_path = os.path.join(os.path.dirname(__file__), "report_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    print("Готово. Сохранено:")
    print(f"  {out_path}")
    for fname in sorted(os.listdir(FIG_DIR)):
        print(f"  {os.path.join(FIG_DIR, fname)}")

    print("\nБуквальная vs практическая схема (успех генерации простого числа):")
    for bits, row in report["naive_vs_practical"].items():
        print(f"  p={bits:>3} бит: naive={row['naive_succeeded']!s:<5}  seeded={row['seeded_succeeded']}")


if __name__ == "__main__":
    main()
