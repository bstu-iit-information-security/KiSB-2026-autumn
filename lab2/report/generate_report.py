"""
Формирует материалы для отчёта по ЛР №2 (Вариант 1):

  report/report_data.json        - все числовые результаты
  report/results_tables.md       - таблицы (параметры кодов, N2/N1, N3/N1 по кратностям)
  report/demo_hamming.txt        - примеры работы (d_min = 3 и 4; 0, 1, 2 ошибки)
  report/demo_iterative.txt      - примеры работы итеративных кодов
  report/hamming_matrices.txt    - матрицы H для k = 4, 6, 8, 9, 10, 15, 16
  report/figures/*.png           - графики

Запуск (из директории lab2/):  python3 report/generate_report.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.experiments import error_table
from src.hamming import HammingCode
from src.iterative import VARIANT1_CONFIGS, IterativeCode, IterativeConfig
from src.reports import (
    _fmt_rows,
    hamming_demo,
    hamming_matrices_report,
    iterative_demo,
    iterative_parameters_report,
    iterative_parameters_rows,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)

SEED = 2026
TRIALS = 10000
MAX_WEIGHT = 3
MAX_I = 5


def write(name: str, text: str) -> None:
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def dims(k1, k2, z) -> str:
    return f"{k1}x{k2}" + (f"x{z}" if z > 1 else "")


# ----------------------------------------------------------------------------- Хемминг
def hamming_section() -> dict:
    data = {}
    for d in (3, 4):
        c = HammingCode(16, d)
        data[f"d{d}"] = {
            "n": c.n, "r": c.r, "rate": c.rate, "dmin_measured": c.min_distance(),
            "rows": error_table(c, 4, TRIALS, 1, SEED, exhaustive_up_to=2),
        }

    # график: исходы декодирования для кратностей 1..3
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    colors = {"exact": "tab:green", "miscorrected": "tab:red", "detected": "tab:orange", "undetected": "tab:gray"}
    names = {"exact": "исправлено верно", "miscorrected": "ошибочная коррекция",
             "detected": "обнаружено, не исправлено", "undetected": "не обнаружено"}
    for ax, d in zip(axes, (3, 4)):
        rows = data[f"d{d}"]["rows"][:3]
        bottom = [0.0] * len(rows)
        for key in ("exact", "miscorrected", "detected", "undetected"):
            vals = [r[key] / r["N1"] for r in rows]
            ax.bar([f"i={r['i']}" for r in rows], vals, bottom=bottom, color=colors[key], label=names[key])
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.set_title(f"Код Хемминга (21/22, 16), d_min = {d}")
        ax.set_ylabel("доля случаев")
    axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Исходы декодирования при ошибках кратности i (k = 16)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "hamming_outcomes.png"), dpi=150)
    plt.close(fig)

    # график: r и скорость от k
    ks = list(range(4, 65))
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(ks, [HammingCode(k, 3).r for k in ks], label="r (d_min = 3)")
    ax1.plot(ks, [HammingCode(k, 4).r for k in ks], label="r (d_min = 4)")
    ax1.set_xlabel("длина информационного слова k, бит")
    ax1.set_ylabel("число проверочных символов r")
    ax2 = ax1.twinx()
    ax2.plot(ks, [HammingCode(k, 3).rate for k in ks], "k--", label="R = k/n (d_min = 3)")
    ax2.set_ylabel("скорость кода R")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="center right")
    ax1.set_title("Избыточность кода Хемминга растёт как log2(k)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "hamming_r_vs_k.png"), dpi=150)
    plt.close(fig)
    return data


# ------------------------------------------------------------------------- итеративные
def iterative_section() -> dict:
    data = {"params": iterative_parameters_rows(), "tables": {}}
    for idx, (k1, k2, z, allowed) in enumerate(VARIANT1_CONFIGS, 1):
        for g in allowed:
            c = IterativeCode(IterativeConfig(k1, k2, z, g))
            data["tables"][f"{idx}-{g}"] = error_table(c, MAX_I, TRIALS, MAX_WEIGHT, SEED)

    # N3/N1 и доля опасных исходов по кратностям
    for key, fname, title, ylabel in (
        ("good", "iterative_correction.png", "Доля полностью исправленных ошибок N3/N1", "N3/N1"),
        ("bad", "iterative_dangerous.png", "Опасные исходы: ошибочная коррекция + необнаруженная ошибка", "доля опасных исходов"),
    ):
        fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, sharey=True)
        for ax, (idx, (k1, k2, z, allowed)) in zip(axes.flat, enumerate(VARIANT1_CONFIGS, 1)):
            for g in allowed:
                rows = data["tables"][f"{idx}-{g}"]
                xs = [r["i"] for r in rows]
                if key == "good":
                    ys = [r["N3/N1"] for r in rows]
                else:
                    ys = [(r["miscorrected"] + r["undetected"]) / r["N1"] for r in rows]
                style = {"linestyle": ["-", "-", "--", ":"][g - 2], "marker": ["o", "s", "^", "x"][g - 2]}
                ax.plot(xs, ys, label=f"{g} гр.", **style)
            ax.axvline(MAX_WEIGHT + 0.5, color="gray", linestyle="--", linewidth=0.8)
            ax.text(MAX_WEIGHT + 0.55, 0.5 if key == "good" else 0.05, "предел\nдекодера", fontsize=7, color="gray")
            ax.set_xticks(range(1, MAX_I + 1))
            ax.set_title(f"конф. {idx}: {dims(k1, k2, z)}")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
        for ax in axes[1]:
            ax.set_xlabel("кратность ошибки i")
        for ax in axes[:, 0]:
            ax.set_ylabel(ylabel)
        fig.suptitle(title + " (вариант 1, k = 16)")
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, fname), dpi=150)
        plt.close(fig)

    # скорость и d_min в зависимости от числа групп
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    for idx, (k1, k2, z, allowed) in enumerate(VARIANT1_CONFIGS, 1):
        rows = [p for p in data["params"] if p["config"] == idx]
        ax1.plot([p["groups"] for p in rows], [p["rate"] for p in rows], marker="o", label=f"{idx}: {dims(k1, k2, z)}")
        ax2.plot([p["groups"] for p in rows], [p["dmin"] for p in rows], marker="s", label=f"{idx}: {dims(k1, k2, z)}")
    ax1.set_xlabel("число групп паритетов"); ax1.set_ylabel("скорость k/(k+r)"); ax1.legend(); ax1.grid(alpha=0.3)
    ax2.set_xlabel("число групп паритетов"); ax2.set_ylabel("d_min (измерено)"); ax2.legend(); ax2.grid(alpha=0.3)
    ax1.set_xticks([2, 3, 4, 5]); ax2.set_xticks([2, 3, 4, 5])
    fig.suptitle("Цена надёжности: скорость падает, d_min растёт на 1 с каждой группой")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "iterative_rate_dmin.png"), dpi=150)
    plt.close(fig)
    return data


def main() -> None:
    ham = hamming_section()
    it = iterative_section()

    with open(os.path.join(HERE, "report_data.json"), "w", encoding="utf-8") as f:
        json.dump({"seed": SEED, "trials": TRIALS, "max_weight": MAX_WEIGHT, "hamming": ham, "iterative": it},
                  f, ensure_ascii=False, indent=2)

    # таблицы
    md = ["# ЛР №2. Результаты экспериментов (вариант 1)", "",
          f"Параметры эксперимента: seed = {SEED}; для кратностей i = 1, 2 перебираются ВСЕ ошибки, "
          f"для i >= 3 - {TRIALS} случайных; таблица лидеров синдромов строится до веса {MAX_WEIGHT}.", "",
          "## Часть 1. Код Хемминга (k = 16)", ""]
    for d in (3, 4):
        v = ham[f"d{d}"]
        md.append(f"d_min = {d}: ({v['n']},16)-код, r = {v['r']}, R = {v['rate']:.3f}, измеренное d_min = {v['dmin_measured']}")
        md.append("")
        md += _fmt_rows(v["rows"])
        md.append("")
    md += ["## Часть 2. Итеративные коды", "", iterative_parameters_report(), ""]
    for idx, (k1, k2, z, allowed) in enumerate(VARIANT1_CONFIGS, 1):
        for g in allowed:
            md.append(f"### Конфигурация {idx}: {dims(k1, k2, z)}, групп паритетов: {g}")
            md.append("")
            md += _fmt_rows(it["tables"][f"{idx}-{g}"])
            md.append("")
    write("results_tables.md", "\n".join(md))

    # демонстрации
    demos = []
    for d in (3, 4):
        for e in (0, 1, 2):
            demos.append(f"{'=' * 78}\nКод Хемминга, d_min = {d}, ошибок: {e}\n{'=' * 78}\n" + hamming_demo("Hi", d, e, seed=11))
    write("demo_hamming.txt", "\n\n".join(demos))
    write("hamming_matrices.txt", hamming_matrices_report())

    demos = []
    for idx, (k1, k2, z, allowed) in enumerate(VARIANT1_CONFIGS, 1):
        for g in (allowed[0], allowed[-1]):
            for e in (1, 2):
                demos.append(f"{'=' * 78}\nКонфигурация {idx}, групп: {g}, ошибок: {e}\n{'=' * 78}\n"
                             + iterative_demo(idx, g, e, seed=5))
    write("demo_iterative.txt", "\n\n".join(demos))

    print("Готово:")
    for name in sorted(os.listdir(HERE)):
        if name.endswith((".json", ".md", ".txt")):
            print("  report/" + name)
    for name in sorted(os.listdir(FIG)):
        print("  report/figures/" + name)


if __name__ == "__main__":
    main()
