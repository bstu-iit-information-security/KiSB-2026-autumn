"""
Скрипт автоматического проведения серии экспериментов, сбора статистики
и построения графиков для отчета по Лабораторной работе №1 (Вариант 2).
"""

import os
import sys
import json
import time
import math
from typing import Dict, Any, List

import numpy as np
import matplotlib.pyplot as plt

# Добавляем корень variant2 в пути импорта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.generators.lfsr import LFSR, check_primitive_gf2
from src.generators.shrinking import ShrinkingGenerator
from src.stats.randomness_tests import chi2_bit_uniformity, chi2_block_uniformity, autocorrelation
from src.primality.trial_division import trial_division_filter, SMALL_PRIMES_256
from src.primality.lehmann import lehmann_test
from src.primality.miller_rabin import miller_rabin_test
from src.primality.solovay_strassen import solovay_strassen_test
from src.primality.candidate_pipeline import generate_prime_pipeline, random_candidate_from_sg


def run_prng_experiments() -> Dict[str, Any]:
    """Эксперименты с генераторами ПСП на основе псевдослучайного прореживания."""
    print("[1/3] Запуск статистических тестов генератора (Этап 1)...")
    sample_size = 32000  # Выборка близка к максимальному периоду 32512

    presets = [
        ("f1", "f1(x) = x^7 + x^3 + x^2 + x + 1 (Примитивный)", "f1"),
        ("f2", "f2(x) = x^7 + x + 1 (Примитивный)", "f2"),
        ("f3", "f3(x) = x^7 + x^3 + 1 (Примитивный)", "f3"),
        ("degenerate", "f_deg(x) = x^7 + x^6 + x^2 + 1 (Приводимый)", "degenerate")
    ]

    results = {}

    for key, name, preset_id in presets:
        gen = ShrinkingGenerator(g1_preset=preset_id, seed_g1=0b1010101, seed_g2=0b110011001)
        t0 = time.perf_counter()
        bits = gen.generate_bits(sample_size)
        gen_time = time.perf_counter() - t0

        bit_res = chi2_bit_uniformity(bits)
        block_res = chi2_block_uniformity(bits, block_size=4)
        corrs = autocorrelation(bits, max_lag=10)

        # Подсчет частот 4-битных блоков 0..15
        counts_dict = {i: int(block_res["counts"].get(i, 0)) for i in range(16)}

        results[key] = {
            "name": name,
            "sample_size": sample_size,
            "gen_time_sec": gen_time,
            "total_lfsr_clocks": gen.total_clock_cycles,
            "discarded_clocks": gen.discarded_bits_count,
            "discard_ratio": gen.discarded_bits_count / gen.total_clock_cycles if gen.total_clock_cycles > 0 else 0,
            "chi2_bit": {
                "stat": float(bit_res["chi2_stat"]),
                "critical": float(bit_res["critical_val"]),
                "is_uniform": bool(bit_res["is_uniform"]),
                "zeros": int(bit_res["counts"].get(0, 0)),
                "ones": int(bit_res["counts"].get(1, 0))
            },
            "chi2_block": {
                "stat": float(block_res["chi2_stat"]),
                "critical": float(block_res["critical_val"]),
                "is_uniform": bool(block_res["is_uniform"]),
                "counts": counts_dict,
                "expected": float(block_res["expected_per_symbol"])
            },
            "autocorrelation": [float(c) for c in corrs]
        }
        print(f"  - {key}: chi2_block={block_res['chi2_stat']:.2f} (crit={block_res['critical_val']:.2f}), "
              f"ones_ratio={bit_res['ratio_ones']*100:.1f}%, time={gen_time*1000:.1f} ms")

    return results


