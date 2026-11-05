"""
Модуль статистического тестирования псевдослучайных последовательностей.
Реализует критерий согласия Хи-квадрат Пирсона, оценку автокорреляции и частотный анализ.
"""

import math
from collections import Counter
from typing import List, Dict, Any


def chi2_bit_uniformity(bits: List[int], alpha: float = 0.05) -> Dict[str, Any]:
    """
    Критерий Хи-квадрат Пирсона для проверки равномерности распределения битов {0, 1}.
    Число степеней свободы df = 2 - 1 = 1.
    Критическое значение для alpha = 0.05 равно 3.8415.
    """
    n = len(bits)
    if n == 0:
        return {"chi2_stat": 0.0, "critical_val": 3.8415, "is_uniform": True, "counts": {}}

    counts = Counter(bits)
    zeros = counts.get(0, 0)
    ones = counts.get(1, 0)
    expected = n / 2.0

    chi2_stat = ((zeros - expected) ** 2 / expected) + ((ones - expected) ** 2 / expected)
    crit_val = 3.8415

    return {
        "chi2_stat": chi2_stat,
        "critical_val": crit_val,
        "is_uniform": chi2_stat <= crit_val,
        "counts": {0: zeros, 1: ones},
        "ratio_ones": ones / n if n > 0 else 0.0
    }


def chi2_block_uniformity(bits: List[int], block_size: int = 4, alpha: float = 0.05) -> Dict[str, Any]:
    """
    Критерий Хи-квадрат для проверки распределения блоков длины block_size (размер алфавита N = 2^block_size).
    Для block_size=4, N=16, df=15, критическое значение для alpha=0.05 равно 24.9958.
    """
    alphabet_size = 1 << block_size
    num_blocks = len(bits) // block_size
    if num_blocks == 0:
        return {"chi2_stat": 0.0, "critical_val": 24.9958, "is_uniform": True, "counts": {}}

    values = []
    for i in range(num_blocks):
        block = bits[i * block_size : (i + 1) * block_size]
        val = 0
        for b in block:
            val = (val << 1) | b
        values.append(val)

    counts = Counter(values)
    expected = num_blocks / alphabet_size

    chi2_stat = sum((counts.get(k, 0) - expected) ** 2 / expected for k in range(alphabet_size))

    # Табличные критические значения хи-квадрат при alpha = 0.05
    crit_table = {
        1: 3.8415,
        3: 7.8147,
        7: 14.067,
        15: 24.9958,  # block_size = 4 (df = 15)
        31: 44.9853,
        63: 82.5287,
        255: 293.2478  # block_size = 8 (df = 255)
    }
    df = alphabet_size - 1
    # Аппроксимация Вильсона-Хилферти при отсутствии точного значения
    crit_val = crit_table.get(df, df * (1 - 2.0 / (9 * df) + 1.64485 * math.sqrt(2.0 / (9 * df))) ** 3)

    return {
        "block_size": block_size,
        "alphabet_size": alphabet_size,
        "df": df,
        "num_blocks": num_blocks,
        "chi2_stat": chi2_stat,
        "critical_val": crit_val,
        "is_uniform": chi2_stat <= crit_val,
        "counts": counts,
        "expected_per_symbol": expected
    }


def autocorrelation(bits: List[int], max_lag: int = 10) -> List[float]:
    """
    Выборочная нормированная автокорреляционная функция R(d) для задержек d = 1..max_lag.
    Преобразует биты {0, 1} в полярную форму {-1, +1} согласно теории связи и криптографии.
    """
    n = len(bits)
    if n <= max_lag:
        return [0.0] * max_lag

    # Полярное отображение: 0 -> -1, 1 -> +1
    polar = [1.0 if b == 1 else -1.0 for b in bits]
    mean = sum(polar) / n
    var = sum((x - mean) ** 2 for x in polar)

    if var == 0:
        return [0.0] * max_lag

    corrs = []
    for lag in range(1, max_lag + 1):
        cov = sum((polar[t] - mean) * (polar[t + lag] - mean) for t in range(n - lag))
        corrs.append(cov / var)

    return corrs

