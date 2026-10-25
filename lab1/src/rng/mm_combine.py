"""
Комбинирование алгоритмов генерации методом Макларена-Марсальи (§4.8).

Вариант 1: N = 10 (алфавит "основного" генератора G1),
           K = 5  (алфавит "селектора" G2 и размер T-таблицы).

Алгоритм:
  1. T-таблица (K ячеек) заполняется первыми K значениями последовательности {x_i} от G1.
  2. На шаге k:  s <- y_k (очередное значение G2, индекс в T);
                 z_k <- T(s);
                 T(s) <- x_{K+k} (следующее ещё не использованное значение G1).
"""
from __future__ import annotations

from .lcg import LCG


class MaclarenMarsaglia:
    def __init__(self, g1: LCG, g2: LCG, K: int):
        if g2.N != K:
            raise ValueError(
                f"Алфавит генератора-селектора G2 (N={g2.N}) должен совпадать с K={K}"
            )
        self.g1 = g1
        self.g2 = g2
        self.K = K
        self._table: list[int] | None = None

    def reset(self) -> None:
        """Сбросить оба под-генератора и заново заполнить T-таблицу."""
        self.g1.reset()
        self.g2.reset()
        self._table = [self.g1.next() for _ in range(self.K)]

    def next(self) -> int:
        if self._table is None:
            self.reset()
        s = self.g2.next() % self.K
        z = self._table[s]
        self._table[s] = self.g1.next()
        return z

    def sequence(self, length: int) -> list[int]:
        self.reset()
        return [self.next() for _ in range(length)]

    def detect_period(self, max_len: int | None = None) -> tuple[int | None, int | None]:
        """
        Определить период комбинированного генератора по полному внутреннему
        состоянию (state(G1), state(G2), T-таблица) - в отличие от периода
        по значениям выхода, это даёт истинный период автомата.
        """
        self.reset()
        seen: dict[tuple, int] = {}
        # Точная верхняя граница периода огромна (N^K * N * K), поэтому
        # по умолчанию используем практичный лимит перебора; для точных
        # оценок вызывающий код может передать max_len явно.
        limit = max_len or 20000
        t = 0
        while t < limit:
            state = (self.g1.state, self.g2.state, tuple(self._table))
            if state in seen:
                tau = seen[state]
                return t - tau, tau
            seen[state] = t
            self.next()
            t += 1
        return None, None
