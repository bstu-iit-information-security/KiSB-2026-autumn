# -*- coding: utf-8 -*-
"""
Модуль 1. Алгебра эллиптической кривой Ed25519 (скрученная кривая Эдвардса)
в аффинных координатах:

        a*x^2 + y^2 = 1 + d*x^2*y^2  (mod p),   a = -1,   p = 2^255 - 19.

Инкапсулирует параметры кривой (p, a, d, G, q), структуру «Точка» и операции
над ней: add(P, Q), double(P), multiply(k, P). Арифметика GF(p) выполняется
встроенными целыми числами Python произвольной длины (BigInt).
Параметры заданы шестнадцатеричными строками (RFC 8032, раздел 5.1).
"""

# ----------------------------------------------------------------------
#                     ПАРАМЕТРЫ КРИВОЙ Ed25519
# ----------------------------------------------------------------------
P_HEX = "7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffed"   # 2^255 - 19
A_HEX = "7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffec"   # -1 mod p
D_HEX = "52036cee2b6ffe738cc740797779e89800700a4d4141d8ab75eb4dca135978a3"   # -121665/121666
Q_HEX = "1000000000000000000000000000000014def9dea2f79cd65812631a5cf5d3ed"   # порядок G
GX_HEX = "216936d3cd6e53fec0a4e231fdd6dc5c692cc7609525a7b2c9562d608f25d51a"
GY_HEX = "6666666666666666666666666666666666666666666666666666666666666658"  # 4/5 mod p
COFACTOR = 8

P = int(P_HEX, 16)
A = int(A_HEX, 16)
D = int(D_HEX, 16)
Q = int(Q_HEX, 16)
FIELD_BITS = 256          # все элементы поля и скаляры умещаются в 256 бит


# ----------------------------------------------------------------------
#                     АРИФМЕТИКА ПОЛЯ GF(p)
# ----------------------------------------------------------------------
def fadd(a, b):
    return (a + b) % P


def fsub(a, b):
    return (a - b) % P


def fmul(a, b):
    return a * b % P


def finv(a):
    """Обратный элемент по Малой теореме Ферма: a^(-1) = a^(p-2) mod p.
    Показатель степени публичный и постоянный, ветвлений по значению a нет."""
    return pow(a, P - 2, P)


# ----------------------------------------------------------------------
#                     СТРУКТУРА «ТОЧКА»
# ----------------------------------------------------------------------
class Point:
    """Точка (x, y) в аффинных координатах. __slots__ задаёт фиксированную
    структуру из двух полей без динамического словаря атрибутов."""
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x % P
        self.y = y % P

    def __eq__(self, other):
        """Обычное (не constant-time) сравнение — только для публичных данных."""
        return self.x == other.x and self.y == other.y

    def hex(self, indent=""):
        return f"{indent}x = {self.x:064x}\n{indent}y = {self.y:064x}"

    def __repr__(self):
        return f"Point(x={self.x:064x}, y={self.y:064x})"


O = Point(0, 1)                                   # нейтральный элемент группы
G = Point(int(GX_HEX, 16), int(GY_HEX, 16))       # базовая точка


def is_on_curve(pt):
    """Проверка a*x^2 + y^2 - 1 - d*x^2*y^2 = 0 (mod p)."""
    xx, yy = fmul(pt.x, pt.x), fmul(pt.y, pt.y)
    return (A * xx + yy - 1 - D * xx * yy) % P == 0


def neg(pt):
    """-(x, y) = (-x, y)."""
    return Point(-pt.x, pt.y)


# ----------------------------------------------------------------------
#                     СЛОЖЕНИЕ И УДВОЕНИЕ ТОЧЕК
# ----------------------------------------------------------------------
def add(p1, p2):
    """Полный (единый) закон сложения Эдвардса, справедлив и для P = Q:
        x3 = (x1*y2 + y1*x2) / (1 + d*x1*x2*y1*y2)
        y3 = (y1*y2 - a*x1*x2) / (1 - d*x1*x2*y1*y2)
    Оба знаменателя обращаются одной инверсией: 1/u = v/(u*v), 1/v = u/(u*v)."""
    x1x2, y1y2 = fmul(p1.x, p2.x), fmul(p1.y, p2.y)
    t = fmul(D, fmul(x1x2, y1y2))
    num_x = fadd(fmul(p1.x, p2.y), fmul(p1.y, p2.x))
    num_y = fsub(y1y2, fmul(A, x1x2))
    den_x, den_y = fadd(1, t), fsub(1, t)
    inv = finv(fmul(den_x, den_y))
    return Point(num_x * den_y * inv, num_y * den_x * inv)


def double(p1):
    """Удвоение (формула сложения при P = Q с учётом уравнения кривой
    1 + d*x^2*y^2 = a*x^2 + y^2):
        x3 = 2*x*y / (a*x^2 + y^2)
        y3 = (y^2 - a*x^2) / (2 - a*x^2 - y^2)"""
    xx, yy, xy = fmul(p1.x, p1.x), fmul(p1.y, p1.y), fmul(p1.x, p1.y)
    den_x = fadd(fmul(A, xx), yy)
    den_y = fsub(2, den_x)
    inv = finv(fmul(den_x, den_y))
    return Point(2 * xy * den_y * inv, fsub(yy, fmul(A, xx)) * den_x * inv)


def sub(p1, p2):
    return add(p1, neg(p2))


def multiply(k, pt):
    """Классический Double-and-Add «слева направо». Число сложений равно весу
    Хэмминга k, поэтому применяется ТОЛЬКО для публичных скаляров (проверка
    подписи). Для секретных скаляров — ct_secure.secure_multiply."""
    r = O
    for bit in bin(k)[2:]:
        r = double(r)
        if bit == "1":
            r = add(r, pt)
    return r


# ----------------------------------------------------------------------
#                     КОДИРОВАНИЕ ТОЧЕК (RFC 8032, 5.1.2)
# ----------------------------------------------------------------------
def encode_point(pt):
    """32 байта little-endian: координата y, старший бит — чётность x."""
    return (pt.y | ((pt.x & 1) << 255)).to_bytes(32, "little")


def x2_from_y(y):
    """Из уравнения кривой: x^2 = (y^2 - 1) / (d*y^2 - a) = (y^2 - 1) / (d*y^2 + 1)."""
    yy = fmul(y, y)
    return fmul(fsub(yy, 1), finv(fsub(fmul(D, yy), A)))
