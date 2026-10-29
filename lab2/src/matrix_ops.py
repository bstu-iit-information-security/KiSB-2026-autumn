# matrix_ops.py
"""
Операции с 2D- и 3D-матрицами для итеративного кода.
Вариант 3: k = 24, 2D: 4x6, 3D: 3x4x2.
"""


def bits_to_matrix_2d(bits, k1, k2):
    """
    Заполнить 2D-матрицу k1 x k2 построчно из списка бит.
    bits: список длины k1*k2.
    Возвращает список списков (k1 строк по k2 элементов).
    """
    assert len(bits) == k1 * k2, \
        f"Ожидалось {k1 * k2} бит, получено {len(bits)}"
    return [[bits[i * k2 + j] for j in range(k2)] for i in range(k1)]


def matrix_2d_to_bits(m):
    """Преобразовать 2D-матрицу обратно в список бит (построчно)."""
    return [m[i][j] for i in range(len(m)) for j in range(len(m[0]))]


def bits_to_matrix_3d(bits, a, b, c):
    """
    Заполнить 3D-матрицу: c плоскостей размера a x b.
    Биты распределяются слой за слоем (сначала вся плоскость 0,
    затем плоскость 1 и т.д.).
    Возвращает список из c матриц a x b.
    """
    assert len(bits) == a * b * c, \
        f"Ожидалось {a * b * c} бит, получено {len(bits)}"
    planes = []
    idx = 0
    for _ in range(c):
        plane = [[bits[idx + i * b + j] for j in range(b)] for i in range(a)]
        planes.append(plane)
        idx += a * b
    return planes


def matrix_3d_to_bits(planes):
    """Преобразовать 3D-матрицу обратно в список бит (слой за слоем)."""
    return [planes[p][i][j]
            for p in range(len(planes))
            for i in range(len(planes[p]))
            for j in range(len(planes[p][0]))]


def make_identity(n):
    """Единичная матрица n x n."""
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]


def flatten(nested):
    """Развернуть вложенный список (список списков) в плоский."""
    if nested and isinstance(nested[0], list):
        return [x for row in nested for x in row]
    return list(nested)


def print_matrix_2d(m, title=""):
    """Красивый вывод 2D-матрицы (для отладки)."""
    if title:
        print(title)
    for row in m:
        print("  " + " ".join(map(str, row)))


def print_matrix_3d(planes, title=""):
    """Красивый вывод 3D-матрицы (для отладки)."""
    if title:
        print(title)
    for p, plane in enumerate(planes):
        print(f"  Плоскость z={p}:")
        for row in plane:
            print("    " + " ".join(map(str, row)))


# ---------- Самопроверка при запуске файла напрямую ----------
if __name__ == "__main__":
    # --- Тест 1: 2D, 4x6 ---
    bits = list(range(24))  # 0..23 — чтобы видеть, куда что попадает
    m = bits_to_matrix_2d(bits, 4, 6)
    print("2D (4x6):")
    print_matrix_2d(m)
    back = matrix_2d_to_bits(m)
    assert back == bits, "2D: обратное преобразование сломано"
    print("2D обратно:", back)

    # --- Тест 2: 3D, 3x4x2 = 24 ---
    planes = bits_to_matrix_3d(bits, 3, 4, 2)
    print("\n3D (3x4x2):")
    print_matrix_3d(planes)
    back3 = matrix_3d_to_bits(planes)
    assert back3 == bits, "3D: обратное преобразование сломано"
    print("3D обратно:", back3)

    # --- Тест 3: единичная матрица ---
    I = make_identity(3)
    print("\nЕдиничная 3x3:")
    print_matrix_2d(I)

    # --- Тест 4: flatten ---
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]
    assert flatten([1, 2, 3]) == [1, 2, 3]
    print("\nflatten — OK")

    print("\nВсе тесты matrix_ops пройдены.")