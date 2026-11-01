"""
Итеративный код. Вариант 2: k = 20, матрица 4×5, 2 группы паритетов.
"""

import random


def encode(data: list[int], rows: int = 4, cols: int = 5
           ) -> tuple[list[int], list[list[int]]]:
    """Кодирует data длиной rows*cols в итеративный код."""
    k = rows * cols
    if len(data) != k:
        raise ValueError(f"Нужно {k} бит, получено {len(data)}")
    mat = [[data[r * cols + c] for c in range(cols)] for r in range(rows)]

    h = [sum(mat[r]) & 1 for r in range(rows)]
    v = [sum(mat[r][c] for r in range(rows)) & 1 for c in range(cols)]

    cw = data[:] + h + v
    return cw, mat


def decode(cw: list[int], rows: int = 4, cols: int = 5
           ) -> tuple[list[int], list[int], str]:
    """
    Декодирует. Возвращает (corrected, error_positions, status).
    status: "ok" | "fixed" | "detected" | "undetected"
    """
    k = rows * cols
    n = k + rows + cols
    if len(cw) != n:
        raise ValueError(f"Длина {len(cw)}, ожидалось {n}")

    data = cw[:k]
    h_recv = cw[k:k + rows]
    v_recv = cw[k + rows:]

    mat = [[data[r * cols + c] for c in range(cols)] for r in range(rows)]
    h_calc = [sum(mat[r]) & 1 for r in range(rows)]
    v_calc = [sum(mat[r][c] for r in range(rows)) & 1 for c in range(cols)]

    h_diff = [h_recv[i] ^ h_calc[i] for i in range(rows)]
    v_diff = [v_recv[j] ^ v_calc[j] for j in range(cols)]

    err = [0] * n

    if not any(h_diff) and not any(v_diff):
        return cw[:], err, "ok"

    bad_rows = [i for i in range(rows) if h_diff[i]]
    bad_cols = [j for j in range(cols) if v_diff[j]]

    if len(bad_rows) == 1 and len(bad_cols) == 1:
        r, c = bad_rows[0], bad_cols[0]
        pos = r * cols + c
        err[pos] = 1
        fixed = [cw[i] ^ err[i] for i in range(n)]
        return fixed, err, "fixed"

    if len(bad_rows) == 1 and not bad_cols:
        pos = k + bad_rows[0]
        err[pos] = 1
        fixed = [cw[i] ^ err[i] for i in range(n)]
        return fixed, err, "fixed"

    if len(bad_cols) == 1 and not bad_rows:
        pos = k + rows + bad_cols[0]
        err[pos] = 1
        fixed = [cw[i] ^ err[i] for i in range(n)]
        return fixed, err, "fixed"

    return cw[:], err, "detected"


def inject_errors(cw: list[int], count: int, rng: random.Random | None = None
                  ) -> tuple[list[int], list[int]]:
    rng = rng or random.Random()
    n = len(cw)
    positions = rng.sample(range(n), count)
    err = [0] * n
    for p in positions:
        err[p] = 1
    return [cw[i] ^ err[i] for i in range(n)], err


def inject_rect_errors(cw: list[int], rows: int = 4, cols: int = 5
                       ) -> tuple[list[int], list[int]]:
    """
    Вносит 4 ошибки в вершины прямоугольника (классический
    необнаруживаемый случай для итеративного кода).
    """
    n = len(cw)
    positions = [0, 1, cols, cols + 1]  # (0,0), (0,1), (1,0), (1,1)
    err = [0] * n
    for p in positions:
        err[p] = 1
    return [cw[i] ^ err[i] for i in range(n)], err


def self_test(rows: int = 4, cols: int = 5, trials: int = 1000) -> dict:
    """Анализ корректирующей способности: N2/N1 и N3/N1 для каждой кратности."""
    rng = random.Random(42)
    k = rows * cols
    n = k + rows + cols
    results = {}
    for i in range(0, n + 1):
        detected = fixed = total = 0
        for _ in range(trials):
            data = [rng.randint(0, 1) for _ in range(k)]
            cw, _ = encode(data, rows, cols)
            recv, _ = inject_errors(cw, i, rng)
            corr, _, status = decode(recv, rows, cols)
            total += 1
            if i == 0 or status in ("fixed", "detected"):
                detected += 1
            if status in ("fixed", "ok") and corr == cw:
                fixed += 1
        results[i] = {
            "total": total,
            "detected": detected,
            "fixed": fixed,
            "detect_ratio": detected / total,
            "fix_ratio": fixed / total,
        }
    return results