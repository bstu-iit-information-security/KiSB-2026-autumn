"""
Использование генератора Этапа 1 в качестве источника СИДА для практического
генератора битов на Этапе 2.

Почему не напрямую: генератор варианта 1 (N=10, K=5) удовлетворяет
достаточному условию максимального периода (§4.1, свойство 4), но сам
период (T=10 для G1, T=5 для G2) на порядки меньше, чем нужно для различимых
p-битных кандидатов уже при p>=16-20 (см. tests/test_candidate.py,
test_variant1_generator_too_short_for_large_candidates - там же показано,
что "лобовое" масштабирование параметров LCG способно давать скрытую
структурную корреляцию между генератором-селектором и генератором-значений).

Методичка явно допускает на Этапе 2 использовать "базовые механизмы
генерации" Этапа 1, а не буквально его числовой поток - поэтому здесь он
используется как источник сида для random.Random (Mersenne Twister),
который и служит источником бит для построения p-битных кандидатов.
"""
from __future__ import annotations

import random

from .mm_combine import MaclarenMarsaglia


def seed_from_stage1(gen: MaclarenMarsaglia, digits: int = 64) -> int:
    """Извлечь `digits` десятичных цифр из генератора Этапа 1 и собрать из них целое число-сид."""
    gen.reset()
    values = gen.sequence(digits)
    return int("".join(str(v) for v in values))


def build_stage2_rng(gen: MaclarenMarsaglia, digits: int = 64) -> random.Random:
    """Вернуть random.Random, засеянный значением, извлечённым из генератора Этапа 1."""
    seed = seed_from_stage1(gen, digits)
    return random.Random(seed)
