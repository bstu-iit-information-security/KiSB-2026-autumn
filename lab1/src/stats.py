"""Статистические тесты равномерности/случайности последовательности.
 
Без внешних библиотек: p-value для хи-квадрат считается через
регуляризованную неполную гамма-функцию.
"""
from __future__ import annotations
 
import math
from dataclasses import dataclass
from typing import List, Optional, Sequence
 
 
# -------------------------------------------------------- хи-квадрат: p-value
def _gamma_series(a: float, x: float) -> float:
    ap, total = a, 1.0 / a
    delta = total
    for _ in range(2000):
        ap += 1
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * 1e-15:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
 
 
def _gamma_cf(a: float, x: float) -> float:
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 2000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
 
 
def chi2_sf(x: float, df: int) -> float:
    """P(chi2_df >= x)."""
    if x <= 0:
        return 1.0
    a, xx = df / 2.0, x / 2.0
    if xx < a + 1:
        return 1.0 - _gamma_series(a, xx)
    return _gamma_cf(a, xx)
 
 
# ------------------------------------------------------------- результат
@dataclass
class TestResult:
    name: str
    statistic: float
    p_value: float
    alpha: float
    df: Optional[int] = None
 
    @property
    def passed(self) -> bool:
        return self.p_value > self.alpha
 
    def __str__(self) -> str:
        df = f", df={self.df}" if self.df is not None else ""
        verdict = "ПРОЙДЕН" if self.passed else "НЕ ПРОЙДЕН"
        return (f"{self.name}: статистика={self.statistic:.4f}{df}, "
                f"p-value={self.p_value:.4f} -> {verdict} (alpha={self.alpha})")
 
 
def _chi2_from_counts(name: str, counts: Sequence[int], alpha: float) -> TestResult:
    total = sum(counts)
    expected = total / len(counts)
    chi2 = sum((c - expected) ** 2 / expected for c in counts)
    df = len(counts) - 1
    return TestResult(name, chi2, chi2_sf(chi2, df), alpha, df)
 
 
# ------------------------------------------------------------------ тесты
def frequencies(seq: Sequence[int], N: int) -> List[int]:
    counts = [0] * N
    for x in seq:
        counts[x] += 1
    return counts
 
 
def frequency_test(seq: Sequence[int], N: int, alpha: float = 0.05) -> TestResult:
    """H0: все символы алфавита равновероятны (критерий хи-квадрат)."""
    return _chi2_from_counts("Частотный (хи-квадрат)", frequencies(seq, N), alpha)
 
 
def serial_test(seq: Sequence[int], N: int, alpha: float = 0.05) -> TestResult:
    """Серийный тест: непересекающиеся пары (a, b) равновероятны, N^2 классов."""
    counts = [0] * (N * N)
    for i in range(0, len(seq) - 1, 2):
        counts[seq[i] * N + seq[i + 1]] += 1
    return _chi2_from_counts("Серийный (пары, хи-квадрат)", counts, alpha)
 
 
def runs_test(seq: Sequence[int], alpha: float = 0.05) -> Optional[TestResult]:
    """Тест серий Вальда-Вольфовица (только для двоичной последовательности)."""
    n = len(seq)
    n1 = sum(1 for x in seq if x == 1)
    n0 = n - n1
    runs = 1 + sum(1 for i in range(1, n) if seq[i] != seq[i - 1])
    mu = 2 * n0 * n1 / n + 1
    var = (mu - 1) * (mu - 2) / (n - 1)
    if var <= 0:
        return TestResult("Серий (Вальд-Вольфовиц)", float("inf"), 0.0, alpha)
    z = (runs - mu) / math.sqrt(var)
    return TestResult("Серий (Вальд-Вольфовиц)", z, math.erfc(abs(z) / math.sqrt(2)), alpha)
 
 
def autocorrelation_test(seq: Sequence[int], lag: int = 1, alpha: float = 0.05) -> TestResult:
    """Коэффициент автокорреляции со сдвигом lag; H0: он равен 0."""
    n = len(seq)
    mean = sum(seq) / n
    var = sum((x - mean) ** 2 for x in seq) / n
    name = f"Автокорреляция (lag={lag})"
    if var == 0:
        return TestResult(name, float("nan"), 0.0, alpha)
    cov = sum((seq[i] - mean) * (seq[i + lag] - mean) for i in range(n - lag)) / (n - lag)
    rho = cov / var
    z = rho * math.sqrt(n - lag)
    return TestResult(name, rho, math.erfc(abs(z) / math.sqrt(2)), alpha)
 
 
def run_all(seq: Sequence[int], N: int, alpha: float = 0.05) -> List[TestResult]:
    results = [frequency_test(seq, N, alpha), serial_test(seq, N, alpha)]
    if N == 2:
        results.append(runs_test(seq, alpha))
    results.append(autocorrelation_test(seq, 1, alpha))
    return results
 
