# decoder.py
"""
Декодирование: Yn -> (Yk_fixed, errors_found, identified, corrected).
Поиск и исправление ошибок по синдромам.
"""

from matrix_ops import (bits_to_matrix_2d, bits_to_matrix_3d,
                        matrix_2d_to_bits, matrix_3d_to_bits, flatten)
from parity import (parity_2groups_2d, parity_3groups_2d,
                    parity_4groups_3d, parity_5groups_3d)


def decode_2groups_2d(Yn, k1, k2):
    """
    Декодирование для 2 групп (2D).
    """
    k = k1 * k2
    Yk = Yn[:k]
    off = k

    Yh_rx = Yn[off:off + k1];
    off += k1
    Yv_rx = Yn[off:off + k2];
    off += k2
    Yhv_rx = Yn[off]

    m = bits_to_matrix_2d(Yk, k1, k2)
    Yh_calc, Yv_calc, Yhv_calc = parity_2groups_2d(m)

    # Синдромы (расхождения)
    dYh = [Yh_rx[i] ^ Yh_calc[i] for i in range(k1)]
    dYv = [Yv_rx[j] ^ Yv_calc[j] for j in range(k2)]
    dYhv = Yhv_rx ^ Yhv_calc

    Yk_fixed = list(Yk)
    errors_found = []
    identified = False
    corrected = False

    # Если все синдромы нулевые — ошибок нет
    if not any(dYh) and not any(dYv) and dYhv == 0:
        return Yk_fixed, [], True, True

    # Ищем одиночную ошибку среди информационных бит
    rows_err = [i for i, v in enumerate(dYh) if v]
    cols_err = [j for j, v in enumerate(dYv) if v]

    if len(rows_err) == 1 and len(cols_err) == 1:
        i, j = rows_err[0], cols_err[0]
        pos = i * k2 + j
        errors_found = [pos]
        Yk_fixed[pos] ^= 1
        identified = True

        # Проверяем, что исправление сделало синдром нулевым
        m2 = bits_to_matrix_2d(Yk_fixed, k1, k2)
        h2, v2, hv2 = parity_2groups_2d(m2)
        corrected = (h2 == Yh_rx and v2 == Yv_rx and hv2 == Yhv_rx)

    # Если не нашли в информационных, проверяем ошибки в паритетах
    if not corrected:
        for pos in range(k, len(Yn)):
            Yn_try = list(Yn)
            Yn_try[pos] ^= 1

            Yk_try = Yn_try[:k]
            off_t = k
            Yh_try = Yn_try[off_t:off_t + k1];
            off_t += k1
            Yv_try = Yn_try[off_t:off_t + k2];
            off_t += k2
            Yhv_try = Yn_try[off_t]

            m2 = bits_to_matrix_2d(Yk_try, k1, k2)
            h2, v2, hv2 = parity_2groups_2d(m2)

            if h2 == Yh_try and v2 == Yv_try and hv2 == Yhv_try:
                return Yk_try, [pos], True, True

    return Yk_fixed, errors_found, identified, corrected


def decode_3groups_2d(Yn, k1, k2):
    """
    Декодирование для 3 групп (2D): добавляются диагонали.
    """
    k = k1 * k2
    Yk = Yn[:k]
    off = k

    Yh_rx = Yn[off:off + k1];
    off += k1
    Yv_rx = Yn[off:off + k2];
    off += k2
    Yhv_rx = Yn[off];
    off += 1
    Yd_rx = Yn[off:off + (k1 + k2 - 1)]

    m = bits_to_matrix_2d(Yk, k1, k2)
    Yh_c, Yv_c, Yhv_c, Yd_c = parity_3groups_2d(m)

    dYh = [Yh_rx[i] ^ Yh_c[i] for i in range(k1)]
    dYv = [Yv_rx[j] ^ Yv_c[j] for j in range(k2)]
    dYd = [Yd_rx[s] ^ Yd_c[s] for s in range(k1 + k2 - 1)]
    dYhv = Yhv_rx ^ Yhv_c

    Yk_fixed = list(Yk)
    errors_found = []
    identified = False
    corrected = False

    if not any(dYh) and not any(dYv) and not any(dYd) and dYhv == 0:
        return Yk_fixed, [], True, True

    rows_err = [i for i, v in enumerate(dYh) if v]
    cols_err = [j for j, v in enumerate(dYv) if v]

    # Одиночная ошибка в информации
    if len(rows_err) == 1 and len(cols_err) == 1:
        i, j = rows_err[0], cols_err[0]
        pos = i * k2 + j
        errors_found = [pos]
        Yk_fixed[pos] ^= 1
        identified = True
        m2 = bits_to_matrix_2d(Yk_fixed, k1, k2)
        h2, v2, hv2, d2 = parity_3groups_2d(m2)
        corrected = (h2 == Yh_rx and v2 == Yv_rx and hv2 == Yhv_rx and d2 == Yd_rx)

    # Поиск ошибки в избыточных битах (если одиночная в инфо не помогла)
    if not corrected:
        for pos in range(k, len(Yn)):
            Yn_try = list(Yn)
            Yn_try[pos] ^= 1
            Yk_try = Yn_try[:k]
            off_t = k
            Yh_try = Yn_try[off_t:off_t + k1];
            off_t += k1
            Yv_try = Yn_try[off_t:off_t + k2];
            off_t += k2
            Yhv_try = Yn_try[off_t];
            off_t += 1
            Yd_try = Yn_try[off_t:off_t + (k1 + k2 - 1)]

            m2 = bits_to_matrix_2d(Yk_try, k1, k2)
            h2, v2, hv2, d2 = parity_3groups_2d(m2)
            if h2 == Yh_try and v2 == Yv_try and hv2 == Yhv_try and d2 == Yd_try:
                return Yk_try, [pos], True, True

    return Yk_fixed, errors_found, identified, corrected


