"""
Часть 2 (методичка: ЛР №5). Итеративные (многомерные) коды.

Информационное слово X_k длиной k = k1 * k2 * z записывается в трёхмерный массив
из z плоскостей (матриц) размером k1 строк x k2 столбцов; в двумерном случае
z = 1. Нумерация бит - построчно, плоскость за плоскостью (x1..x16 - первая
плоскость, x17..x32 - вторая и т.д., рис. 5.4 методички):

    позиция t = p * k1 * k2 + i * k2 + j      (p - плоскость, i - строка, j - столбец)

Группы паритетов (направления проверок на чётность):
  1. горизонтальные X_h - по каждой строке каждой плоскости (z * k1 проверок);
  2. вертикальные   X_v - по каждому столбцу каждой плоскости (z * k2 проверок);
  3. первые диагональные - по диагоналям i + j = const;
  4. вторые диагональные - по диагоналям j - i = const;
  5. z-паритеты - по "столбцам" вдоль оси Z, т.е. для каждой пары (i, j)
     сумма соответствующих бит всех z плоскостей (k1 * k2 проверок).

Диагонали бывают двух видов:
  * "full"     - все k1 + k2 - 1 диагоналей плоскости (рис. 5.3, двумерный случай);
  * "combined" - объединённые диагонали (рис. 5.4, трёхмерный случай): диагонали
    с одинаковым остатком (i + j) mod m, соответственно (j - i) mod m, где
    m = max(k1, k2), объединяются в одну проверку - всего m проверок на плоскость.
По умолчанию: z = 1 -> "full", z > 1 -> "combined".

Проверки, число которых вычисляется по выбранному числу групп (2, 3, 4 или 5),
образуют проверочные символы X_r; кодовое слово X_n = (X_k, X_r).
"""
from __future__ import annotations

from dataclasses import dataclass

from .linear import LinearCode

GROUP_NAMES = {
    1: "горизонтальные",
    2: "вертикальные",
    3: "диагональные 1 (i+j)",
    4: "диагональные 2 (j-i)",
    5: "z-паритеты",
}


@dataclass(frozen=True)
class IterativeConfig:
    k1: int
    k2: int
    z: int = 1
    groups: int = 2
    diag: str | None = None   # "full" | "combined" | None (выбор по умолчанию)

    def __post_init__(self):
        if self.k1 < 1 or self.k2 < 1 or self.z < 1:
            raise ValueError("k1, k2, z должны быть положительными")
        if not 2 <= self.groups <= 5:
            raise ValueError("число групп паритетов должно быть от 2 до 5")
        if self.groups == 5 and self.z < 2:
            raise ValueError("5-я группа (z-паритеты) требует z >= 2")
        if self.diag not in (None, "full", "combined"):
            raise ValueError("diag: 'full', 'combined' или None")

    @property
    def k(self) -> int:
        return self.k1 * self.k2 * self.z

    @property
    def diag_mode(self) -> str:
        return self.diag or ("full" if self.z == 1 else "combined")

    @property
    def title(self) -> str:
        dims = f"{self.k1}x{self.k2}" + (f"x{self.z}" if self.z > 1 else "")
        return f"{dims}, групп паритетов: {self.groups}"


def cell(cfg: IterativeConfig, t: int) -> tuple[int, int, int]:
    """Позиция бита t -> (плоскость p, строка i, столбец j)."""
    plane, rest = divmod(t, cfg.k1 * cfg.k2)
    i, j = divmod(rest, cfg.k2)
    return plane, i, j


