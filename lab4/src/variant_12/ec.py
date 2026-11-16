"""Модуль 1: алгебра эллиптических кривых над GF(p).

Кривая в короткой форме Вейерштрасса y^2 = x^3 + a*x + b (mod p),
аффинные координаты. Параметры — стандартная кривая bign-curve256v1
из СТБ 34.101.45 (приложение Б).

Здесь собраны «публичные» операции: сложение, удвоение и классическое
умножение Double-and-Add. Они ветвятся по значениям, поэтому для
секретных скаляров используется SecureMultiply из модуля ct.py.
"""

# --------------------------------------------------------------------------
# Параметры кривой bign-curve256v1 (СТБ 34.101.45, табл. Б.1).
# В стандарте числа записаны в порядке little-endian; ниже — обычная
# (big-endian) шестнадцатеричная запись тех же чисел.
# --------------------------------------------------------------------------

P_HEX = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF43"  # 2^256 - 189
A_HEX = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF40"  # p - 3
B_HEX = "77CE6C1515F3A8EDD2C13AABE4D8FBBE4CF55069978B9253B22E7D6BD69C03F1"
Q_HEX = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFD95C8ED60DFB4DFC7E5ABF99263D6607"  # порядок G
GX_HEX = "0000000000000000000000000000000000000000000000000000000000000000"
GY_HEX = "6BF7FC3CFB16D69F5CE4C9A351D6835D78913966C408F6521E29CF1804516A93"

COORD_BYTES = 32


class Point:
    """Точка кривой фиксированного размера: две координаты и флаг O.

    __slots__ запрещает динамический словарь атрибутов: объект всегда
    состоит ровно из трёх полей.
    """
    __slots__ = ("x", "y", "inf")

    def __init__(self, x: int = 0, y: int = 0, inf: int = 0):
        self.x = x
        self.y = y
        self.inf = inf

    @staticmethod
    def infinity() -> "Point":
        return Point(0, 0, 1)

    def copy(self) -> "Point":
        return Point(self.x, self.y, self.inf)

    def __eq__(self, other) -> bool:
        if self.inf or other.inf:
            return self.inf == other.inf
        return self.x == other.x and self.y == other.y

    def hex(self) -> str:
        if self.inf:
            return "O (бесконечно удалённая точка)"
        return f"x = {self.x:064X}\n    y = {self.y:064X}"

    def __repr__(self):
        return "O" if self.inf else f"({self.x:064X}, {self.y:064X})"


class Curve:
    __slots__ = ("name", "p", "a", "b", "q", "G")

    def __init__(self, name, p, a, b, q, gx, gy):
        self.name = name
        self.p, self.a, self.b, self.q = p, a, b, q
        self.G = Point(gx, gy)

    # ---------------- арифметика поля GF(p) ----------------

    def fadd(self, x, y):
        return (x + y) % self.p

    def fsub(self, x, y):
        return (x - y) % self.p

    def fmul(self, x, y):
        return x * y % self.p

    def finv(self, x):
        """Обратный элемент (расширенный алгоритм Евклида внутри pow).
        Время зависит от x, поэтому только для публичных данных."""
        if x % self.p == 0:
            raise ZeroDivisionError("обратного к 0 не существует")
        return pow(x, -1, self.p)

    # ---------------- проверки ----------------

    def is_on_curve(self, P: Point) -> bool:
        if P.inf:
            return True
        x, y, p = P.x, P.y, self.p
        if not (0 <= x < p and 0 <= y < p):
            return False
        return (y * y - (x * x * x + self.a * x + self.b)) % p == 0

    def is_nonsingular(self) -> bool:
        return (4 * pow(self.a, 3, self.p) + 27 * self.b * self.b) % self.p != 0

    # ---------------- групповой закон (аффинные координаты) ----------------

    def neg(self, P: Point) -> Point:
        if P.inf:
            return P.copy()
        return Point(P.x, (-P.y) % self.p)

    def double(self, P: Point) -> Point:
        """2P: s = (3x^2 + a) / (2y), x3 = s^2 - 2x, y3 = s(x - x3) - y."""
        if P.inf or P.y == 0:
            return Point.infinity()
        p = self.p
        s = (3 * P.x * P.x + self.a) * self.finv(2 * P.y) % p
        x3 = (s * s - 2 * P.x) % p
        y3 = (s * (P.x - x3) - P.y) % p
        return Point(x3, y3)

    def add(self, P: Point, Q: Point) -> Point:
        """P + Q: s = (y2 - y1) / (x2 - x1), x3 = s^2 - x1 - x2, y3 = s(x1 - x3) - y1."""
        if P.inf:
            return Q.copy()
        if Q.inf:
            return P.copy()
        p = self.p
        if P.x == Q.x:
            if (P.y + Q.y) % p == 0:
                return Point.infinity()      # Q = -P
            return self.double(P)            # Q = P
        s = (Q.y - P.y) * self.finv(Q.x - P.x) % p
        x3 = (s * s - P.x - Q.x) % p
        y3 = (s * (P.x - x3) - P.y) % p
        return Point(x3, y3)

    def multiply(self, k: int, P: Point) -> Point:
        """Классический Double-and-Add (слева направо).

        if bit == 1: add(...) — ветвление по битам k: число сложений равно
        весу Хэмминга k, поэтому этот метод применяется только к публичным
        скалярам (проверка подписи)."""
        R = Point.infinity()
        if k < 0:
            k, P = -k, self.neg(P)
        for bit in bin(k)[2:]:
            R = self.double(R)
            if bit == "1":
                R = self.add(R, P)
        return R


def _h(s: str) -> int:
    return int(s, 16)


BIGN256 = Curve("bign-curve256v1", _h(P_HEX), _h(A_HEX), _h(B_HEX), _h(Q_HEX), _h(GX_HEX), _h(GY_HEX))


def is_probable_prime(n: int, rounds: int = 32) -> bool:
    """Тест Миллера-Рабина (для самопроверки параметров кривой)."""
    if n < 2:
        return False
    for sp in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % sp == 0:
            return n == sp
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    import random
    rnd = random.Random(n)
    for _ in range(rounds):
        a = rnd.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True