def run_primality_experiments() -> Dict[str, Any]:
    """Эксперименты по генерации и тестированию простоты чисел (Этап 2)."""
    print("[2/3] Запуск бенчмарков тестирования простоты (Этап 2)...")
    bit_lengths = [16, 32, 64, 128]
    rounds_count = 15

    results = {
        "pipeline_benchmarks": [],
        "algorithm_timing": []
    }

    sg = ShrinkingGenerator(g1_preset="f1")

    for bits in bit_lengths:
        # Бенчмарк 1: Конвейер генерации простого числа (3 независимых прогона для усреднения)
        attempts_list = []
        sieve_filtered_list = []
        elapsed_list = []
        found_primes = []

        for _ in range(3):
            p, st = generate_prime_pipeline(bits=bits, k_lehmann=rounds_count, sg_generator=sg)
            if p is not None:
                attempts_list.append(st["checked"])
                sieve_filtered_list.append(st["sieve_filtered"])
                elapsed_list.append(st["elapsed"])
                found_primes.append(hex(p))

        mean_checked = float(np.mean(attempts_list)) if attempts_list else 0
        mean_sieve = float(np.mean(sieve_filtered_list)) if sieve_filtered_list else 0
        mean_elapsed = float(np.mean(elapsed_list)) if elapsed_list else 0
        sieve_pct = (mean_sieve / mean_checked * 100) if mean_checked > 0 else 0

        results["pipeline_benchmarks"].append({
            "bits": bits,
            "mean_candidates_checked": mean_checked,
            "mean_sieve_filtered": mean_sieve,
            "sieve_filtered_pct": sieve_pct,
            "mean_elapsed_sec": mean_elapsed,
            "sample_prime_hex": found_primes[0] if found_primes else None
        })

        # Бенчмарк 2: Сравнение скорости тестов на фиксированном наборе из 100 кандидатов
        sample_candidates = [random_candidate_from_sg(bits, sg) for _ in range(100)]

        # Тест Леманна
        t0 = time.perf_counter()
        for cand in sample_candidates:
            lehmann_test(cand, k=rounds_count)
        t_lehmann = (time.perf_counter() - t0) / 100.0

        # Тест Миллера-Рабина
        t0 = time.perf_counter()
        for cand in sample_candidates:
            miller_rabin_test(cand, k=rounds_count)
        t_mr = (time.perf_counter() - t0) / 100.0

        # Тест Соловея-Штрассена
        t0 = time.perf_counter()
        for cand in sample_candidates:
            solovay_strassen_test(cand, k=rounds_count)
        t_ss = (time.perf_counter() - t0) / 100.0

        results["algorithm_timing"].append({
            "bits": bits,
            "lehmann_ms": t_lehmann * 1000.0,
            "miller_rabin_ms": t_mr * 1000.0,
            "solovay_strassen_ms": t_ss * 1000.0
        })

        print(f"  - {bits} бит: кандидатов={mean_checked:.1f}, сито={sieve_pct:.1f}%, "
              f"Леманн={t_lehmann*1000:.3f} мс, Рабин={t_mr*1000:.3f} мс, Соловей={t_ss*1000:.3f} мс")

    return results


