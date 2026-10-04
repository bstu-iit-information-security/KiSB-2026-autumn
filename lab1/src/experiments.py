"""Эксперименты для отчёта. Результаты: папка results/ (PNG + CSV) и вывод в консоль."""
from __future__ import annotations
 
import csv
import os
import statistics
from typing import List
 
from fibonacci import FibonacciGenerator, find_period, search_periods, theoretical_max_period
from primes import generate_prime, theory_survival
from stats import frequency_test, serial_test, runs_test, autocorrelation_test
 
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:                              # графики необязательны
    plt = None
 
RESULTS_DIR = "results"
 
 
def _ensure_dir() -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
 
 
def _save_csv(name: str, header: List[str], rows: List[list]) -> None:
    _ensure_dir()
    path = os.path.join(RESULTS_DIR, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)
    print(f"  [csv] {path}")
 
 
def _save_fig(name: str) -> None:
    if plt is None:
        print("  (matplotlib не установлен - график пропущен)")
        return
    _ensure_dir()
    path = os.path.join(RESULTS_DIR, name)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  [png] {path}")
 
 
# ======================================================================= ЧАСТЬ 1
def exp_best_params(r_max: int = 18) -> None:
    """Для каждого r: какие s дают максимальный период 2^r - 1."""
    print("\n== Эксперимент 1.1. Подбор параметров (r, s) для N = 2 ==")
    print(f"{'r':>3} | {'2^r-1':>8} | {'найденный max T':>15} | s с макс. периодом")
    rows, rs, best = [], [], []
    for r in range(3, r_max + 1):
        res = search_periods(r)
        t_max = max(t for _, t in res)
        good = [s for s, t in res if t == theoretical_max_period(r)]
        print(f"{r:>3} | {2 ** r - 1:>8} | {t_max:>15} | {good if good else 'нет'}")
        rows.append([r, 2 ** r - 1, t_max, " ".join(map(str, good))])
        rs.append(r)
        best.append(t_max)
    _save_csv("exp1_best_params.csv", ["r", "2^r-1", "max_T", "s_max"], rows)
    if plt:
        plt.figure(figsize=(7, 4))
        plt.semilogy(rs, [2 ** r - 1 for r in rs], "k--", label="теория 2^r - 1")
        plt.semilogy(rs, best, "o", label="лучший найденный T")
        plt.xlabel("r")
        plt.ylabel("период T")
        plt.title("Максимальный период генератора Фибоначчи (N=2)")
        plt.legend()
        plt.grid(True, which="both", alpha=0.3)
        _save_fig("exp1_best_params.png")
 
 
def exp_period_vs_s(r: int = 10) -> None:
    """Период при фиксированном r в зависимости от s."""
    print(f"\n== Эксперимент 1.2. Период при r = {r} в зависимости от s ==")
    res = search_periods(r)
    for s, t in res:
        mark = "  <- максимум" if t == 2 ** r - 1 else ""
        print(f"  s={s:>2}: T={t}{mark}")
    _save_csv(f"exp2_period_vs_s_r{r}.csv", ["s", "T"], [[s, t] for s, t in res])
    if plt:
        plt.figure(figsize=(7, 4))
        plt.bar([s for s, _ in res], [t for _, t in res])
        plt.axhline(2 ** r - 1, color="r", ls="--", label=f"2^{r}-1")
        plt.yscale("log")
        plt.xlabel("s")
        plt.ylabel("период T")
        plt.title(f"Период в зависимости от s (r={r})")
        plt.legend()
        _save_fig(f"exp2_period_vs_s_r{r}.png")
 
 
def exp_stat_vs_params(length: int = 20000) -> None:
    """p-value тестов для хороших и плохих параметров/начальных значений."""
    print(f"\n== Эксперимент 1.3. Статистика vs параметры (длина {length}) ==")
    configs = [
        ("(10,3) макс. период", 10, 3, None),
        ("(17,3) макс. период", 17, 3, None),
        ("(31,3) макс. период", 31, 3, None),
        ("(10,5) короткий период", 10, 5, None),
        ("(10,3) нулевое начальное", 10, 3, 0),
        ("(10,3) почти нулевое", 10, 3, 1),
    ]
    header = ["конфигурация", "период T", "доля 1", "p частотный", "p серийный", "p серий", "p автокорр."]
    rows, curves = [], {}
    checkpoints = [10, 30, 100, 300, 1000, 3000, 10000, length]
    for name, r, s, seed in configs:
        T = find_period(r, s, 1, seed) if r <= 20 else theoretical_max_period(r)
        seq = FibonacciGenerator(r, s, 1, seed).sequence(length)
        freq = frequency_test(seq, 2)
        ser = serial_test(seq, 2)
        runs = runs_test(seq)
        ac = autocorrelation_test(seq, 1)
        rows.append([name, T if T else "-", round(sum(seq) / length, 4),
                     round(freq.p_value, 4), round(ser.p_value, 4),
                     round(runs.p_value, 4), round(ac.p_value, 4)])
        curves[name] = [(n, abs(sum(seq[:n]) / n - 0.5)) for n in checkpoints]
    print(" | ".join(header))
    for row in rows:
        print(" | ".join(str(x) for x in row))
    print("  (p-value <= 0.05 -> гипотеза о равномерности/случайности отвергается)")
    _save_csv("exp3_stat_vs_params.csv", header, rows)
    if plt:
        plt.figure(figsize=(7, 4.5))
        for name, pts in curves.items():
            plt.loglog([p[0] for p in pts], [max(p[1], 1e-5) for p in pts], "o-", label=name)
        plt.xlabel("длина префикса n")
        plt.ylabel("|доля единиц - 0.5|")
        plt.title("Сходимость частоты к равномерной")
        plt.legend(fontsize=7)
        plt.grid(True, which="both", alpha=0.3)
        _save_fig("exp3_frequency_convergence.png")
 
 
