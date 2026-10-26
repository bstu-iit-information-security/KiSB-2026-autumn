"""
Эксперименты по оценке корректирующей способности кодов (п. 4-6 практического
задания ЛР №4 и ЛР №5).

Для кодового слова X_n генерируется ошибка кратности i (i позиций, выбранных
случайно среди ВСЕХ n символов слова, включая проверочные) -> слово Y_n.
Декодер возвращает слово Y_n'. Исходы:

  undetected   - синдром нулевой, ошибка не замечена (ошибка сама является кодовым словом);
  corrected    - ошибка обнаружена и найден единственный вектор ошибки;
                   из них exact   - Y_n' == X_n (все ошибки исправлены, N3),
                        miscorrected - Y_n' != X_n (ошибочная "коррекция");
  detected     - ошибка обнаружена, но исправить нельзя (неоднозначность / слишком
                 большая кратность).

По определению методички:
  N1 - число сгенерированных слов с ошибкой кратности i;
  N2 - число случаев, когда кратность ошибки определена правильно
       (декодер нашёл вектор ошибки веса i);
  N3 - число случаев, когда все ошибки исправлены (X_n == Y_n').
Результат - отношения N2/N1 и N3/N1.

Код линейный, поэтому исход зависит только от вектора ошибки, а не от
конкретного сообщения; для наглядности используется фиксированное слово.
"""
from __future__ import annotations

import random
from itertools import combinations
from math import comb

from .linear import LinearCode


def classify(code: LinearCode, word: int, positions: tuple[int, ...], max_weight: int) -> str:
    """Внести ошибку в позиции positions и классифицировать результат декодирования."""
    received = word
    for p in positions:
        received ^= 1 << p
    res = code.decode(received, max_weight)
    if res.status == "ok":
        return "undetected"
    if res.status == "detected":
        return "detected"
    return "exact" if res.word == word else "miscorrected"


def _row(i: int, n1: int, counts: dict[str, int], identified: int) -> dict:
    n3 = counts["exact"]
    return {
        "i": i,
        "N1": n1,
        "N2": identified,
        "N3": n3,
        "N2/N1": identified / n1 if n1 else 0.0,
        "N3/N1": n3 / n1 if n1 else 0.0,
        "exact": counts["exact"],
        "miscorrected": counts["miscorrected"],
        "detected": counts["detected"],
        "undetected": counts["undetected"],
    }


def run_trials(
    code: LinearCode,
    multiplicity: int,
    n_trials: int,
    max_weight: int,
    rng: random.Random,
    info: int = 0,
) -> dict:
    """Случайные ошибки заданной кратности (позиции равновероятны, без повторов)."""
    word = code.encode(info)
    counts = {"exact": 0, "miscorrected": 0, "detected": 0, "undetected": 0}
    identified = 0
    for _ in range(n_trials):
        positions = tuple(sorted(rng.sample(range(code.n), multiplicity)))
        received = word
        for p in positions:
            received ^= 1 << p
        res = code.decode(received, max_weight)
        if res.status == "ok":
            counts["undetected"] += 1
        elif res.status == "detected":
            counts["detected"] += 1
        else:
            if len(res.error_positions) == multiplicity:
                identified += 1
            counts["exact" if res.word == word else "miscorrected"] += 1
    return _row(multiplicity, n_trials, counts, identified)


def run_exhaustive(code: LinearCode, multiplicity: int, max_weight: int, info: int = 0) -> dict:
    """ВСЕ возможные ошибки заданной кратности (C(n, i) вариантов)."""
    word = code.encode(info)
    counts = {"exact": 0, "miscorrected": 0, "detected": 0, "undetected": 0}
    identified = 0
    total = 0
    for positions in combinations(range(code.n), multiplicity):
        total += 1
        received = word
        for p in positions:
            received ^= 1 << p
        res = code.decode(received, max_weight)
        if res.status == "ok":
            counts["undetected"] += 1
        elif res.status == "detected":
            counts["detected"] += 1
        else:
            if len(res.error_positions) == multiplicity:
                identified += 1
            counts["exact" if res.word == word else "miscorrected"] += 1
    assert total == comb(code.n, multiplicity)
    return _row(multiplicity, total, counts, identified)


def error_table(
    code: LinearCode,
    max_multiplicity: int,
    n_trials: int,
    max_weight: int,
    seed: int,
    exhaustive_up_to: int = 2,
) -> list[dict]:
    """
    Таблица по кратностям 1..max_multiplicity: для малых кратностей - полный
    перебор всех ошибок, для больших - n_trials случайных ошибок.
    """
    rng = random.Random(seed)
    rows = []
    for i in range(1, max_multiplicity + 1):
        if i <= exhaustive_up_to:
            rows.append(run_exhaustive(code, i, max_weight) | {"mode": "полный перебор"})
        else:
            rows.append(run_trials(code, i, n_trials, max_weight, rng) | {"mode": "случайные"})
    return rows
