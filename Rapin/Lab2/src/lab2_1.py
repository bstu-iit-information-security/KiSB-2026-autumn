import random
from typing import List, Tuple, Optional


def fact(n: int) -> int:
    """Факториал n."""
    if n <= 1:
        return 1
    return fact(n - 1) * n


def binom(wt: int, r: int) -> int:
    """Бином Ньютона C(r, wt)."""
    if wt < 0 or wt > r:
        return 0
    return fact(r) // (fact(wt) * fact(r - wt))


def int_to_bin_str(num: int, width: int = 0) -> str:
    """Двоичное представление числа."""
    s = bin(num)[2:]
    return s.zfill(width) if width > 0 else s


def weight(bin_str: str) -> int:
    """Количество единиц в строке."""
    return bin_str.count('1')


def bits_to_str(bits: List[int]) -> str:
    return ''.join(str(b) for b in bits)


# Построение проверочной матрицы H (d_min = 3)

def find_r(k: int) -> int:
    """Число проверочных символов r из 2^r >= k + r + 1."""
    r = 1
    while (1 << r) < (k + r + 1):
        r += 1
    return r


def build_P_matrix(r: int, k: int) -> List[List[int]]:
    """Подматрица P' размера r × k. Столбцы начиная с веса 2."""
    P = [[0] * k for _ in range(r)]
    count = 0
    wt = 2

    while count < k and wt <= r:
        for num in range(1, 1 << r):
            if count >= k:
                break
            bin_repr = int_to_bin_str(num, width=r)
            if weight(bin_repr) == wt:
                for i in range(r):
                    P[i][count] = int(bin_repr[i])
                count += 1
        wt += 1

    if count < k:
        raise ValueError(f"Не удалось построить {k} столбцов для r={r}.")
    return P


def build_H_matrix(k: int, r: Optional[int] = None
                   ) -> Tuple[List[List[int]], int, int]:
    """Проверочная матрица H = [P' | I], n = k + r."""
    if r is None:
        r = find_r(k)
    n = k + r

    P = build_P_matrix(r, k)
    H = [[0] * n for _ in range(r)]

    for i in range(r):
        for j in range(k):
            H[i][j] = P[i][j]
        for j in range(r):
            H[i][k + j] = 1 if i == j else 0

    return H, n, r


def matrix_to_str(M: List[List[int]]) -> str:
    return '\n'.join(' '.join(str(x) for x in row) for row in M)


# Кодирование

def compute_parity_bits(Xk: List[int], H: List[List[int]],
                        k: int, r: int) -> List[int]:
    """Вычисление проверочных битов Xr (сумма по модулю 2)."""
    Xr = [0] * r
    for i in range(r):
        s = 0
        for j in range(k):
            s ^= (Xk[j] & H[i][j])
        Xr[i] = s
    return Xr


def encode(Xk: List[int], H: List[List[int]],
           k: int, r: int) -> List[int]:
    """Кодовое слово Xn = [Xk | Xr]."""
    return Xk + compute_parity_bits(Xk, H, k, r)


# Синдром и исправление ошибок

def compute_syndrome(Yn: List[int], H: List[List[int]],
                     r: int, n: int) -> List[int]:
    """Синдром S через пересчёт проверочных битов."""
    k = n - r
    Yr_recomputed = compute_parity_bits(Yn[:k], H, k, r)
    Yr_received = Yn[k:]
    return [1 if Yr_received[i] != Yr_recomputed[i] else 0 for i in range(r)]


def syndrome_matrix_multiply(Yn: List[int], H: List[List[int]],
                             r: int, n: int) -> List[int]:
    """Синдром S = H · Yn^T (mod 2)."""
    S = [0] * r
    for i in range(r):
        s = 0
        for j in range(n):
            s ^= (H[i][j] & Yn[j])
        S[i] = s
    return S


def syndrome_to_error_position(S: List[int], H: List[List[int]],
                               n: int) -> int:
    """
    Позиция ошибки по синдрому:
    -1 — ошибок нет,
    >=0 — позиция одиночной ошибки,
    -2 — вероятно две ошибки.
    """
    if all(s == 0 for s in S):
        return -1
    for j in range(n):
        if [H[i][j] for i in range(len(S))] == S:
            return j
    return -2


def build_error_vector(position: int, n: int) -> List[int]:
    """Унарный вектор ошибки En."""
    En = [0] * n
    if 0 <= position < n:
        En[position] = 1
    return En


def correct_error(Yn: List[int], En: List[int]) -> List[int]:
    """Исправление: Yn XOR En."""
    return [y ^ e for y, e in zip(Yn, En)]


# Внесение ошибок

def introduce_errors(Xn: List[int], num_errors: int
                     ) -> Tuple[List[int], List[int]]:
    """Внесение num_errors случайных ошибок."""
    n = len(Xn)
    Yn = Xn[:]
    positions = random.sample(range(n), num_errors) if num_errors > 0 else []
    for pos in positions:
        Yn[pos] ^= 1
    return Yn, sorted(positions)


# Формирование информационного слова

