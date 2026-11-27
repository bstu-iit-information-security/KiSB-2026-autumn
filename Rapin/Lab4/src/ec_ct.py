"""Модуль 3. Constant-time защита: Joye's Double-Add, CSWAP, безопасное сравнение.

Для данных, зависящих от секрета, не используются ветвления и индексация
по секретным значениям: выбор значений выполняется битовыми масками.
"""

from ec_algebra import Point, infinity


def ct_nonzero(x, bits):
    """1, если x != 0, иначе 0 (для 0 <= x < 2^bits), без ветвлений."""
    return ((x | -x) >> bits) & 1


def ct_is_zero(x, bits):
    return 1 ^ ct_nonzero(x, bits)


def ct_select(flag, a, b):
    """a, если flag == 1; b, если flag == 0."""
    mask = -flag
    return (a & mask) | (b & ~mask)


def ct_select_point(flag, P, Q):
    return Point(ct_select(flag, P.X, Q.X),
                 ct_select(flag, P.Y, Q.Y),
                 ct_select(flag, P.Z, Q.Z))


def ct_cswap(flag, P, Q):
    """Условный обмен координат точек на месте: mask = 0 - b; dummy = mask & (X ^ Y)."""
    mask = -flag
    dummy = mask & (P.X ^ Q.X)
    P.X ^= dummy
    Q.X ^= dummy
    dummy = mask & (P.Y ^ Q.Y)
    P.Y ^= dummy
    Q.Y ^= dummy
    dummy = mask & (P.Z ^ Q.Z)
    P.Z ^= dummy
    Q.Z ^= dummy


def secure_add(curve, P1, P2):
    """Сложение без ветвлений: все особые случаи разрешаются масками.

    Всегда вычисляются и общая формула сложения, и удвоение.
    """
    bits = curve.p.bit_length()
    P3, H, R = curve.add_raw(P1, P2)
    D = curve.double(P1)
    inf1 = ct_is_zero(P1.Z, bits)
    inf2 = ct_is_zero(P2.Z, bits)
    same = ct_is_zero(H, bits) & ct_is_zero(R, bits) & (1 - inf1) & (1 - inf2)
    # H == 0, R != 0 (P1 = -P2): формула уже даёт Z3 = 0, т.е. O.
    result = ct_select_point(same, D, P3)
    result = ct_select_point(inf2, P1, result)
    result = ct_select_point(inf1, P2, result)
    return result


def secure_multiply(curve, k, P):
    """Скалярное умножение k*P алгоритмом Joye's Double-Add (справа налево).

    R0 = O, R1 = P. Для каждого бита d_i (от младшего к старшему) выполняется
    ровно одно удвоение и одно сложение: R_{1-d_i} = 2*R_{1-d_i} + R_{d_i}.
    Число итераций фиксировано и равно длине порядка q.
    """
    nbits = curve.q.bit_length()
    if k < 0 or k >> nbits:
        raise ValueError("scalar out of range")
    R0 = infinity()
    R1 = P.copy()
    for i in range(nbits):
        bit = (k >> i) & 1
        swap = 1 - bit
        ct_cswap(swap, R0, R1)
        R0 = secure_add(curve, curve.double(R0), R1)
        ct_cswap(swap, R0, R1)
    return R0


def secure_compare(curve, A, B):
    """Сравнение точек (в проективных координатах) XOR-аккумулятором без раннего выхода.

    Возвращает 1, если точки равны, иначе 0.
    """
    p = curve.p
    bits = p.bit_length()
    z1sq = A.Z * A.Z % p
    z2sq = B.Z * B.Z % p
    acc = (A.X * z2sq - B.X * z1sq) % p
    acc |= (A.Y * z2sq % p * B.Z - B.Y * z1sq % p * A.Z) % p
    acc |= ct_is_zero(A.Z, bits) ^ ct_is_zero(B.Z, bits)
    return ct_is_zero(acc, bits)