def exp_length_vs_period() -> None:
    """Что происходит, когда длина выборки превышает период."""
    print("\n== Эксперимент 1.4. Длина выборки относительно периода ==")
    header = ["(r,s)", "T", "длина L", "p частотный", "p серийный", "p серий"]
    rows = []
    for r, s in [(10, 3), (17, 3)]:
        T = 2 ** r - 1
        for L in [100, 1000, 10000, 100000]:
            seq = FibonacciGenerator(r, s, 1).sequence(L)
            rows.append([f"({r},{s})", T, L,
                         round(frequency_test(seq, 2).p_value, 4),
                         round(serial_test(seq, 2).p_value, 4),
                         round(runs_test(seq).p_value, 4)])
    print(" | ".join(header))
    for row in rows:
        print(" | ".join(str(x) for x in row))
    _save_csv("exp4_length_vs_period.csv", header, rows)
 
 
# ======================================================================= ЧАСТЬ 2
def exp_prime_generation(bit_list=(64, 128, 256, 512, 1024), runs: int = 5) -> None:
    """Время и число отсеянных кандидатов для разных разрядностей и порогов просеивания."""
    print("\n== Эксперимент 2.1. Генерация простых чисел (среднее по запускам) ==")
    header = ["бит", "просеивание <", "кандидатов", "отсеяно делением",
              "отсеяно Р-М", "доля пережив. просеивание", "время, с"]
    rows = []
    for bits in bit_list:
        for limit in (0, 256, 2000):
            rng = FibonacciGenerator(127, 1, 1, seed=0xC0FFEE + bits + limit)
            rng.skip(500)
            logs = [generate_prime(bits, rng, small_limit=limit)[1] for _ in range(runs)]
            cand = statistics.mean(l.candidates for l in logs)
            small = statistics.mean(l.rejected_small for l in logs)
            mr = statistics.mean(l.rejected_mr for l in logs)
            tm = statistics.mean(l.time_s for l in logs)
            survive = (cand - small) / cand
            rows.append([bits, limit or "нет", round(cand, 1), round(small, 1),
                         round(mr, 1), round(survive, 3), round(tm, 4)])
    print(" | ".join(header))
    for row in rows:
        print(" | ".join(str(x) for x in row))
    print("  Теория: доля нечётных, не делящихся на простые < z, ~ 1.12/ln z:")
    for z in (256, 2000):
        print(f"    z={z}: {theory_survival(z):.3f}")
    _save_csv("exp5_prime_generation.csv", header, rows)
    if plt:
        plt.figure(figsize=(7, 4.5))
        for limit in (0, 256, 2000):
            pts = [(r[0], r[6]) for r in rows if r[1] == (limit or "нет")]
            plt.plot([p[0] for p in pts], [p[1] for p in pts], "o-",
                     label=f"просеивание < {limit}" if limit else "без просеивания")
        plt.xlabel("разрядность, бит")
        plt.ylabel("среднее время, с")
        plt.yscale("log")
        plt.title("Время генерации простого числа")
        plt.legend()
        plt.grid(True, which="both", alpha=0.3)
        _save_fig("exp5_prime_time.png")
 
 
def exp_sequential_vs_random(bits: int = 512, runs: int = 5) -> None:
    """Случайный кандидат каждый раз vs последовательный перебор n += 2."""
    print(f"\n== Эксперимент 2.2. Случайный vs последовательный перебор ({bits} бит) ==")
    rows = []
    for seq_mode in (False, True):
        rng = FibonacciGenerator(127, 1, 1, seed=0xABCDEF)
        rng.skip(500)
        logs = [generate_prime(bits, rng, 2000, sequential=seq_mode)[1] for _ in range(runs)]
        rows.append(["последовательный" if seq_mode else "случайный",
                     round(statistics.mean(l.candidates for l in logs), 1),
                     round(statistics.mean(l.time_s for l in logs), 4)])
        print(f"  {rows[-1][0]:>16}: кандидатов={rows[-1][1]}, время={rows[-1][2]} с")
    _save_csv("exp6_sequential_vs_random.csv", ["режим", "кандидатов", "время, с"], rows)
 
 
def run_all_experiments() -> None:
    exp_best_params()
    exp_period_vs_s()
    exp_stat_vs_params()
    exp_length_vs_period()
    exp_prime_generation()
    exp_sequential_vs_random()
    print("\nГотово. Файлы в папке results/")
 
