"""
Модуль комбинирования LFSR методом псевдослучайного прореживания (Shrinking Generator).

Теория (раздел 4.9.1 методических указаний):
  - LFSR G1 порождает элементарную двоичную последовательность {a_t}
  - LFSR G2 порождает двоичную селектирующую последовательность {s_t}
  - Выходная последовательность {x_k} включает те биты a_t, для которых s_t = 1;
    если s_t = 0, бит a_t игнорируется (прореживается).
  - Если deg(G1) = n, deg(G2) = m, многочлены примитивны и периоды (2^n - 1) и (2^m - 1)
    взаимно просты, то период выходной последовательности:
      T = (2^n - 1) * 2^(m - 1).
"""

from typing import List, Tuple, Dict, Any, Optional
from .lfsr import LFSR


class ShrinkingGenerator:
    """
    Генератор на основе псевдослучайного прореживания (SG-генератор).
    """

    # Варианты порождающих многочленов 7-й степени по Заданию Варианта 2:
    POLYNOMIAL_PRESETS: Dict[str, Dict[str, Any]] = {
        "f1": {
            "name": "f1(x) = x^7 + x^3 + x^2 + x + 1",
            "taps": [7, 3, 2, 1],
            "degree": 7,
            "is_primitive": True,
            "period": 127
        },
        "f2": {
            "name": "f2(x) = x^7 + x + 1",
            "taps": [7, 1],
            "degree": 7,
            "is_primitive": True,
            "period": 127
        },
        "f3": {
            "name": "f3(x) = x^7 + x^3 + 1",
            "taps": [7, 3],
            "degree": 7,
            "is_primitive": True,
            "period": 127
        },
        "degenerate": {
            "name": "f_deg(x) = x^7 + x^6 + x^2 + 1 (приводимый/вырожденный)",
            "taps": [7, 6, 2],
            "degree": 7,
            "is_primitive": False,
            "period": 9
        }
    }

    # Селектор G2 по умолчанию: g(x) = x^9 + x^4 + 1 (Контрольный вопрос 11, вар. 2)
    DEFAULT_G2 = {
        "name": "g(x) = x^9 + x^4 + 1",
        "taps": [9, 4],
        "degree": 9,
        "is_primitive": True,
        "period": 511
    }

    def __init__(
        self,
        g1_preset: str = "f1",
        g1_taps: Optional[List[int]] = None,
        g1_degree: Optional[int] = None,
        g2_taps: Optional[List[int]] = None,
        g2_degree: Optional[int] = None,
        seed_g1: int = 0b1010101,
        seed_g2: int = 0b110011001
    ):
        if g1_taps is None or g1_degree is None:
            preset = self.POLYNOMIAL_PRESETS.get(g1_preset, self.POLYNOMIAL_PRESETS["f1"])
            self.g1_name = preset["name"]
            g1_taps = preset["taps"]
            g1_degree = preset["degree"]
        else:
            self.g1_name = f"Custom (deg={g1_degree})"

        if g2_taps is None or g2_degree is None:
            self.g2_name = self.DEFAULT_G2["name"]
            g2_taps = self.DEFAULT_G2["taps"]
            g2_degree = self.DEFAULT_G2["degree"]
        else:
            self.g2_name = f"Custom G2 (deg={g2_degree})"

        self.g1 = LFSR(g1_taps, g1_degree, seed_g1)
        self.g2 = LFSR(g2_taps, g2_degree, seed_g2)

        self.total_clock_cycles = 0
        self.output_bits_count = 0
        self.discarded_bits_count = 0

    def reset(self, seed_g1: Optional[int] = None, seed_g2: Optional[int] = None) -> None:
        """Сброс состояния генератора."""
        self.g1.reset(seed_g1)
        self.g2.reset(seed_g2)
        self.total_clock_cycles = 0
        self.output_bits_count = 0
        self.discarded_bits_count = 0

    def next_bit(self) -> int:
        """
        Генерация одного выходного бита методом псевдослучайного прореживания.
        Тактирует G1 и G2 до тех пор, пока селектор G2 не выдаст 1.
        """
        while True:
            a_bit = self.g1.next_bit()
            s_bit = self.g2.next_bit()
            self.total_clock_cycles += 1

            if s_bit == 1:
                self.output_bits_count += 1
                return a_bit
            else:
                self.discarded_bits_count += 1

    def generate_bits(self, count: int) -> List[int]:
        """Генерация списка из count бит."""
        return [self.next_bit() for _ in range(count)]

    def generate_integer(self, bit_length: int) -> int:
        """
        Сборка целого числа заданной битовой длины из потока псевдослучайных бит.
        """
        val = 0
        for _ in range(bit_length):
            val = (val << 1) | self.next_bit()
        return val

    def theoretical_period(self) -> int:
        """
        Теоретический период SG-генератора:
          T = (2^n - 1) * 2^(m - 1)
        """
        n = self.g1.degree
        m = self.g2.degree
        return ( (1 << n) - 1 ) * (1 << (m - 1))

    def measure_full_cycle(self) -> Tuple[int, int]:
        """
        Полный цикл состояния (G1, G2).
        Возвращает (всего_тактов_LFSR, сгенерировано_выходных_бит).
        """
        init_state = (self.g1.state, self.g2.state)
        cycles = 0
        out_bits = 0
        while True:
            a = self.g1.next_bit()
            s = self.g2.next_bit()
            cycles += 1
            if s == 1:
                out_bits += 1
            if (self.g1.state, self.g2.state) == init_state:
                break
        return cycles, out_bits

