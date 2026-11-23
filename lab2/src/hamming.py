"""
Часть 1 (методичка: ЛР №4). Код Хемминга с минимальным кодовым расстоянием 3 или 4.

Построение проверочной матрицы H = [P' | I] (формула (4.4)):
  * число проверочных символов r - наименьшее целое, для которого 2^r >= k + r + 1
    (то есть 2^r >= n + 1: синдром должен различать n позиций ошибки и случай
    "ошибки нет");
  * столбцы подматрицы P' (размер r x k) - r-разрядные двоичные записи натуральных
    чисел, вес которых не меньше 2 (вес 1 занимает единичная подматрица I).
    Числа берутся сначала с весом 2 (3, 5, 6, 9, ...), затем с весом 3 и т.д.,
    в порядке возрастания - ровно как в алгоритме методички (листинг 4.2).
    Старший разряд числа - верхняя строка столбца.

Код с d_min = 4 (формула (4.8)): добавляется общая проверка на чётность.
Матрица приводится к каноническому виду: в добавленной строке на месте столбца
j стоит (1 + вес столбца j) mod 2, т.е. дополнительный проверочный символ равен
сумме по модулю 2 ВСЕХ символов слова (информационных и проверочных).
Такой код исправляет одиночные ошибки и обнаруживает все двойные.
"""
from __future__ import annotations

from .bits import weight
from .linear import LinearCode


def min_check_bits(k: int) -> int:
    """Наименьшее r, при котором 2^r >= k + r + 1 (код Хемминга с d_min = 3)."""
    if k < 1:
        raise ValueError("k должно быть положительным")
    r = 1
    while (1 << r) < k + r + 1:
        r += 1
    return r


def p_columns(k: int, r: int) -> list[int]:
    """Столбцы подматрицы P' как r-разрядные числа (старший разряд - верхняя строка)."""
    candidates = sorted(
        (num for num in range(3, 1 << r) if weight(num) >= 2),
        key=lambda num: (weight(num), num),
    )
    if len(candidates) < k:
        raise ValueError(f"при r={r} нельзя построить {k} различных столбцов веса >= 2")
    return candidates[:k]


class HammingCode(LinearCode):
    """Код Хемминга (n, k) с d_min = 3 либо d_min = 4 (расширенный)."""

    def __init__(self, k: int, dmin: int = 3):
        if dmin not in (3, 4):
            raise ValueError("d_min должно быть равно 3 или 4")
        self.dmin = dmin
        self.r_hamming = min_check_bits(k)
        r = self.r_hamming
        cols = p_columns(k, r)
        masks = []
        for i in range(r):
            shift = r - 1 - i  # строка i - разряд (r-1-i) числа-столбца
            m = 0
            for j, num in enumerate(cols):
                m |= ((num >> shift) & 1) << j
            masks.append(m)
        labels = [f"p{i + 1}" for i in range(r)]
        if dmin == 4:
            extra = 0
            for j, num in enumerate(cols):
                extra |= ((1 + weight(num)) & 1) << j
            masks.append(extra)
            labels.append("p0 (общая чётность)")
        super().__init__(k, masks, labels)

    @property
    def rate(self) -> float:
        """Скорость кода R = k / n."""
        return self.k / self.n

    @property
    def redundancy(self) -> float:
        """Относительная избыточность r / n."""
        return self.r / self.n

    def decode_word(self, word: int):
        """Классическое декодирование: исправляется одна ошибка."""
        return self.decode(word, max_weight=1)


def format_matrix(rows: list[list[int]], k: int | None = None) -> str:
    """Матрица в виде текста; если задано k - вертикальная черта между P' и I."""
    lines = []
    for row in rows:
        cells = [str(b) for b in row]
        if k is not None:
            cells.insert(k, "|")
        lines.append(" ".join(cells))
    return "\n".join(lines)
