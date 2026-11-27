"""Модуль 1. Алгебра эллиптических кривых y^2 = x^3 + a*x + b над GF(p).

Точки хранятся в проективных координатах Якоби (X, Y, Z):
x = X / Z^2, y = Y / Z^3, точка на бесконечности O = (1, 1, 0).
"""


def hex_to_int(value):
    return int(value, 16)


def int_to_hex(value, nbytes):
    return format(value, "0{}x".format(nbytes * 2))


def mod_inv(a, m):
    """Обратный элемент по простому модулю через малую теорему Ферма: a^(m-2)."""
    a %= m
    if a == 0:
        raise ZeroDivisionError("zero has no inverse")
    return pow(a, m - 2, m)


class Point:
    __slots__ = ("X", "Y", "Z")

    def __init__(self, X, Y, Z):
        self.X = X
        self.Y = Y
        self.Z = Z

    def copy(self):
        return Point(self.X, self.Y, self.Z)


def infinity():
    return Point(1, 1, 0)


class Curve:
    def __init__(self, p_hex, a_hex, b_hex, gx_hex, gy_hex, q_hex):
        self.p = hex_to_int(p_hex)
        self.a = hex_to_int(a_hex) % self.p
        self.b = hex_to_int(b_hex) % self.p
        self.q = hex_to_int(q_hex)
        self.nbytes = (self.p.bit_length() + 7) // 8
        if (4 * pow(self.a, 3, self.p) + 27 * self.b * self.b) % self.p == 0:
            raise ValueError("singular curve")
        self.G = self.from_affine(hex_to_int(gx_hex), hex_to_int(gy_hex))
        if not self.is_on_curve(self.G):
            raise ValueError("base point is not on the curve")
        if self.multiply(self.q, self.G).Z != 0:
            raise ValueError("q*G != O")

    def from_affine(self, x, y):
        if not (0 <= x < self.p and 0 <= y < self.p):
            raise ValueError("coordinates out of range")
        return Point(x, y, 1)

    def to_affine(self, P):
        if P.Z % self.p == 0:
            raise ValueError("point at infinity has no affine form")
        zi = mod_inv(P.Z, self.p)
        zi2 = zi * zi % self.p
        return P.X * zi2 % self.p, P.Y * zi2 * zi % self.p

    def is_infinity(self, P):
        return P.Z % self.p == 0

    def is_on_curve(self, P):
        """Y^2 = X^3 + a*X*Z^4 + b*Z^6 (mod p)."""
        p = self.p
        if P.Z % p == 0:
            return True
        z2 = P.Z * P.Z % p
        z4 = z2 * z2 % p
        z6 = z4 * z2 % p
        left = P.Y * P.Y % p
        right = (P.X * P.X % p * P.X + self.a * P.X % p * z4 + self.b * z6) % p
        return left == right

    def double(self, P):
        p = self.p
        X1, Y1, Z1 = P.X, P.Y, P.Z
        Y1sq = Y1 * Y1 % p
        S = 4 * X1 * Y1sq % p
        Z1sq = Z1 * Z1 % p
        M = (3 * X1 * X1 + self.a * Z1sq % p * Z1sq) % p
        X3 = (M * M - 2 * S) % p
        Y3 = (M * (S - X3) - 8 * Y1sq * Y1sq) % p
        Z3 = 2 * Y1 * Z1 % p
        return Point(X3, Y3, Z3)

    def add_raw(self, P1, P2):
        """Формулы сложения Якоби без обработки особых случаев.

        Корректны при P1 != +-P2 и обеих точках не на бесконечности.
        Возвращает (P3, H, R).
        """
        p = self.p
        X1, Y1, Z1 = P1.X, P1.Y, P1.Z
        X2, Y2, Z2 = P2.X, P2.Y, P2.Z
        Z1sq = Z1 * Z1 % p
        Z2sq = Z2 * Z2 % p
        U1 = X1 * Z2sq % p
        U2 = X2 * Z1sq % p
        S1 = Y1 * Z2sq % p * Z2 % p
        S2 = Y2 * Z1sq % p * Z1 % p
        H = (U2 - U1) % p
        R = (S2 - S1) % p
        H2 = H * H % p
        H3 = H2 * H % p
        U1H2 = U1 * H2 % p
        X3 = (R * R - H3 - 2 * U1H2) % p
        Y3 = (R * (U1H2 - X3) - S1 * H3) % p
        Z3 = H * Z1 % p * Z2 % p
        return Point(X3, Y3, Z3), H, R

    def add(self, P1, P2):
        """Классическое (ветвящееся) сложение; для публичных данных."""
        if self.is_infinity(P1):
            return P2.copy()
        if self.is_infinity(P2):
            return P1.copy()
        P3, H, R = self.add_raw(P1, P2)
        if H == 0:
            if R == 0:
                return self.double(P1)
            return infinity()
        return P3

    def multiply(self, k, P):
        """Классический Double-and-Add слева направо; для публичных данных."""
        if k < 0:
            raise ValueError("negative scalar")
        result = infinity()
        for i in range(k.bit_length() - 1, -1, -1):
            result = self.double(result)
            if (k >> i) & 1:
                result = self.add(result, P)
        return result
