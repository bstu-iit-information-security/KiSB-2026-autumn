#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Лабораторная работа №1 (вариант 6)
Этап 1: линейный конгруэнтный генератор (ЛКГ), N = 15
        случай 1 - мультипликативный (Лемер, c = 0), случай 2 - смешанный (c != 0)
Этап 2: тест простоты Леманна + генерация p-битовых простых чисел
        (генератор кандидатов - ЛКГ из этапа 1, просеивание малыми простыми).

Запуск:
    python3 lab1.py stage1            # исследование ЛКГ, графики и таблицы
    python3 lab1.py stage2            # лог генерации простых чисел
    python3 lab1.py gen 256           # одно простое 256-битное число
    python3 lab1.py all
"""
import sys, os, csv, time, math, argparse
from collections import Counter
from math import gcd

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import chi2 as chi2_dist

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)


# =====================================================================
#                              ЭТАП 1
# =====================================================================
class LCG:
    """Линейный конгруэнтный генератор x_{t+1} = (a*x_t + c) mod N.
    c = 0 -> мультипликативный (МКГ, Лемера), c != 0 -> смешанный (СКГ)."""

    def __init__(self, x0, a, c, N):
        if not (0 <= x0 < N and 0 < a < N and 0 <= c < N):
            raise ValueError("Требуется x0, c in A={0..N-1}, a in A\\{0}")
        self.x0, self.a, self.c, self.N = x0, a, c, N
        self.x = x0

    def next(self):
        self.x = (self.a * self.x + self.c) % self.N
        return self.x

    def generate(self, n):
        """Последовательность произвольной длины n: x_1 ... x_n."""
        return [self.next() for _ in range(n)]

    def reset(self):
        self.x = self.x0


def find_period(x0, a, c, N):
    """Возвращает (tau, T): длина предпериода и период последовательности."""
    seen, x, t = {}, x0, 0
    while x not in seen:
        seen[x] = t
        x = (a * x + c) % N
        t += 1
    tau = seen[x]
    return tau, t - tau


def prime_factors(n):
    f, d = set(), 2
    while d * d <= n:
        while n % d == 0:
            f.add(d); n //= d
        d += 1
    if n > 1: f.add(n)
    return f


def hull_dobell(a, c, N):
    """Теоретическое условие T_max = N для ЛКГ (п.4 методички)."""
    a_ok = gcd(c, N) == 1
    b = a - 1
    b_ok = all(b % p == 0 for p in prime_factors(N))
    c_ok = (N % 4 != 0) or (b % 4 == 0)
    return a_ok, b_ok, c_ok, (a_ok and b_ok and c_ok)


def chi_square_uniform(seq, N):
    """Критерий хи-квадрат на равномерность частот элементов алфавита."""
    n = len(seq)
    cnt = Counter(seq)
    obs = np.array([cnt.get(i, 0) for i in range(N)], float)
    exp = n / N
    stat = ((obs - exp) ** 2 / exp).sum()
    p = chi2_dist.sf(stat, N - 1)
    return stat, p, obs


def chi_square_serial(seq, N):
    """Серийный критерий: неперекрывающиеся пары (x_{2i}, x_{2i+1}), N^2 ячеек."""
    pairs = list(zip(seq[0::2], seq[1::2]))
    n = len(pairs)
    cnt = Counter(pairs)
    exp = n / (N * N)
    stat = sum((cnt.get((i, j), 0) - exp) ** 2 / exp for i in range(N) for j in range(N))
    return stat, chi2_dist.sf(stat, N * N - 1), len(cnt)


def autocorr(seq, lag=1):
    x = np.asarray(seq, float)
    x = x - x.mean()
    d = (x * x).sum()
    return float((x[:-lag] * x[lag:]).sum() / d) if d > 0 else float("nan")


def stats_row(seq, N):
    st, p, obs = chi_square_uniform(seq, N)
    s2, p2, used = chi_square_serial(seq, N)
    return dict(n=len(seq), chi2=st, p=p, serial_chi2=s2, serial_p=p2,
                pairs_used=used, mean=float(np.mean(seq)), var=float(np.var(seq)),
                r1=autocorr(seq, 1), obs=obs)


def stage1():
    N = 15
    A_ALPHA = 0.05
    crit = chi2_dist.ppf(1 - A_ALPHA, N - 1)
    lines = []
    P = lambda *s: (print(*s), lines.append(" ".join(str(x) for x in s)))

    P("=" * 78)
    P("ЭТАП 1. ЛКГ, N = 15, алфавит A = {0..14}")
    P("Теор. значения для равномерного распределения: M = %.3f, D = %.3f" %
      ((N - 1) / 2, (N * N - 1) / 12))
    P("Критическое значение хи-квадрат (df=%d, alpha=%.2f): %.3f" % (N - 1, A_ALPHA, crit))
    P("=" * 78)

    # ---------- 1. Теоретический анализ N = 15 ----------
    P("\n[1] N = 15 = 3*5. Простые делители: %s" % sorted(prime_factors(N)))
    P("    Условия T_max = N для смешанного ЛКГ: НОД(c,15)=1; (a-1) кратно 3 и 5 -> a = 1 (mod 15)")
    P("    В алфавите A\\{0} единственное такое a = 1  => x_{t+1} = x_t + c (счётчик)")
    P("    Для МКГ (c=0) максимум периода = lambda(15) = НОК(phi(3),phi(5)) = НОК(2,4) = 4,")
    P("    т.к. группа (Z/15)* не циклическая, первообразных корней по модулю 15 нет.")

    # ---------- 2. Полный перебор ----------
    best_mcg = (0, [])
    mcg_by_a = {}
    for a in range(1, N):
        Ts = []
        for x0 in range(N):
            tau, T = find_period(x0, a, 0, N)
            Ts.append(T)
            if T > best_mcg[0]: best_mcg = (T, [(a, x0)])
            elif T == best_mcg[0]: best_mcg[1].append((a, x0))
        mcg_by_a[a] = max(Ts)
    P("\n[2] Полный перебор МКГ (c=0): T_max = %d, достигается при %d парах (a, x0):" %
      (best_mcg[0], len(best_mcg[1])))
    units = [(a, x0) for a, x0 in best_mcg[1] if gcd(x0, N) == 1]
    pure_u = [(a, x0) for a, x0 in units if find_period(x0, a, 0, N)[0] == 0]
    pre_u = [(a, x0) for a, x0 in units if find_period(x0, a, 0, N)[0] > 0]
    P("    при НОД(x0,15)=1 (требование п.5): T=4 и tau=0 у %d пар, a in %s (a - обратимые элементы порядка 4);"
      % (len(pure_u), sorted({a for a, _ in pure_u})))
    P("    у %d пар a in %s T=4, но есть предпериод tau=1 (a не взаимно просто с 15), чисто периодическими они не являются"
      % (len(pre_u), sorted({a for a, _ in pre_u})))
    P("    Первообразного элемента порядка phi(15)=8 не существует, поэтому T=4 - максимум для МКГ.")

    best_mix = 0
    mix_best = {}
    mix_params = []
    for a in range(1, N):
        mx = 0
        for c in range(1, N):
            for x0 in range(N):
                tau, T = find_period(x0, a, c, N)
                mx = max(mx, T)
                if T > best_mix: best_mix = T; mix_params = [(a, c)]
                elif T == best_mix and (a, c) not in mix_params: mix_params.append((a, c))
        mix_best[a] = mx
    P("    Полный перебор СКГ (c!=0): T_max = %d, достигается ТОЛЬКО при a in %s, c in %s" %
      (best_mix, sorted({a for a, _ in mix_params}), sorted({c for _, c in mix_params})))
    ok = all(hull_dobell(a, c, N)[3] for a, c in mix_params)
    P("    Совпадение с теоретическим условием (п.4): %s" % ("ДА" if ok else "НЕТ"))

    # ---------- 3. Таблица экспериментов ----------
    experiments = [
        ("МКГ", 2, 0, 1), ("МКГ", 7, 0, 1), ("МКГ", 4, 0, 1), ("МКГ", 11, 0, 1),
        ("МКГ", 7, 0, 3), ("МКГ", 7, 0, 5), ("МКГ", 14, 0, 1), ("МКГ", 13, 0, 2),
        ("СКГ", 1, 1, 0), ("СКГ", 1, 7, 0), ("СКГ", 1, 2, 0),
        ("СКГ", 4, 1, 0), ("СКГ", 7, 1, 0), ("СКГ", 7, 2, 0), ("СКГ", 11, 4, 3),
        ("СКГ", 6, 5, 2), ("СКГ", 13, 7, 4),
    ]
    L = 150000   # длина последовательности для статистики (кратна 15 и чётна? 150000/15=10000)
    P("\n[3] Влияние параметров (L = %d элементов; хи-квадрат при df=14: crit=%.2f;"
      " серийный df=224: crit=%.1f)" % (L, crit, chi2_dist.ppf(0.95, N * N - 1)))
    hdr = "%-4s %2s %2s %2s | %3s %3s | %9s %7s | %10s %6s | %6s %6s %7s | %s" % (
        "тип", "a", "c", "x0", "tau", "T", "chi2", "p", "serial", "p", "M", "D", "r1", "T=Tmax")
    P(hdr); P("-" * len(hdr))
    rows = []
    for kind, a, c, x0 in experiments:
        tau, T = find_period(x0, a, c, N)
        seq = LCG(x0, a, c, N).generate(L)
        s = stats_row(seq, N)
        tmax = 4 if kind == "МКГ" else 15
        P("%-4s %2d %2d %2d | %3d %3d | %9.2f %7.4f | %10.1f %6.3f | %6.3f %6.2f %7.3f | %s" % (
            kind, a, c, x0, tau, T, s["chi2"], s["p"], s["serial_chi2"], s["serial_p"],
            s["mean"], s["var"], s["r1"], "да" if T == tmax else "нет"))
        rows.append(dict(kind=kind, a=a, c=c, x0=x0, tau=tau, T=T, **{k: v for k, v in s.items() if k != "obs"}))
    with open(os.path.join(OUT, "stage1_table.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader(); w.writerows(rows)

    # ---------- 4. Зависимость хи-квадрат от длины ----------
    P("\n[4] Хи-квадрат от длины последовательности (СКГ a=1,c=1 [T=15] и МКГ a=2 [T=4])")
    lens = [15, 45, 150, 450, 1500, 4500, 15000, 150000]
    chi_a, chi_b, chi_c = [], [], []
    P("%8s | %12s | %12s | %12s" % ("L", "СКГ(1,1,0)", "МКГ(2,0,1)", "МКГ(7,0,1)"))
    for n in lens:
        r1_ = chi_square_uniform(LCG(0, 1, 1, N).generate(n), N)[0]
        r2_ = chi_square_uniform(LCG(1, 2, 0, N).generate(n), N)[0]
        r3_ = chi_square_uniform(LCG(1, 7, 0, N).generate(n), N)[0]
        chi_a.append(r1_); chi_b.append(r2_); chi_c.append(r3_)
        P("%8d | %12.2f | %12.2f | %12.2f" % (n, r1_, r2_, r3_))
    P("    Порог (alpha=0.05): %.2f. МКГ покрывает лишь T=4 значения из 15, поэтому равномерность отвергается;"
      " СКГ a=1 даёт chi2=0 (идеально ровные частоты) только потому, что это счётчик x+c." % crit)

    # ---------- 5. Какие значения достижимы ----------
    P("\n[5] Покрытие алфавита (число различных значений = T):")
    for a in (2, 4, 7, 11, 13, 14):
        seq = LCG(1, a, 0, N).generate(100)
        P("    МКГ a=%2d x0=1: значения %s" % (a, sorted(set(seq))))

    # ---------- Графики ----------
    # (а) гистограммы
    cfg = [("СКГ a=1,c=1 (T=15=Tmax)", LCG(0, 1, 1, N)),
           ("СКГ a=4,c=1 (T<Tmax)", LCG(0, 4, 1, N)),
           ("МКГ a=7,x0=1 (T=4=Tmax)", LCG(1, 7, 0, N)),
           ("МКГ a=14,x0=1 (T=2)", LCG(1, 14, 0, N))]
    fig, ax = plt.subplots(2, 2, figsize=(11, 7))
    for axx, (ttl, g) in zip(ax.ravel(), cfg):
        seq = g.generate(L)
        s = chi_square_uniform(seq, N)
        axx.bar(range(N), s[2], color="#4C78A8")
        axx.axhline(L / N, color="red", ls="--", lw=1)
        axx.set_title("%s\nchi2=%.1f, p=%.3f" % (ttl, s[0], s[1]), fontsize=10)
        axx.set_xticks(range(N)); axx.set_xlabel("значение"); axx.set_ylabel("частота")
    fig.suptitle("Частоты элементов, L=%d (красная линия — ожидаемая частота)" % L)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig1_hist.png"), dpi=130); plt.close(fig)

    # (б) максимальные периоды по a
    fig, ax = plt.subplots(figsize=(9, 4.5))
    xs = np.arange(1, N)
    ax.bar(xs - 0.2, [mcg_by_a[a] for a in xs], 0.4, label="МКГ (c=0), max по x0", color="#F58518")
    ax.bar(xs + 0.2, [mix_best[a] for a in xs], 0.4, label="СКГ (c≠0), max по c,x0", color="#4C78A8")
    ax.axhline(15, color="gray", ls=":"); ax.text(1, 15.2, "N=15")
    ax.set_xticks(xs); ax.set_xlabel("множитель a"); ax.set_ylabel("максимальный период T")
    ax.set_title("Максимальный период ЛКГ при N=15 (полный перебор)"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig2_period_by_a.png"), dpi=130); plt.close(fig)

    # (в) хи-квадрат от длины
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.loglog(lens, np.maximum(chi_a, 1e-3), "o-", label="СКГ a=1,c=1 (T=15)")
    ax.loglog(lens, chi_b, "s-", label="МКГ a=2,x0=1 (T=4)")
    ax.loglog(lens, chi_c, "^-", label="МКГ a=7,x0=1 (T=4)")
    ax.axhline(crit, color="red", ls="--", label="порог α=0.05 (%.1f)" % crit)
    ax.set_xlabel("длина последовательности L"); ax.set_ylabel("статистика χ²")
    ax.set_title("Рост χ² с ростом длины (периодичность видна на длинных выборках)")
    ax.legend(); ax.grid(True, which="both", alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig3_chi_vs_len.png"), dpi=130); plt.close(fig)

    # (г) диаграмма рассеяния (x_t, x_{t+1})
    cfg2 = [("СКГ a=1,c=1", LCG(0, 1, 1, N)), ("СКГ a=4,c=1", LCG(0, 4, 1, N)),
            ("СКГ a=11,c=4", LCG(3, 11, 4, N)), ("МКГ a=7", LCG(1, 7, 0, N))]
    fig, ax = plt.subplots(1, 4, figsize=(14, 3.6))
    for axx, (ttl, g) in zip(ax, cfg2):
        s = g.generate(3000)
        axx.scatter(s[:-1], s[1:], s=18, alpha=.6)
        axx.set_title(ttl); axx.set_xlim(-1, N); axx.set_ylim(-1, N)
        axx.set_xlabel("$x_t$"); axx.set_ylabel("$x_{t+1}$")
    fig.suptitle("Парные точки (x_t, x_{t+1}): число различных пар = число состояний")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig4_scatter.png"), dpi=130); plt.close(fig)

    P("\nГрафики: fig1_hist.png, fig2_period_by_a.png, fig3_chi_vs_len.png, fig4_scatter.png")
    with open(os.path.join(OUT, "stage1_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# =====================================================================
#                              ЭТАП 2
# =====================================================================
def primes_upto(n):
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(n ** .5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i, v in enumerate(sieve) if v]


class BigLCG(LCG):
    """Тот же ЛКГ, но с модулем N = 2^32 и параметрами по теореме Халла-Добелла
    (c нечётно, a-1 кратно 4, T_max = 2^32). Параметры Numerical Recipes.
    Для N = 15 получить p-битовые числа невозможно (15 состояний), поэтому для
    этапа 2 берётся ЛКГ с тем же рекуррентным соотношением и большим модулем.
    Младшие биты ЛКГ с N=2^k имеют короткие периоды, поэтому берутся старшие 16 бит."""

    def __init__(self, seed=None):
        N, a, c = 2 ** 32, 1664525, 1013904223
        assert hull_dobell(a, c, N)[3]
        if seed is None:
            seed = int(time.time_ns()) % N
        super().__init__(seed % N, a, c, N)

    def bits(self, p):
        """p случайных бит из выхода ЛКГ (по 16 старших бит за шаг)."""
        v, got = 0, 0
        while got < p:
            v = (v << 16) | (self.next() >> 16)
            got += 16
        return v >> (got - p)

    def randrange(self, lo, hi):
        """Случайное целое из [lo, hi)."""
        span = hi - lo
        return lo + self.bits(span.bit_length() + 16) % span


def lehmann(n, rng, k=20):
    """Тест Леманна. Возвращает 'composite' или 'probably prime'.
    Для n нечётного: a случайно, t = a^((n-1)/2) mod n.
    t не равно +-1 -> составное. Если t = +-1 во всех k раундах и хотя бы раз t = -1,
    то n простое с вероятностью ошибки <= 2^-k."""
    if n < 2: return "composite"
    if n in (2, 3): return "probably prime"
    if n % 2 == 0: return "composite"
    seen_minus = False
    for _ in range(k):
        a = rng.randrange(2, n - 1)
        t = pow(a, (n - 1) // 2, n)
        if t == n - 1: seen_minus = True
        elif t != 1: return "composite"
    return "probably prime" if seen_minus else "composite"   # все t=1: не доказано (случай 2^-k для простых)


def generate_prime(p, rng, sieve_bound=2000, k=20, sequential=False):
    """Схема генерации из задания. Возвращает (prime, статистика)."""
    small = primes_upto(sieve_bound)
    st = dict(candidates=0, sieve_rej=0, lehmann_rej=0, lehmann_calls=0)
    t0 = time.perf_counter()
    n = None
    while True:
        if n is None or not sequential:
            n = rng.bits(p)                          # 1. случайное p-битовое число
            n |= (1 << (p - 1)) | 1                  # 2. старший и младший биты = 1
        else:
            n += 2                                   # перебор подряд нечётных
            if n.bit_length() > p: n = (1 << (p - 1)) | 1
        st["candidates"] += 1
        # 3. просеивание малыми простыми
        if any(n % q == 0 and n != q for q in small):
            st["sieve_rej"] += 1
            continue
        # 4. тест Леманна
        st["lehmann_calls"] += 1
        if lehmann(n, rng, k) == "composite":
            st["lehmann_rej"] += 1
            continue
        st["time"] = time.perf_counter() - t0
        return n, st


def stage2():
    from sympy import isprime
    lines = []
    P = lambda *s: (print(*s), lines.append(" ".join(str(x) for x in s)))
    P("=" * 78)
    P("ЭТАП 2. Генерация простых чисел: ЛКГ + просеивание + тест Леманна (k=20)")
    P("=" * 78)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    rng = BigLCG(seed=20260101)

    P("\n[1] Подробный лог (по одному числу каждого размера, просеивание < 2000)")
    for p in sizes:
        n, st = generate_prime(p, rng)
        P("p=%4d бит | кандидатов %5d | отсеяно делением %5d (%.1f%%) | отсеяно Леманном %3d "
          "| вызовов теста %3d | время %9.2f мс | sympy.isprime=%s" % (
              p, st["candidates"], st["sieve_rej"], 100 * st["sieve_rej"] / st["candidates"],
              st["lehmann_rej"], st["lehmann_calls"], st["time"] * 1000, isprime(n)))
        if p <= 128: P("      n = %d" % n)
        else: P("      n = %s...%s (%d десятичных цифр)" % (str(n)[:20], str(n)[-12:], len(str(n))))

    P("\n[2] Статистика по 20 запускам (среднее), граница просеивания 256 vs 2000")
    P("%5s | %6s | %9s %9s %9s | %9s %9s %9s" % ("p", "граница", "канд.", "делением", "Леманн", "t, мс", "", ""))
    rows = []
    for p in sizes:
        for bound in (256, 2000):
            agg = Counter(); tt = 0
            R = 20
            for _ in range(R):
                n, st = generate_prime(p, rng, sieve_bound=bound)
                assert isprime(n)
                for kk in ("candidates", "sieve_rej", "lehmann_rej", "lehmann_calls"): agg[kk] += st[kk]
                tt += st["time"]
            row = dict(bits=p, bound=bound, candidates=agg["candidates"] / R,
                       sieve_rej=agg["sieve_rej"] / R, lehmann_rej=agg["lehmann_rej"] / R,
                       lehmann_calls=agg["lehmann_calls"] / R, time_ms=1000 * tt / R)
            rows.append(row)
            P("%5d | %7d | %9.1f %9.1f %9.1f | %9.2f" % (
                p, bound, row["candidates"], row["sieve_rej"], row["lehmann_rej"], row["time_ms"]))
    P("    Все %d сгенерированных чисел перепроверены sympy.isprime — ошибок нет." % (len(rows) * 20))
    P("    Теория: доля нечётных, не делящихся на простые < z, ~ 1.12/ln z: z=256 -> %.1f%%, z=2000 -> %.1f%%" % (
        112 / math.log(256), 112 / math.log(2000)))
    with open(os.path.join(OUT, "stage2_table.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader(); w.writerows(rows)

    # графики
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for bound, mk in ((256, "o-"), (2000, "s-")):
        r = [x for x in rows if x["bound"] == bound]
        ax[0].semilogy([x["bits"] for x in r], [x["time_ms"] for x in r], mk, label="просеивание < %d" % bound)
        ax[1].plot([x["bits"] for x in r], [100 * x["sieve_rej"] / x["candidates"] for x in r], mk, label="< %d" % bound)
    ax[0].set_xlabel("разрядность p"); ax[0].set_ylabel("среднее время, мс"); ax[0].set_title("Время генерации простого")
    ax[0].grid(True, which="both", alpha=.3); ax[0].legend()
    ax[1].set_xlabel("разрядность p"); ax[1].set_ylabel("% кандидатов, отсеянных делением")
    ax[1].set_title("Эффективность просеивания"); ax[1].grid(alpha=.3); ax[1].legend()
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig5_stage2.png"), dpi=130); plt.close(fig)

    # корректность теста Леманна
    P("\n[3] Проверка корректности теста Леманна (k=20) в сравнении с sympy.isprime")
    rng2 = BigLCG(seed=7)
    LIM = 30000
    fn = fp = 0
    for n in range(3, LIM, 2):
        r = lehmann(n, rng2, 20) == "probably prime"
        if r and not isprime(n): fp += 1
        if (not r) and isprime(n): fn += 1
    P("    n = 3..%d (нечётные): ложных 'простое' = %d, ложных 'составное' = %d" % (LIM, fp, fn))
    carm = [561, 1105, 1729, 2465, 2821, 6601, 8911, 10585, 15841, 29341, 41041, 46657, 52633, 62745, 63973, 75361]
    res = [lehmann(n, rng2, 20) for n in carm]
    P("    Числа Кармайкла до 1e5: распознано как составные %d из %d" % (res.count("composite"), len(carm)))
    P("    Псевдопростое по основанию 2: 341 -> %s" % lehmann(341, rng2, 20))
    P("    Известные простые: 2^61-1 -> %s; 2^127-1 -> %s" % (lehmann(2 ** 61 - 1, rng2), lehmann(2 ** 127 - 1, rng2)))
    P("    Составное 2^61+1 -> %s" % lehmann(2 ** 61 + 1, rng2))
    with open(os.path.join(OUT, "stage2_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stage1", "stage2", "gen", "all"])
    ap.add_argument("bits", nargs="?", type=int, default=256)
    a = ap.parse_args()
    if a.cmd in ("stage1", "all"): stage1()
    if a.cmd in ("stage2", "all"): stage2()
    if a.cmd == "gen":
        n, st = generate_prime(a.bits, BigLCG())
        print(n); print(st)


if __name__ == "__main__":
    main()
