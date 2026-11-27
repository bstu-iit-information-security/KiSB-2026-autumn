"""Якобианские координаты. Параметры контрольной кривой RFC 7091, раздел 7."""
from typing import NamedTuple


class Point(NamedTuple):
    x: int
    y: int
    z: int


P = int("8000000000000000000000000000000000000000000000000000000000000431", 16)
A = int("07", 16)
B = int("5fbff498aa938ce739b8e022fbafef40563f6e6a3472fc2a514c0ce9dae23b7e", 16)
Q = int("8000000000000000000000000000000150fe8a1892976154c59cfc193accf5b3", 16)
G = Point(int("02", 16),
          int("08e2a8a0e65147d4bd6316030e16d19c85c97f0a9ca267122b96abbcea7e8fc8", 16), 1)
O = Point(1, 1, 0)


def affine(t):
    inverse = pow(t.z, -1, P)
    return t.x * inverse**2 % P, t.y * inverse**3 % P


def select(left, right, bit):
    mask = -int(bit)
    return Point(*(a ^ ((a ^ b) & mask) for a, b in zip(left, right)))


def double(t):
    x, y, z = t
    m = (3*x*x + A*z**4) % P
    s = 4*x*y*y % P
    nx = (m*m - 2*s) % P
    return Point(nx, (m*(s-nx) - 8*y**4) % P, 2*y*z % P)


def add(t, u):
    x1, y1, z1 = t
    x2, y2, z2 = u
    u1, u2 = x1*z2**2 % P, x2*z1**2 % P
    s1, s2 = y1*z2**3 % P, y2*z1**3 % P
    h, r = (u2-u1) % P, (s2-s1) % P
    nx = (r*r - h**3 - 2*u1*h*h) % P
    result = Point(nx, (r*(u1*h*h-nx) - s1*h**3) % P, h*z1*z2 % P)
    result = select(result, double(t), (h == 0) & (r == 0))
    result = select(result, t, z2 == 0)
    return select(result, u, z1 == 0)


def multiply(k, t):
    """Double-and-Add для открытых скаляров."""
    result = O
    for bit in bin(k)[2:]:
        result = double(result)
        if bit == "1":
            result = add(result, t)
    return result
