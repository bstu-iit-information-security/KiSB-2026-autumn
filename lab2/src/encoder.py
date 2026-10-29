# encoder.py
"""
Кодирование: Xk -> Xn (добавление избыточных символов).
Вариант 3: k = 24, 2D: 4x6, 3D: 3x4x2.
"""

from matrix_ops import bits_to_matrix_2d, bits_to_matrix_3d, flatten
from parity import (parity_2groups_2d, parity_3groups_2d,
                    parity_4groups_3d, parity_5groups_3d)


def encode_2groups_2d(bits, k1, k2):
    """
    2 группы паритетов (2D).
    Xn = Xk + Xh + Xv + [Xhv]
    Возвращает (Xn, (Xh, Xv, Xhv)).
    """
    m = bits_to_matrix_2d(bits, k1, k2)
    Xh, Xv, Xhv = parity_2groups_2d(m)
    Xn = list(bits) + Xh + Xv + [Xhv]
    return Xn, (Xh, Xv, Xhv)


def encode_3groups_2d(bits, k1, k2):
    """
    3 группы паритетов (2D).
    Xn = Xk + Xh + Xv + [Xhv] + Xd
    Возвращает (Xn, (Xh, Xv, Xhv, Xd)).
    """
    m = bits_to_matrix_2d(bits, k1, k2)
    Xh, Xv, Xhv, Xd = parity_3groups_2d(m)
    Xn = list(bits) + Xh + Xv + [Xhv] + Xd
    return Xn, (Xh, Xv, Xhv, Xd)


def encode_4groups_3d(bits, a, b, c):
    """
    4 группы паритетов (3D).
    Xn = Xk + flat(Xh) + flat(Xv) + flat(Xz) + [Xhv]
    Возвращает (Xn, (Xh, Xv, Xz, Xhv)).
    """
    planes = bits_to_matrix_3d(bits, a, b, c)
    Xh, Xv, Xz, Xhv = parity_4groups_3d(planes)
    Xn = list(bits) + flatten(Xh) + flatten(Xv) + flatten(Xz) + [Xhv]
    return Xn, (Xh, Xv, Xz, Xhv)


def encode_5groups_3d(bits, a, b, c):
    """
    5 групп паритетов (3D).
    Xn = Xk + flat(Xh) + flat(Xv) + flat(Xz) + [Xhv] + Xd
    Возвращает (Xn, (Xh, Xv, Xz, Xhv, Xd)).
    """
    planes = bits_to_matrix_3d(bits, a, b, c)
    Xh, Xv, Xz, Xhv, Xd = parity_5groups_3d(planes)
    Xn = list(bits) + flatten(Xh) + flatten(Xv) + flatten(Xz) + [Xhv] + Xd
    return Xn, (Xh, Xv, Xz, Xhv, Xd)


# ---------- Самопроверка ----------
if __name__ == "__main__":
    bits = [0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0,
            0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1]

    print("Исходное Xk:", "".join(map(str, bits)))

    # 2 группы
    Xn2, p2 = encode_2groups_2d(bits, 4, 6)
    print(f"\n[2 группы] n={len(Xn2)}, r={len(Xn2) - len(bits)}")
    print("Xn:", "".join(map(str, Xn2)))

    # 3 группы
    Xn3, p3 = encode_3groups_2d(bits, 4, 6)
    print(f"\n[3 группы] n={len(Xn3)}, r={len(Xn3) - len(bits)}")
    print("Xn:", "".join(map(str, Xn3)))

    # 4 группы
    Xn4, p4 = encode_4groups_3d(bits, 3, 4, 2)
    print(f"\n[4 группы] n={len(Xn4)}, r={len(Xn4) - len(bits)}")
    print("Xn:", "".join(map(str, Xn4)))

    # 5 групп
    Xn5, p5 = encode_5groups_3d(bits, 3, 4, 2)
    print(f"\n[5 групп] n={len(Xn5)}, r={len(Xn5) - len(bits)}")
    print("Xn:", "".join(map(str, Xn5)))