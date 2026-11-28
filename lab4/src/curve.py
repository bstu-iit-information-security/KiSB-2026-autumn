from dataclasses import dataclass


P = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF43", 16)
A = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF40", 16)
B = int("77CE6C1515F3A8EDD2C13AABE4D8FBBE4CF55069978B9253B22E7D6BD69C03F1", 16)
Q = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFD95C8ED60DFB4DFC7E5ABF99263D6607", 16)
GX = int("00", 16)
GY = int("6BF7FC3CFB16D69F5CE4C9A351D6835D78913966C408F6521E29CF1804516A93", 16)


@dataclass(frozen=True, slots=True)
class Point:
    x: int | None = None
    y: int | None = None

    @property
    def is_infinity(self):
        return self.x is None or self.y is None


INFINITY = Point()
GENERATOR = Point(GX, GY)


class Curve:
    def __init__(self, p, a, b, generator, order):
        self.p = p
        self.a = a
        self.b = b
        self.generator = generator
        self.order = order
        self.coordinate_size = (p.bit_length() + 7) // 8
        if (4 * a ** 3 + 27 * b ** 2) % p == 0:
            raise ValueError("Особая кривая")
        if not self.is_on_curve(generator):
            raise ValueError("Базовая точка не принадлежит кривой")

    def inverse(self, value):
        return pow(value, -1, self.p)

    def is_on_curve(self, point):
        if point.is_infinity:
            return True
        x, y = point.x, point.y
        return (y * y - x * x * x - self.a * x - self.b) % self.p == 0

    def negate(self, point):
        if point.is_infinity:
            return INFINITY
        return Point(point.x, (-point.y) % self.p)

    def double(self, point):
        if point.is_infinity or point.y == 0:
            return INFINITY
        x, y = point.x, point.y
        numerator = (3 * x * x + self.a) % self.p
        slope = numerator * self.inverse((2 * y) % self.p) % self.p
        x3 = (slope * slope - 2 * x) % self.p
        y3 = (slope * (x - x3) - y) % self.p
        return Point(x3, y3)

    def add(self, first, second):
        if first.is_infinity:
            return second
        if second.is_infinity:
            return first
        if first.x == second.x:
            if (first.y + second.y) % self.p == 0 or first.y == 0:
                return INFINITY
            return self.double(first)
        slope = ((second.y - first.y) * self.inverse((second.x - first.x) % self.p)) % self.p
        x3 = (slope * slope - first.x - second.x) % self.p
        y3 = (slope * (first.x - x3) - first.y) % self.p
        return Point(x3, y3)

    def multiply_classic(self, scalar, point):
        if scalar < 0:
            raise ValueError("Отрицательный скаляр")
        result = INFINITY
        current = point
        while scalar:
            if scalar & 1:
                result = self.add(result, current)
            current = self.double(current)
            scalar >>= 1
        return result

    def valid_public_key(self, point):
        return (not point.is_infinity and self.is_on_curve(point) and
                self.multiply_classic(self.order, point).is_infinity)

    def encode_point(self, point):
        if point.is_infinity:
            return bytes(2 * self.coordinate_size)
        return (point.x.to_bytes(self.coordinate_size, "little") +
                point.y.to_bytes(self.coordinate_size, "little"))

    def decode_point(self, raw):
        size = self.coordinate_size
        if len(raw) != 2 * size:
            raise ValueError("Неверная длина точки")
        x = int.from_bytes(raw[:size], "little")
        y = int.from_bytes(raw[size:], "little")
        point = Point(x, y)
        if x == 0 and y == 0:
            return INFINITY
        if not self.is_on_curve(point):
            raise ValueError("Точка не лежит на кривой")
        return point
