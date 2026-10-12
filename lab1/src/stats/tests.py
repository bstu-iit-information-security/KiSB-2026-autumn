"""
Базовое статистическое тестирование псевдослучайной последовательности
(п.3 задания ЛР №1, Этап 1): частотность появления элементов и проверка
гипотезы о равномерности распределения критерием хи-квадрат Пирсона.
"""
from __future__ import annotations

from collections import Counter

# Табличные критические значения хи-квадрат при уровне значимости alpha=0.05
# (df = alphabet_size - 1). Покрывает алфавиты вплоть до 30 символов (df<=29).
_CHI2_CRITICAL_95: dict[int, float] = {
    1: 3.841, 2: 5.991, 3: 7.815, 4: 9.488, 5: 11.070,
    6: 12.592, 7: 14.067, 8: 15.507, 9: 16.919, 10: 18.307,
    11: 19.675, 12: 21.026, 13: 22.362, 14: 23.685, 15: 24.996,
    16: 26.296, 17: 27.587, 18: 28.869, 19: 30.144, 20: 31.410,
    21: 32.671, 22: 33.924, 23: 35.172, 24: 36.415, 25: 37.652,
    26: 38.885, 27: 40.113, 28: 41.337, 29: 42.557,
}


def frequency_test(seq: list[int], alphabet_size: int) -> dict[int, float]:
    """Относительная частота каждого символа алфавита {0,...,alphabet_size-1}."""
    counts = Counter(seq)
    n = len(seq)
    return {i: counts.get(i, 0) / n for i in range(alphabet_size)}


def chi_square_uniform(seq: list[int], alphabet_size: int) -> tuple[float, int]:
    """
    Критерий хи-квадрат Пирсона для проверки гипотезы H0: последовательность
    равномерно распределена на {0,...,alphabet_size-1}.
    Возвращает (статистика хи-квадрат, число степеней свободы).
    """
    counts = Counter(seq)
    n = len(seq)
    expected = n / alphabet_size
    chi2 = sum(
        (counts.get(i, 0) - expected) ** 2 / expected for i in range(alphabet_size)
    )
    df = alphabet_size - 1
    return chi2, df


def chi_square_critical_95(df: int) -> float | None:
    """Табличное критическое значение хи-квадрат при alpha=0.05."""
    return _CHI2_CRITICAL_95.get(df)


def uniformity_verdict(seq: list[int], alphabet_size: int) -> dict:
    """Удобная обёртка: считает хи-квадрат и сразу формирует вывод по гипотезе."""
    chi2, df = chi_square_uniform(seq, alphabet_size)
    crit = chi_square_critical_95(df)
    accepted = crit is not None and chi2 <= crit
    return {
        "chi2": chi2,
        "df": df,
        "critical_95": crit,
        "uniform_hypothesis_accepted": accepted,
    }
