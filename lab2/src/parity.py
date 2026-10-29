# parity.py
"""
Вычисление проверочных битов (паритетов) по 2, 3, 4, 5 направлениям.
Вариант 3: k = 24, 2D: 4x6, 3D: 3x4x2.
"""


def xor_list(lst):
    """Сумма по модулю 2 всех элементов списка."""
    r = 0
    for x in lst:
        r ^= x
    return r


# =====================================================================
#  2 ГРУППЫ ПАРИТЕТОВ (2D): по строкам + по столбцам + паритет паритетов
# =====================================================================
def parity_2groups_2d(m):
    """
    m: 2D-матрица k1 x k2.
    Возвращает (Xh, Xv, Xhv):
      Xh  — список длины k1 (XOR каждой строки),
      Xv  — список длины k2 (XOR каждого столбца),
      Xhv — один бит (XOR всех Xh; равен XOR всех Xv и XOR всех бит матрицы).
    """
    k1, k2 = len(m), len(m[0])
    Xh = [xor_list(m[i]) for i in range(k1)]
    Xv = [xor_list([m[i][j] for i in range(k1)]) for j in range(k2)]
    Xhv = xor_list(Xh)  # == xor_list(Xv) == xor_list всех бит матрицы
    return Xh, Xv, Xhv


# =====================================================================
#  3 ГРУППЫ ПАРИТЕТОВ (2D): Xh + Xv + Xhv + диагонали Xd
# =====================================================================
def parity_3groups_2d(m):
    """
    Диагональные паритеты: индексы s = i + j от 0 до k1+k2-2.
    Для каждого s собираем m[i][j], где i + j = s, и берём XOR.
    Возвращает (Xh, Xv, Xhv, Xd), где Xd — список длины k1+k2-1.
    """
    k1, k2 = len(m), len(m[0])
    Xh, Xv, Xhv = parity_2groups_2d(m)

    Xd = []
    for s in range(k1 + k2 - 1):
        # Собираем элементы диагонали (i + j = s)
        diag = [m[i][s - i] for i in range(k1) if 0 <= s - i < k2]
        Xd.append(xor_list(diag))
    return Xh, Xv, Xhv, Xd


# =====================================================================
#  4 ГРУППЫ ПАРИТЕТОВ (3D): Xh + Xv + Xz + Xhv
# =====================================================================
def parity_4groups_3d(planes):
    """
    planes: список из c матриц a x b.
    Возвращает (Xh, Xv, Xz, Xhv):
      Xh  — [c][a]  : паритеты по строкам в каждой плоскости,
      Xv  — [c][b]  : паритеты по столбцам в каждой плоскости,
      Xz  — [a][b]  : XOR по всем плоскостям для каждой позиции (i,j),
      Xhv — один бит (XOR всех Xh).
    """
    c = len(planes)
    a, b = len(planes[0]), len(planes[0][0])

    Xh = [[xor_list(planes[p][i]) for i in range(a)] for p in range(c)]
    Xv = [[xor_list([planes[p][i][j] for i in range(a)]) for j in range(b)]
          for p in range(c)]
    Xz = [[xor_list([planes[p][i][j] for p in range(c)]) for j in range(b)]
          for i in range(a)]
    Xhv = xor_list([xor_list(row) for row in Xh])

    return Xh, Xv, Xz, Xhv


# =====================================================================
#  5 ГРУПП ПАРИТЕТОВ (3D): Xh + Xv + Xz + Xhv + диагонали Xd
# =====================================================================
def parity_5groups_3d(planes):
    """
    Дополнительно к 4 группам — диагональные паритеты в каждой плоскости
    (главная диагональ i == j, для i от 0 до min(a,b)-1).
    Возвращает (Xh, Xv, Xz, Xhv, Xd), где Xd — список длины c.
    """
    c = len(planes)
    a, b = len(planes[0]), len(planes[0][0])
    Xh, Xv, Xz, Xhv = parity_4groups_3d(planes)

    Xd = []
    for p in range(c):
        diag = [planes[p][i][i] for i in range(min(a, b))]
        Xd.append(xor_list(diag))

    return Xh, Xv, Xz, Xhv, Xd


# ---------- Самопроверка ----------
if __name__ == "__main__":
    import random

    rng = random.Random(0)

    # 2D: матрица 4x6
    m = [[rng.randint(0, 1) for _ in range(6)] for _ in range(4)]
    print("Матрица 4x6:")
    for row in m:
        print("  " + " ".join(map(str, row)))

    Xh, Xv, Xhv = parity_2groups_2d(m)
    print(f"\n2 группы: Xh={Xh}, Xv={Xv}, Xhv={Xhv}")

    # Инвариант: XOR всех Xh == XOR всех Xv == Xhv
    assert xor_list(Xh) == xor_list(Xv) == Xhv
    # Инвариант: XOR всех бит матрицы == Xhv
    assert xor_list([x for row in m for x in row]) == Xhv
    print("  Инварианты 2 групп — OK")

    Xh3, Xv3, Xhv3, Xd3 = parity_3groups_2d(m)
    print(f"\n3 группы: Xd={Xd3}")
    # Инвариант: XOR всех диагональных паритетов == Xhv
    assert xor_list(Xd3) == Xhv3, \
        f"XOR(Xd)={xor_list(Xd3)} != Xhv={Xhv3}"
    print("  Инвариант 3 групп — OK")

    # 3D: 2 плоскости 3x4
    planes = [[[rng.randint(0, 1) for _ in range(4)] for _ in range(3)]
              for _ in range(2)]
    Xh4, Xv4, Xz4, Xhv4 = parity_4groups_3d(planes)
    print(f"\n4 группы (3D): Xhv={Xhv4}, Xz[0][0]={Xz4[0][0]}")
    # Инвариант: XOR всех Xz == XOR всех бит всех плоскостей
    flat_all = [x for plane in planes for row in plane for x in row]
    flat_xz = [x for row in Xz4 for x in row]
    assert xor_list(flat_xz) == xor_list(flat_all)
    print("  Инвариант 4 групп — OK")

    Xh5, Xv5, Xz5, Xhv5, Xd5 = parity_5groups_3d(planes)
    print(f"\n5 групп (3D): Xd={Xd5}")
    # Инвариант: XOR всех диагоналей == XOR всех бит на главных диагоналях
    diag_all = [planes[p][i][i] for p in range(2) for i in range(3)]
    assert xor_list(Xd5) == xor_list(diag_all)
    print("  Инвариант 5 групп — OK")

    print("\nВсе тесты parity пройдены.")