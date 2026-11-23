"""
Систематический линейный двоичный (n, k)-код, заданный проверками на чётность.

Кодовое слово X_n = (X_k, X_r): сначала k информационных символов, затем
r проверочных. Каждый проверочный символ - сумма по модулю 2 некоторого
подмножества информационных символов; подмножество задаётся битовой маской
(parity_masks[i], бит j маски = 1, если j-й информационный символ входит
в i-ю проверку). Это и есть подматрица P' проверочной матрицы H = [P' | I].

Синдром принятого слова Y_n:  S = Y_r' xor Y_r,  где Y_r' - проверочные
символы, вновь вычисленные по принятым информационным Y_k (листинг 4.4
методички). Эквивалентно S = H * Y_n^T: ненулевой синдром всегда равен сумме
(по модулю 2) тех столбцов матрицы H, номера которых совпадают с номерами
ошибочных символов.

Декодирование: по синдрому ищется вектор ошибки E_n минимального веса
(лидер смежного класса). Если лидер единственный - ошибка исправляется
(Y_n' = Y_n + E_n, формула (4.7)); если лидеров несколько либо синдром
не найден в таблице - фиксируется обнаруженная, но неисправимая ошибка.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .bits import parity


@dataclass(frozen=True)
class DecodeResult:
    status: str                      # "ok" | "corrected" | "detected"
    syndrome: int                    # r-битный синдром (бит i - результат i-й проверки)
    error_positions: tuple[int, ...]  # найденные позиции ошибок (для "corrected")
    word: int                        # слово после исправления (или принятое, если не исправлено)


class LinearCode:
    def __init__(self, k: int, parity_masks: list[int], labels: list[str] | None = None):
        self.k = k
        self.masks = list(parity_masks)
        self.r = len(self.masks)
        self.n = k + self.r
        self.labels = labels or [f"p{i}" for i in range(self.r)]
        self._info_mask = (1 << k) - 1
        # синдром одиночной ошибки в позиции p = столбец p проверочной матрицы H
        self.columns: list[int] = []
        for j in range(k):
            col = 0
            for i, m in enumerate(self.masks):
                if (m >> j) & 1:
                    col |= 1 << i
            self.columns.append(col)
        for i in range(self.r):
            self.columns.append(1 << i)
        self._tables: dict[int, dict[int, list]] = {}

    # ---------------------------------------------------------------- кодирование
    def checks(self, info: int) -> int:
        """Проверочные символы X_r для информационного слова X_k (r-битное число)."""
        x = 0
        for i, m in enumerate(self.masks):
            x |= parity(info & m) << i
        return x

    def encode(self, info: int) -> int:
        """Кодовое слово X_n = (X_k, X_r) как n-битное число."""
        info &= self._info_mask
        return info | (self.checks(info) << self.k)

    def split(self, word: int) -> tuple[int, int]:
        """Слово -> (информационная часть, проверочная часть)."""
        return word & self._info_mask, word >> self.k

    # ------------------------------------------------------------------- синдром
    def syndrome(self, word: int) -> int:
        """Синдром S = Y_r xor Y_r' (0 - все проверки выполнены)."""
        info, got = self.split(word)
        return got ^ self.checks(info)

    # ------------------------------------------------------------ таблица лидеров
    def _table(self, max_weight: int) -> dict[int, list]:
        """syndrome -> [вес лидера, позиции, неоднозначность] для ошибок веса 1..max_weight."""
        if max_weight in self._tables:
            return self._tables[max_weight]
        table: dict[int, list] = {}
        cols = self.columns
        for w in range(1, max_weight + 1):
            for combo in combinations(range(self.n), w):
                s = 0
                for p in combo:
                    s ^= cols[p]
                if s == 0:
                    continue  # кодовое слово: такая ошибка не обнаруживается
                entry = table.get(s)
                if entry is None:
                    table[s] = [w, combo, False]
                elif entry[0] == w:
                    entry[2] = True  # два разных лидера одного веса
        self._tables[max_weight] = table
        return table

    def decode(self, word: int, max_weight: int = 1) -> DecodeResult:
        """
        Синдромное декодирование. max_weight - наибольший вес ошибки, для которой
        строится таблица лидеров (1 - классический код Хемминга).
        """
        s = self.syndrome(word)
        if s == 0:
            return DecodeResult("ok", 0, (), word)
        entry = self._table(max_weight).get(s)
        if entry is None or entry[2]:
            return DecodeResult("detected", s, (), word)
        positions = entry[1]
        fixed = word
        for p in positions:
            fixed ^= 1 << p
        return DecodeResult("corrected", s, positions, fixed)

    # ------------------------------------------------------------------ свойства
    def h_matrix(self) -> list[list[int]]:
        """Проверочная матрица H = [P' | I] (r строк, n столбцов)."""
        rows = []
        for i, m in enumerate(self.masks):
            rows.append([(m >> j) & 1 for j in range(self.k)] + [1 if c == i else 0 for c in range(self.r)])
        return rows

    def min_distance(self, max_k: int = 24) -> int | None:
        """
        Минимальное кодовое расстояние d_min = минимальный вес ненулевого кодового
        слова (код линейный). Полный перебор 2^k сообщений, поэтому k <= max_k.
        """
        if self.k > max_k:
            return None
        import numpy as np

        msgs = np.arange(1, 1 << self.k, dtype=np.uint64)
        total = np.zeros(msgs.shape, dtype=np.uint16)
        total += np.bitwise_count(msgs).astype(np.uint16)
        for m in self.masks:
            total += np.bitwise_count(msgs & np.uint64(m)).astype(np.uint16) & 1
        return int(total.min())
