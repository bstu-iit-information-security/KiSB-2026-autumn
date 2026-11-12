"""
Модуль реализации регистра сдвига с линейной обратной связью (LFSR).
Поддерживает работу с произвольными обратными связями над GF(2).
"""

from typing import List, Tuple, Optional


class LFSR:
    """
    Регистр сдвига с линейной обратной связью (Linear Feedback Shift Register, LFSR)
    в конфигурации Фибоначчи.

    Закон обратной связи:
      fb = sum_{t in taps} s_{deg - t} mod 2
    Сдвиг вправо, новый бит fb записывается в старший разряд (deg - 1),
    а младший бит (LSB) выдается на выход.
    """

    def __init__(self, taps: List[int], degree: int, seed: int = 1):
        """
        :param taps: Список степеней одночленов обратной связи (например, [7, 3, 2, 1] для x^7 + x^3 + x^2 + x + 1).
        :param degree: Степень характеристического многочлена n (длина регистра).
        :param seed: Начальное состояние (ненулевое целое число).
        """
        self.taps = sorted(taps, reverse=True)
        self.degree = degree
        self.mask = (1 << degree) - 1
        self.initial_seed = seed & self.mask if (seed & self.mask) != 0 else 1
        self.state = self.initial_seed

    def reset(self, seed: Optional[int] = None) -> None:
        """Сброс состояния регистра."""
        if seed is not None:
            self.initial_seed = seed & self.mask if (seed & self.mask) != 0 else 1
        self.state = self.initial_seed

    def next_bit(self) -> int:
        """
        Вычисление одного такта LFSR.
        Возвращает выходной бит (0 или 1).
        """
        out_bit = self.state & 1
        feedback = 0
        for tap in self.taps:
            feedback ^= ((self.state >> (self.degree - tap)) & 1)
        self.state = (self.state >> 1) | (feedback << (self.degree - 1))
        return out_bit

    def generate_bits(self, count: int) -> List[int]:
        """Генерация последовательности из count бит."""
        return [self.next_bit() for _ in range(count)]

    def measure_period(self, max_steps: int = 1_000_000) -> int:
        """
        Экспериментальное измерение периода регистра.
        Возвращает количество тактов до возврата в исходное состояние.
        """
        initial = self.state
        steps = 0
        while steps < max_steps:
            self.next_bit()
            steps += 1
            if self.state == initial:
                return steps
        return -1


def check_primitive_gf2(taps: List[int], degree: int) -> Tuple[bool, int, int]:
    """
    Проверка примитивности многочлена обратной связи над GF(2).
    Возвращает (is_primitive, measured_period, theoretical_max_period).
    """
    max_period = (1 << degree) - 1
    lfsr = LFSR(taps=taps, degree=degree, seed=1)
    period = lfsr.measure_period(max_steps=max_period + 5)
    is_primitive = (period == max_period)
    return is_primitive, period, max_period

