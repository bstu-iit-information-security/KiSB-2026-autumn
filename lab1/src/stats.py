"""Статистическая оценка равномерности последовательностей (Этап 1)."""

from __future__ import annotations
import math


# ---- функция распределения хи-квадрат (без scipy) -------------------------------
def _gammainc_upper(a: float, x: float) -> float:
    """Регуляризованная верхняя неполная гамма Q(a, x)."""
    if x <= 0:
        return 1.0
    if x < a + 1:  # ряд
        term = s = 1.0 / a
        n = a
        while abs(term) > abs(s) * 1e-14:
            n += 1
            term *= x / n
            s += term
        return 1.0 - s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # цепная дробь Лентца
    b = x + 1 - a
    c = 1e300
    d = 1 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_pvalue(stat: float, df: int) -> float:
    return _gammainc_upper(df / 2, stat / 2)


# ---- тесты ----------------------------------------------------------------------
def monobit(bits: list[int]) -> dict:
    n = len(bits)
    ones = sum(bits)
    chi = (ones - (n - ones)) ** 2 / n          # df = 1
    return {"n": n, "ones": ones, "zeros": n - ones, "chi2": chi, "p": chi2_pvalue(chi, 1)}


def block_frequency(bits: list[int], k: int) -> dict:
    """Частоты k-битных слов (без перекрытия) и хи-квадрат относительно равномерного распределения."""
    m = len(bits) // k
    cnt = [0] * (1 << k)
    for i in range(m):
        v = 0
        for b in bits[i * k:(i + 1) * k]:
            v = (v << 1) | b
        cnt[v] += 1
    exp = m / (1 << k)
    chi = sum((c - exp) ** 2 / exp for c in cnt)
    return {"k": k, "words": m, "counts": cnt, "chi2": chi, "df": (1 << k) - 1,
            "p": chi2_pvalue(chi, (1 << k) - 1)}


def runs_test(bits: list[int]) -> dict:
    """Тест серий (Вальда-Вольфовица): число серий одинаковых бит."""
    n, n1 = len(bits), sum(bits)
    n0 = n - n1
    runs = 1 + sum(bits[i] != bits[i - 1] for i in range(1, n))
    mu = 2 * n0 * n1 / n + 1
    var = (mu - 1) * (mu - 2) / (n - 1)
    z = (runs - mu) / math.sqrt(var) if var > 0 else float("inf")
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"runs": runs, "expected": mu, "z": z, "p": p}


def autocorrelation(bits: list[int], d: int) -> float:
    """Нормированная автокорреляция по +-1 при сдвиге d."""
    s = [1 - 2 * b for b in bits]
    n = len(s) - d
    return sum(s[i] * s[i + d] for i in range(n)) / n


def full_report(bits: list[int], k: int = 4) -> dict:
    return {
        "monobit": monobit(bits),
        "blocks": block_frequency(bits, k),
        "runs": runs_test(bits),
        "autocorr_1": autocorrelation(bits, 1),
        "autocorr_7": autocorrelation(bits, 7),
    }