def text_to_bits(text: str) -> List[int]:
    """Текст → биты (кодировка cp1251)."""
    bits: List[int] = []
    for ch in text:
        try:
            b = ch.encode('cp1251')[0]
        except UnicodeEncodeError:
            b = ord(ch) & 0xFF
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits


def bits_from_text(text: str, min_bits: int = 16) -> List[int]:
    """Информационное слово длиной не менее min_bits."""
    bits = text_to_bits(text)
    while len(bits) < min_bits:
        bits.append(0)
    return bits


def bits_from_file(filename: str, min_bits: int = 16) -> List[int]:
    """Чтение файла и преобразование в биты."""
    with open(filename, 'r', encoding='utf-8') as f:
        text = f.read().strip()
    if not text:
        raise ValueError(f"Файл '{filename}' пуст.")
    return bits_from_text(text, min_bits)


# Основной эксперимент

def run_experiment(info_bits: List[int],
                   num_errors_list: Optional[List[int]] = None,
                   seed: Optional[int] = 42) -> None:
    """Кодирование, внесение 0/1/2 ошибок, декодирование."""
    if seed is not None:
        random.seed(seed)
    if num_errors_list is None:
        num_errors_list = [0, 1, 2]

    def out(s: str = '') -> None:
        print(s)

    k = len(info_bits)
    H, n, r = build_H_matrix(k)
    Xn = encode(info_bits, H, k, r)
    Xr = Xn[k:]

    d_min = 3
    t_o = (d_min - 1) // 2
    t_u = (d_min - 1) // 2

    out()
    out('1. Исходное информационное сообщение (двоичное):')
    out(f'   Xk = {bits_to_str(info_bits)}')
    out(f'   k  = {k}')

    out()
    out('2. Параметры кода:')
    out(f'   r     = {r}')
    out(f'   n     = {n}')
    out(f'   d_min = {d_min}')
    out(f'   t_o   = {t_o}')
    out(f'   t_u   = {t_u}')
    out(f'   R = k/n = {k}/{n} ≈ {k/n:.4f}')

    out()
    out(f'3. Проверочная матрица Хемминга H размера {r}×{n}:')
    out(matrix_to_str(H))

    out()
    out('4. Избыточные символы и кодовое слово:')
    out(f'   Xr = {bits_to_str(Xr)}')
    out(f'   Xn = {bits_to_str(Xn)}')

    for num_err in num_errors_list:
        out()
        out(f'ЭКСПЕРИМЕНТ: внесение {num_err} ошибк(и/ок)')

        Yn, err_pos = introduce_errors(Xn, num_err)
        Yk = Yn[:k]
        Yr_received = Yn[k:]

        out(f'   Позиции ошибок (с 0): {err_pos if err_pos else "нет"}')
        out(f'   Yn  = {bits_to_str(Yn)}')
        out(f'   Yk  = {bits_to_str(Yk)}')
        out(f'   Yr  = {bits_to_str(Yr_received)}')

        Yr_recomputed = compute_parity_bits(Yk, H, k, r)
        out(f"   Yr' = {bits_to_str(Yr_recomputed)}")

        S = compute_syndrome(Yn, H, r, n)
        S_mat = syndrome_matrix_multiply(Yn, H, r, n)
        out(f'   Синдром S = {bits_to_str(S)}')
        if S != S_mat:
            out(f'   !!! Расхождение с матричным умножением: {bits_to_str(S_mat)}')

        pos = syndrome_to_error_position(S, H, n)

        if pos == -1:
            out('   S = 0 → ошибок не обнаружено.')
            En = [0] * n
            Xn_corr = Yn[:]
            out(f'   En = {bits_to_str(En)}')
            out(f'   Исправленное слово = {bits_to_str(Xn_corr)}')
            out('   Информационное слово восстановлено верно.')

        elif pos >= 0:
            out(f'   Обнаружена одиночная ошибка в позиции {pos}.')
            En = build_error_vector(pos, n)
            Xn_corr = correct_error(Yn, En)
            out(f'   En = {bits_to_str(En)}')
            out(f'   Исправленное слово = {bits_to_str(Xn_corr)}')
            if Xn_corr == Xn:
                out('   >>> Ошибка успешно исправлена.')
            else:
                out('   >>> ВНИМАНИЕ: слово не совпало с исходным (возможна кратная ошибка).')

        else:
            out('   Синдром не совпал ни с одним столбцом H.')
            out('   Вероятно, две (или более) ошибки.')
            out('   Код с d_min = 3 обнаруживает, но не исправляет двойную ошибку.')
            En = [0] * n
            out(f'   En = {bits_to_str(En)} (исправление не производилось)')

    out()


def main():
    try:
        info_bits = bits_from_file(
            r'D:\University\PythonProjects\KISBLab2_1\text.txt', min_bits=16
        )
        print("Источник данных: файл 'text.txt'")
    except FileNotFoundError:
        text = "Hello, мир 2026 год!"
        info_bits = bits_from_text(text, min_bits=16)
        print(f"Источник данных: строка в коде ({text!r})")

    run_experiment(
        info_bits,
        num_errors_list=[0, 1, 2],
        seed=42,
    )


if __name__ == '__main__':
    main()