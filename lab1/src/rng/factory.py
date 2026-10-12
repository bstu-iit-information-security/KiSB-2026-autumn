"""
Фабрики генераторов для Этапов 1 и 2 ЛР №1 (Вариант 1).
"""
from __future__ import annotations

from .lcg import LCG
from .mm_combine import MaclarenMarsaglia


def build_variant1_generator() -> MaclarenMarsaglia:
    """
    Точно по таблице варианта 1: N=10, K=5.
    Используется для статистического анализа Этапа 1 (частоты, хи-квадрат,
    исследование периода при разных параметрах генератора).

    Достаточное условие максимального периода (§4.1, свойство 4) для N с
    несколькими простыми делителями вырождается в a ≡ 1 (mod N) - генератор
    становится аддитивным (генератором Вейля). Получаемый период (T=10 для
    G1, T=5 для G2) достаточен для статистических тестов, но НЕ достаточен
    для генерации криптографически различимых p-битных кандидатов при
    p >= ~16-20 бит - см. src/rng/seeding.py и
    tests/test_candidate.py::test_variant1_generator_too_short_for_large_candidates.
    """
    g1 = LCG(a=1, c=3, N=10, x0=0)
    g2 = LCG(a=1, c=2, N=5, x0=0)
    assert g1.satisfies_max_period_condition()
    assert g2.satisfies_max_period_condition()
    return MaclarenMarsaglia(g1, g2, K=5)
