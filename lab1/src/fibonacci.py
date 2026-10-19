"""Генератор Фибоначчи: x_t = x_{t-r} XOR x_{t-s}, t = r, r+1, ...
 
Элемент x_t - двоичный k-вектор (число от 0 до 2^k - 1), алфавит N = 2^k.
Для N = 2 это k = 1 (обычные биты).
 
Внутреннее состояние - одно целое число из r*k бит: в младших k битах лежит
самый старый элемент x_{t-r}, в старших - самый новый x_{t-1}.
"""
from __future__ import annotations
 
from typing import Iterator, List, Optional, Sequence, Tuple, Union
 
Seed = Union[None, int, Sequence[int]]
 
 
class FibonacciGenerator:
    def __init__(self, r: int, s: int, k: int = 1, seed: Seed = None):
        if not (r > s >= 1):
            raise ValueError("Должно быть r > s >= 1")
        if k < 1:
            raise ValueError("k должно быть >= 1")
        self.r, self.s, self.k = r, s, k
        self.N = 1 << k                       # размер алфавита
        self._mask = self.N - 1
        self._shift_s = (r - s) * k           # позиция x_{t-s} в состоянии
        self._shift_new = (r - 1) * k         # куда записывается новый элемент
        self._state = self._pack_seed(seed)
        self._initial_state = self._state
 
    # ------------------------------------------------------------------ seed
    def _pack_seed(self, seed: Seed) -> int:
        total_bits = self.r * self.k
        if seed is None:                      # по умолчанию - все единицы
            return (1 << total_bits) - 1
        if isinstance(seed, int):
            return seed & ((1 << total_bits) - 1)
        if len(seed) != self.r:
            raise ValueError(f"Начальных значений должно быть r = {self.r}")
        state = 0
        for i, v in enumerate(seed):          # seed[0] = x_0 (самый старый)
            if not 0 <= v < self.N:
                raise ValueError(f"Элементы должны лежать в [0, {self.N - 1}]")
            state |= v << (i * self.k)
        return state
 
    def reset(self) -> None:
        self._state = self._initial_state
 
    # ------------------------------------------------------------ генерация
    def next(self) -> int:
        """Следующий элемент последовательности."""
        st = self._state
        new = (st & self._mask) ^ ((st >> self._shift_s) & self._mask)
        self._state = (st >> self.k) | (new << self._shift_new)
        return new
 
    def skip(self, n: int) -> None:
        for _ in range(n):
            self.next()
 
    def sequence(self, length: int) -> List[int]:
        """Последовательность произвольной длины из алфавита {0..N-1}."""
        return [self.next() for _ in range(length)]
 
    def __iter__(self) -> Iterator[int]:
        while True:
            yield self.next()
 
    def getrandbits(self, nbits: int) -> int:
        """Случайное число из nbits бит (интерфейс как у random)."""
        acc, got = 0, 0
        while got < nbits:
            acc = (acc << self.k) | self.next()
            got += self.k
        return acc >> (got - nbits)
 
    def __repr__(self) -> str:
        return f"FibonacciGenerator(r={self.r}, s={self.s}, k={self.k}, N={self.N})"
 
 
# ---------------------------------------------------------------- период
def theoretical_max_period(r: int, k: int = 1) -> int:
    """Максимальный период: 2^r - 1.
 
    Условие: многочлен x^r + x^(r-s) + 1 над GF(2) должен быть примитивным
    (эквивалентно: примитивен x^r + x^s + 1).
    """
    return (1 << r) - 1
 
 
def find_period(r: int, s: int, k: int = 1, seed: Seed = None,
                limit: Optional[int] = None) -> Optional[int]:
    """Точный период (перебором состояний). Отображение состояний обратимо
    (x_{t-r} = x_t XOR x_{t-s}), поэтому последовательность чисто периодична и
    период = число шагов до возврата в начальное состояние."""
    g = FibonacciGenerator(r, s, k, seed)
    init = g._state
    state, mask, sh_s, sh_new = init, g._mask, g._shift_s, g._shift_new
    limit = limit or (1 << (r * k))
    for t in range(1, limit + 1):
        new = (state & mask) ^ ((state >> sh_s) & mask)
        state = (state >> k) | (new << sh_new)
        if state == init:
            return t
    return None
 
 
def search_periods(r: int, k: int = 1, seed: Seed = None) -> List[Tuple[int, Optional[int]]]:
    """Периоды для всех s = 1..r-1 при фиксированном r."""
    return [(s, find_period(r, s, k, seed)) for s in range(1, r)]
 