def plot_results(prng_data: Dict[str, Any], prime_data: Dict[str, Any]) -> None:
    """Построение и сохранение качественных графиков."""
    print("[3/3] Построение графиков для отчета...")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.titlesize"] = 12
    plt.rcParams["axes.labelsize"] = 11

    plots_dir = os.path.join(BASE_DIR, "assets", "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # -------------------------------------------------------------
    # График 1: Частотное распределение 4-битных символов (0..15)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    x = np.arange(16)
    width = 0.2

    expected = prng_data["f1"]["chi2_block"]["expected"]
    ax.axhline(expected, color="gray", linestyle="--", linewidth=1.5, label=f"Ожидаемое (равномерное: E = {expected:.0f})")

    f1_counts = [prng_data["f1"]["chi2_block"]["counts"][i] for i in range(16)]
    f2_counts = [prng_data["f2"]["chi2_block"]["counts"][i] for i in range(16)]
    f3_counts = [prng_data["f3"]["chi2_block"]["counts"][i] for i in range(16)]
    deg_counts = [prng_data["degenerate"]["chi2_block"]["counts"][i] for i in range(16)]

    ax.bar(x - 1.5 * width, f1_counts, width, label=f"f1 (χ² = {prng_data['f1']['chi2_block']['stat']:.1f})", color="#1f77b4")
    ax.bar(x - 0.5 * width, f2_counts, width, label=f"f2 (χ² = {prng_data['f2']['chi2_block']['stat']:.1f})", color="#2ca02c")
    ax.bar(x + 0.5 * width, f3_counts, width, label=f"f3 (χ² = {prng_data['f3']['chi2_block']['stat']:.1f})", color="#9467bd")
    ax.bar(x + 1.5 * width, deg_counts, width, label=f"f_deg (χ² = {prng_data['degenerate']['chi2_block']['stat']:.1f})", color="#d62728")

    ax.set_title("Сравнение частотного распределения 4-битных блоков SG-генератора\n"
                 "(Критическое значение χ²₀.₀₅,₁₅ = 24.996)", fontweight="bold")
    ax.set_xlabel("Значение 4-битного блока (символ алфавита 0..15)")
    ax.set_ylabel("Частота появления в выборке")
    ax.set_xticks(x)
    ax.set_xticklabels([str(i) for i in range(16)])
    ax.legend(frameon=True, loc="upper right")
    plt.tight_layout()
    plot1_path = os.path.join(plots_dir, "frequency_distribution.png")
    plt.savefig(plot1_path)
    plt.close()
    print(f"  - Сохранен график: {plot1_path}")

    # -------------------------------------------------------------
    # График 2: Автокорреляционная функция R(d)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    lags = np.arange(1, 11)

    r_f1 = prng_data["f1"]["autocorrelation"]
    r_f2 = prng_data["f2"]["autocorrelation"]
    r_f3 = prng_data["f3"]["autocorrelation"]
    r_deg = prng_data["degenerate"]["autocorrelation"]

    # 95% доверительный интервал для белого шума: ±1.96 / sqrt(N)
    n_sample = prng_data["f1"]["sample_size"]
    ci = 1.96 / np.sqrt(n_sample)
    ax.axhline(ci, color="gray", linestyle=":", linewidth=1.2, label=f"95% границы шума (±{ci:.4f})")
    ax.axhline(-ci, color="gray", linestyle=":", linewidth=1.2)
    ax.axhline(0, color="black", linestyle="-", linewidth=0.8)

    ax.plot(lags, r_f1, marker="o", linewidth=1.8, label="f1(x) (Примитивный)", color="#1f77b4")
    ax.plot(lags, r_f2, marker="s", linewidth=1.8, label="f2(x) (Примитивный)", color="#2ca02c")
    ax.plot(lags, r_f3, marker="^", linewidth=1.8, label="f3(x) (Примитивный)", color="#9467bd")
    ax.plot(lags, r_deg, marker="x", linewidth=2.0, linestyle="--", label="f_deg(x) (Приводимый/деградировавший)", color="#d62728")

    ax.set_title("Оценка автокорреляционной функции R(d) для задержек d = 1..10\n"
                 "(SG-генератор с селектором g(x) = x^9 + x^4 + 1)", fontweight="bold")
    ax.set_xlabel("Задержка (лаг d, бит)")
    ax.set_ylabel("Коэффициент автокорреляции R(d)")
    ax.set_xticks(lags)
    ax.legend(frameon=True, loc="upper right")
    plt.tight_layout()
    plot2_path = os.path.join(plots_dir, "autocorrelation.png")
    plt.savefig(plot2_path)
    plt.close()
    print(f"  - Сохранен график: {plot2_path}")

    # -------------------------------------------------------------
    # График 3: Бенчмарки тестирования простоты (время и фильтрация)
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    bits = [item["bits"] for item in prime_data["algorithm_timing"]]
    t_leh = [item["lehmann_ms"] for item in prime_data["algorithm_timing"]]
    t_mr = [item["miller_rabin_ms"] for item in prime_data["algorithm_timing"]]
    t_ss = [item["solovay_strassen_ms"] for item in prime_data["algorithm_timing"]]

    ax1.plot(bits, t_leh, marker="o", linewidth=2, label="Тест Леманна (Вариант 2)", color="#1f77b4")
    ax1.plot(bits, t_mr, marker="s", linewidth=2, label="Тест Рабина — Миллера", color="#ff7f0e")
    ax1.plot(bits, t_ss, marker="^", linewidth=2, label="Тест Соловея — Штрассена", color="#2ca02c")

    ax1.set_title("Время проверки одного кандидата (k = 15)", fontweight="bold")
    ax1.set_xlabel("Разрядность числа (бит)")
    ax1.set_ylabel("Время (мс)")
    ax1.set_xticks(bits)
    ax1.legend(frameon=True)

    # Доля отсеянных ситом кандидатов
    pipe_bits = [item["bits"] for item in prime_data["pipeline_benchmarks"]]
    sieve_pcts = [item["sieve_filtered_pct"] for item in prime_data["pipeline_benchmarks"]]

    bars = ax2.bar([str(b) for b in pipe_bits], sieve_pcts, color="#4c72b0", width=0.5)
    ax2.axhline(80.0, color="red", linestyle="--", linewidth=1.5, label="Теоретический порог (~80%)")
    for bar in bars:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2., h - 8, f"{h:.1f}%", ha="center", va="bottom", color="white", fontweight="bold")

    ax2.set_title("Эффективность сита малых простых (≤ 256)", fontweight="bold")
    ax2.set_xlabel("Разрядность кандидата (бит)")
    ax2.set_ylabel("Доля отсеянных кандидатов (%)")
    ax2.set_ylim(0, 100)
    ax2.legend(frameon=True, loc="lower right")

    plt.suptitle("Исследование эффективности алгоритмов тестирования простоты (Этап 2)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plot3_path = os.path.join(plots_dir, "primality_benchmarks.png")
    plt.savefig(plot3_path)
    plt.close()
    print(f"  - Сохранен график: {plot3_path}")


def main():
    print("=" * 70)
    print("  ЗАПУСК АВТОМАТИЧЕСКИХ ЭКСПЕРИМЕНТОВ И ПОСТРОЕНИЯ ГРАФИКОВ (ВАРИАНТ 2)")
    print("=" * 70)

    prng_results = run_prng_experiments()
    primality_results = run_primality_experiments()

    all_data = {
        "prng_experiments": prng_results,
        "primality_experiments": primality_results,
        "metadata": {
            "variant": 2,
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "Shrinking Generator (LFSR combination)",
            "primality_test": "Lehmann Primality Test (k=15)",
            "congruence": "5x = 3 (mod 12)"
        }
    }

    data_dir = os.path.join(BASE_DIR, "assets", "data")
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, "experiment_results.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\nДанные экспериментов сохранены в: {json_path}")

    plot_results(prng_results, primality_results)
    print("\nЭксперименты и генерация графиков успешно завершены!")


if __name__ == "__main__":
    main()

