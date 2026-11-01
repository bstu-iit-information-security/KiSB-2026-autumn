"""
Код Хемминга. Поддержка d_min = 3 (классический) и d_min = 4 (расширенный).
"""

import random


def hamming_params(k: int, dmin: int) -> tuple[int, int]:
    """Возвращает (n, r) для заданного k и d_min."""
    r = 1
    while (1 << r) < k + r + 1:
        r += 1
    if dmin == 4:
        return k + r + 1, r + 1
    return k + r, r


def _data_positions(n: int, r: int, dmin: int = 3) -> list[int]:
    """0-индексированные позиции информационных битов."""
    check = set((1 << i) - 1 for i in range(r))
    last = n - 1 if dmin == 4 else n
    return [i for i in range(last) if i not in check]


def _check_positions(n: int, r: int) -> list[int]:
    """0-индексированные позиции проверочных битов (степени 2 − 1)."""
    return [(1 << i) - 1 for i in range(r) if (1 << i) - 1 < n]


def build_check_matrix(k: int, dmin: int = 3) -> tuple[list[list[int]], int, int]:
    """
    Проверочная матрица H (r × n).
    Классический код Хемминга: столбцы — числа 1..n в двоичном виде
    (проверочные позиции 0, 1, 3, 7, ... — там, где cols[j] = 2^i).
    Для d=4 последний столбец — нулевой (общий бит чётности),
         последняя строка — все единицы.
    """
    n, r = hamming_params(k, dmin)
    data_r = r if dmin == 3 else r - 1

    if dmin == 3:
        cols = list(range(1, n + 1))
        H = [[(col >> i) & 1 for col in cols] for i in range(data_r)]
    else:
        cols = list(range(1, n)) + [0]   # последний — 0 (общий бит)
        H = [[(col >> i) & 1 for col in cols] for i in range(data_r)]
        H.append([1] * n)                # общая проверка на чётность

    return H, n, r


def encode(data: list[int], dmin: int = 3
           ) -> tuple[list[int], list[list[int]], int, int]:
    """Кодирует data длиной k. Возвращает (codeword, H, n, r)."""
    k = len(data)
    H, n, r = build_check_matrix(k, dmin)
    data_r = r if dmin == 3 else r - 1
    data_pos = _data_positions(n, data_r, dmin)
    check_pos = _check_positions(n, data_r)

    cw = [0] * n
    for idx, pos in enumerate(data_pos):
        if idx < k:
            cw[pos] = data[idx]

    # Итеративно правим проверочные биты, пока синдром не станет нулевым
    for _ in range(data_r + 2):
        s = [sum(H[i][j] * cw[j] for j in range(n)) & 1
             for i in range(data_r)]
        if not any(s):
            break
        for i in range(data_r):
            if s[i]:
                cw[check_pos[i]] ^= 1

    # Для d=4: общий бит чётности
    if dmin == 4:
        cw[n - 1] = sum(cw[:n - 1]) & 1

    return cw, H, n, r


def syndrome(cw: list[int], H: list[list[int]]) -> list[int]:
    """S = H · cwᵀ (mod 2)."""
    return [sum(row[i] * cw[i] for i in range(len(cw))) & 1 for row in H]


def decode(received: list[int], H: list[list[int]], dmin: int = 3
           ) -> tuple[list[int], list[int], list[int]]:
    """Декодирует. Возвращает (corrected, syndrome, error_vector)."""
    s = syndrome(received, H)
    n = len(received)
    err = [0] * n

    if not any(s):
        return received[:], s, err

    if dmin == 3:
        # Синдром = номер позиции ошибки (1-индексация)
        s_int = sum(b << i for i, b in enumerate(s))
        if 1 <= s_int <= n:
            err[s_int - 1] = 1
    else:
        H_core = H[:-1]
        s_core = s[:-1]
        s_core_int = sum(b << i for i, b in enumerate(s_core))
        for j in range(n):
            col_int = sum(H_core[i][j] << i for i in range(len(H_core)))
            if col_int == s_core_int:
                err[j] = 1
                break
        if not any(s_core) and s[-1] == 1:
            err[-1] = 1

    corrected = [received[i] ^ err[i] for i in range(n)]
    return corrected, s, err


def inject_errors(cw: list[int], count: int, rng: random.Random | None = None
                  ) -> tuple[list[int], list[int]]:
    """Вносит count случайных ошибок в кодовое слово."""
    rng = rng or random.Random()
    n = len(cw)
    if count > n:
        raise ValueError(f"count > n ({count} > {n})")
    positions = rng.sample(range(n), count)
    err = [0] * n
    for p in positions:
        err[p] = 1
    return [cw[i] ^ err[i] for i in range(n)], err


def self_test(k: int = 4, dmin: int = 3, trials: int = 1000) -> dict:
    """Для каждой кратности 0..n: сколько обнаружено, сколько исправлено."""
    rng = random.Random(42)
    results = {}
    n_full, _ = hamming_params(k, dmin)
    for i in range(0, n_full + 1):
        detected = fixed = total = 0
        for _ in range(trials):
            data = [rng.randint(0, 1) for _ in range(k)]
            cw, H, n, r = encode(data, dmin)
            recv, _ = inject_errors(cw, i, rng)
            corr, s, _ = decode(recv, H, dmin)
            total += 1
            if i == 0 or any(s):
                detected += 1
            if corr == cw:
                fixed += 1
        results[i] = {
            "total": total,
            "detected": detected,
            "fixed": fixed,
            "detect_ratio": detected / total,
            "fix_ratio": fixed / total,
        }
    return results