def build_parity_masks(cfg: IterativeConfig) -> tuple[list[int], list[str], list[int]]:
    """
    Возвращает (маски проверок, подписи проверок, номер группы каждой проверки).
    Маска - множество информационных бит, входящих в проверку.
    """
    k1, k2, z = cfg.k1, cfg.k2, cfg.z
    m = max(k1, k2)
    full = cfg.diag_mode == "full"
    cells = [cell(cfg, t) for t in range(cfg.k)]

    masks: list[int] = []
    labels: list[str] = []
    gids: list[int] = []

    def add(group: int, label: str, pred) -> None:
        mask = 0
        for t, (p, i, j) in enumerate(cells):
            if pred(p, i, j):
                mask |= 1 << t
        masks.append(mask)
        labels.append(label)
        gids.append(group)

    # 1. горизонтальные: по каждой строке каждой плоскости
    for p in range(z):
        for i in range(k1):
            add(1, f"H[пл{p},стр{i}]", lambda P, I, J, p=p, i=i: P == p and I == i)
    # 2. вертикальные: по каждому столбцу каждой плоскости
    for p in range(z):
        for j in range(k2):
            add(2, f"V[пл{p},стлб{j}]", lambda P, I, J, p=p, j=j: P == p and J == j)
    # 3. первые диагонали (i + j)
    if cfg.groups >= 3:
        classes = range(k1 + k2 - 1) if full else range(m)
        for p in range(z):
            for c in classes:
                if full:
                    add(3, f"D1[пл{p},{c}]", lambda P, I, J, p=p, c=c: P == p and I + J == c)
                else:
                    add(3, f"D1[пл{p},{c}]", lambda P, I, J, p=p, c=c: P == p and (I + J) % m == c)
    # 4. вторые диагонали (j - i)
    if cfg.groups >= 4:
        classes = range(-(k1 - 1), k2) if full else range(m)
        for p in range(z):
            for c in classes:
                if full:
                    add(4, f"D2[пл{p},{c}]", lambda P, I, J, p=p, c=c: P == p and J - I == c)
                else:
                    add(4, f"D2[пл{p},{c}]", lambda P, I, J, p=p, c=c: P == p and (J - I) % m == c)
    # 5. z-паритеты: для каждой пары (i, j) - сумма по всем плоскостям
    if cfg.groups >= 5:
        for i in range(k1):
            for j in range(k2):
                add(5, f"Z[{i},{j}]", lambda P, I, J, i=i, j=j: I == i and J == j)
    return masks, labels, gids


class IterativeCode(LinearCode):
    """Итеративный код с заданным числом групп паритетов."""

    def __init__(self, cfg: IterativeConfig):
        self.cfg = cfg
        masks, labels, gids = build_parity_masks(cfg)
        self.group_ids = gids
        super().__init__(cfg.k, masks, labels)

    @property
    def rate(self) -> float:
        """Скорость передачи k / (k + r)."""
        return self.k / self.n

    @property
    def redundancy(self) -> float:
        return self.r / self.n

    def group_sizes(self) -> dict[int, int]:
        """Сколько проверочных символов приходится на каждую группу."""
        sizes: dict[int, int] = {}
        for g in self.group_ids:
            sizes[g] = sizes.get(g, 0) + 1
        return sizes

    def failed_checks(self, syndrome: int) -> list[str]:
        """Подписи проверок, не выполненных у принятого слова (ненулевые разряды синдрома)."""
        return [self.labels[i] for i in range(self.r) if (syndrome >> i) & 1]

    def position_name(self, pos: int) -> str:
        """Человекочитаемое имя позиции: ячейка массива либо проверочный символ."""
        if pos < self.k:
            p, i, j = cell(self.cfg, pos)
            return f"x{pos + 1}=[пл{p},стр{i},стлб{j}]"
        return f"проверка {self.labels[pos - self.k]}"

    def render(self, word: int) -> str:
        """Информационная часть слова в виде плоскостей (для вывода на экран)."""
        cfg = self.cfg
        out = []
        for p in range(cfg.z):
            if cfg.z > 1:
                out.append(f"плоскость {p}:")
            for i in range(cfg.k1):
                row = "".join(str((word >> (p * cfg.k1 * cfg.k2 + i * cfg.k2 + j)) & 1) for j in range(cfg.k2))
                out.append("  " + " ".join(row))
        return "\n".join(out)


# Конфигурации варианта 1 (табл. 5.2 методички): k = 16
VARIANT1_CONFIGS: list[tuple[int, int, int, tuple[int, ...]]] = [
    # (k1, k2, z, допустимые числа групп паритетов)
    (4, 4, 1, (2, 3)),
    (8, 2, 1, (2, 3)),
    (4, 2, 2, (2, 3, 4, 5)),
    (2, 4, 2, (2, 3, 4, 5)),
]