def decode_4groups_3d(Yn, a, b, c):
    """Декодирование для 4 групп (3D). Поиск по всему слову."""
    k = a * b * c
    Yk = Yn[:k]
    off = k

    len_Xh = c * a
    len_Xv = c * b
    len_Xz = a * b

    Yh_rx = Yn[off:off + len_Xh];
    off += len_Xh
    Yv_rx = Yn[off:off + len_Xv];
    off += len_Xv
    Yz_rx = Yn[off:off + len_Xz];
    off += len_Xz
    Yhv_rx = Yn[off]

    planes = bits_to_matrix_3d(Yk, a, b, c)
    Yh_c, Yv_c, Yz_c, Yhv_c = parity_4groups_3d(planes)

    if (flatten(Yh_c) == Yh_rx and flatten(Yv_c) == Yv_rx and
            flatten(Yz_c) == Yz_rx and Yhv_c == Yhv_rx):
        return list(Yk), [], True, True

    for pos in range(len(Yn)):
        Yn_try = list(Yn)
        Yn_try[pos] ^= 1

        Yk_try = Yn_try[:k]
        off_t = k
        Yh_try = Yn_try[off_t:off_t + len_Xh];
        off_t += len_Xh
        Yv_try = Yn_try[off_t:off_t + len_Xv];
        off_t += len_Xv
        Yz_try = Yn_try[off_t:off_t + len_Xz];
        off_t += len_Xz
        Yhv_try = Yn_try[off_t]

        planes_try = bits_to_matrix_3d(Yk_try, a, b, c)
        h2, v2, z2, hv2 = parity_4groups_3d(planes_try)

        if (flatten(h2) == Yh_try and flatten(v2) == Yv_try and
                flatten(z2) == Yz_try and hv2 == Yhv_try):
            return Yk_try, [pos], True, True

    return list(Yk), [], False, False


def decode_5groups_3d(Yn, a, b, c):
    """Декодирование для 5 групп (3D). Поиск по всему слову."""
    k = a * b * c
    Yk = Yn[:k]
    off = k

    len_Xh = c * a
    len_Xv = c * b
    len_Xz = a * b

    Yh_rx = Yn[off:off + len_Xh];
    off += len_Xh
    Yv_rx = Yn[off:off + len_Xv];
    off += len_Xv
    Yz_rx = Yn[off:off + len_Xz];
    off += len_Xz
    Yhv_rx = Yn[off];
    off += 1
    Yd_rx = Yn[off:off + c]

    planes = bits_to_matrix_3d(Yk, a, b, c)
    Yh_c, Yv_c, Yz_c, Yhv_c, Yd_c = parity_5groups_3d(planes)

    if (flatten(Yh_c) == Yh_rx and flatten(Yv_c) == Yv_rx and
            flatten(Yz_c) == Yz_rx and Yhv_c == Yhv_rx and Yd_c == Yd_rx):
        return list(Yk), [], True, True

    for pos in range(len(Yn)):
        Yn_try = list(Yn)
        Yn_try[pos] ^= 1

        Yk_try = Yn_try[:k]
        off_t = k
        Yh_try = Yn_try[off_t:off_t + len_Xh];
        off_t += len_Xh
        Yv_try = Yn_try[off_t:off_t + len_Xv];
        off_t += len_Xv
        Yz_try = Yn_try[off_t:off_t + len_Xz];
        off_t += len_Xz
        Yhv_try = Yn_try[off_t];
        off_t += 1
        Yd_try = Yn_try[off_t:off_t + c]

        planes_try = bits_to_matrix_3d(Yk_try, a, b, c)
        h2, v2, z2, hv2, d2 = parity_5groups_3d(planes_try)

        if (flatten(h2) == Yh_try and flatten(v2) == Yv_try and
                flatten(z2) == Yz_try and hv2 == Yhv_try and d2 == Yd_try):
            return Yk_try, [pos], True, True

    return list(Yk), [], False, False