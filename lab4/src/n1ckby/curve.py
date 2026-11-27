from typing import NamedTuple


P = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF43", 16)
A = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF40", 16)
B = int("77CE6C1515F3A8EDD2C13AABE4D8FBBE4CF55069978B9253B22E7D6BD69C03F1", 16)
Q = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFD95C8ED60DFB4DFC7E5ABF99263D6607", 16)
YG = int("6BF7FC3CFB16D69F5CE4C9A351D6835D78913966C408F6521E29CF1804516A93", 16)


class Point(NamedTuple):
    x: int
    y: int
    infinity: int = 0


G = Point(int("00", 16), YG)
O = Point(0, 0, 1)


def choose(bit, left, right):
    mask = -bit
    return Point(*(a ^ ((a ^ b) & mask) for a, b in zip(left, right)))


def double(t):
    x, y = t.x, t.y
    slope = (3*x*x + A) * pow(2*y % P, P-2, P) % P
    rx = (slope*slope - 2*x) % P
    result = Point(rx, (slope*(x-rx) - y) % P)
    return choose(t.infinity | int(y == 0), result, O)


def add(t, u):
    dx = (u.x - t.x) % P
    slope = (u.y - t.y) * pow(dx, P-2, P) % P
    rx = (slope*slope - t.x - u.x) % P
    result = Point(rx, (slope*(t.x-rx) - t.y) % P)
    special = choose(int(t.y == u.y), O, double(t))
    result = choose(int(dx == 0), result, special)
    result = choose(t.infinity, result, u)
    return choose(u.infinity, result, t)


def multiply(k, t):
    """Double-and-Add для общедоступных значений."""
    result = O
    for bit in bin(k)[2:]:
        result = double(result)
        if bit == "1":
            result = add(result, t)
    return result


def valid(t):
    return (t.infinity == 0 and 0 <= t.x < P and 0 <= t.y < P
            and (t.y**2 - t.x**3 - A*t.x - B) % P == 0
            and multiply(Q, t) == O)
