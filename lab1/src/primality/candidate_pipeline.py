"""
Модуль конвейера генерации больших простых чисел по стандартной схеме (Этап 2).

Алгоритм:
  1. Генерация p-битового кандидата с использованием ПСП из Этапа 1 (SG-генератор);
  2. Установка старшего (MSB) и младшего (LSB) битов в 1 (гарантия разрядности и нечетности);
  3. Предварительное просеивание ситом малых простых чисел (<= 256);
  4. Проверка целевым вероятностным тестом Леманна (k раундов);
  5. Сбор метрик эффективности: доля отсеянных кандидатов, время работы, количество шагов.
"""

import time
from typing import Tuple, Dict, Any, Optional
from .trial_division import trial_division_filter
from .lehmann import lehmann_test
from ..generators.shrinking import ShrinkingGenerator


def random_candidate_from_sg(bits: int, sg_generator: ShrinkingGenerator) -> int:
    """
    Генерация p-битового нечетного кандидата из потока бит SG-генератора.
    Устанавливает старший (MSB) и младший (LSB) биты в 1.
    """
    if bits < 2:
        raise ValueError("Разрядность должна быть >= 2 бит")

    val = 0
    for _ in range(bits):
        val = (val << 1) | sg_generator.next_bit()

    # Гарантия разрядности p бит и нечетности
    val |= (1 << (bits - 1))
    val |= 1
    return val


def generate_prime_pipeline(
    bits: int = 64,
    k_lehmann: int = 15,
    max_attempts: int = 50_000,
    sg_generator: Optional[ShrinkingGenerator] = None
) -> Tuple[Optional[int], Dict[str, Any]]:
    """
    Стандартная схема генерации простого числа.
    Возвращает (найденное_простое, статистика).
    """
    if sg_generator is None:
        sg_generator = ShrinkingGenerator(g1_preset="f1")

    stats = {
        "bits": bits,
        "k_lehmann": k_lehmann,
        "checked": 0,
        "sieve_filtered": 0,
        "lehmann_checked": 0,
        "lehmann_rejected": 0,
        "elapsed": 0.0,
        "sieve_filter_pct": 0.0
    }

    start_time = time.perf_counter()

    for _ in range(max_attempts):
        cand = random_candidate_from_sg(bits, sg_generator)
        stats["checked"] += 1

        # 1. Предварительное сито
        passed_sieve, _ = trial_division_filter(cand)
        if not passed_sieve:
            stats["sieve_filtered"] += 1
            continue

        # 2. Целевой тест Леманна
        stats["lehmann_checked"] += 1
        if lehmann_test(cand, k=k_lehmann):
            stats["elapsed"] = time.perf_counter() - start_time
            if stats["checked"] > 0:
                stats["sieve_filter_pct"] = (stats["sieve_filtered"] / stats["checked"]) * 100.0
            return cand, stats
        else:
            stats["lehmann_rejected"] += 1

    stats["elapsed"] = time.perf_counter() - start_time
    if stats["checked"] > 0:
        stats["sieve_filter_pct"] = (stats["sieve_filtered"] / stats["checked"]) * 100.0
    return None, stats

