from dataclasses import dataclass
from typing import Optional
from .field import Field


@dataclass(frozen=True)
class Point:
    """
    Точка эллиптической кривой.

    x = None, y = None означает бесконечно удаленную точку.
    """

    x: Optional[int]
    y: Optional[int]

    @property
    def is_infinity(self) -> bool:
        return self.x is None and self.y is None


class EllipticCurve:
    """
    Эллиптическая кривая в короткой форме Вейерштрасса:

    y^2 = x^3 + ax + b (mod p)
    """

    def __init__(self, p: int, a: int, b: int,
                 gx: int, gy: int, q: int):

        self.field = Field(p)
        self.p = p
        self.a = a % p
        self.b = b % p
        self.q = q

        # Проверка отсутствия особых точек кривой.
        discriminant = (
            4 * pow(self.a, 3, p) +
            27 * pow(self.b, 2, p)
        ) % p

        if discriminant == 0:
            raise ValueError("Кривая является вырожденной")

        self.G = Point(gx % p, gy % p)

        if not self.is_on_curve(self.G):
            raise ValueError("Базовая точка G не принадлежит кривой")

        if q <= 0:
            raise ValueError("Порядок подгруппы q должен быть положительным")

    def infinity(self) -> Point:
        """Возвращает бесконечно удаленную точку."""
        return Point(None, None)

    def is_on_curve(self, P: Point) -> bool:
        """Проверяет принадлежность точки эллиптической кривой."""

        if P.is_infinity:
            return True

        if P.x is None or P.y is None:
            return False

        x = P.x % self.p
        y = P.y % self.p

        left = pow(y, 2, self.p)

        right = (
            pow(x, 3, self.p) +
            self.a * x +
            self.b
        ) % self.p

        return left == right

    def negate(self, P: Point) -> Point:
        """Вычисляет противоположную точку -P."""

        if P.is_infinity:
            return P

        return Point(
            P.x,
            (-P.y) % self.p
        )

    def double(self, P: Point) -> Point:
        """Удвоение точки: R = 2P."""

        if not self.is_on_curve(P):
            raise ValueError("Точка не принадлежит кривой")

        if P.is_infinity:
            return P

        x1 = P.x
        y1 = P.y

        # Если y = 0, касательная вертикальна.
        if y1 == 0:
            return self.infinity()

        # s = (3*x1^2 + a) / (2*y1) mod p
        numerator = (
            3 * x1 * x1 + self.a
        ) % self.p

        denominator = (2 * y1) % self.p

        s = self.field.mul(
            numerator,
            self.field.inverse(denominator)
        )

        # x3 = s^2 - 2*x1 mod p
        x3 = (
            s * s - 2 * x1
        ) % self.p

        # y3 = s*(x1-x3)-y1 mod p
        y3 = (
            s * (x1 - x3) - y1
        ) % self.p

        return Point(x3, y3)

    def add(self, P: Point, Q: Point) -> Point:
        """Сложение двух точек: R = P + Q."""

        if not self.is_on_curve(P):
            raise ValueError("Первая точка не принадлежит кривой")

        if not self.is_on_curve(Q):
            raise ValueError("Вторая точка не принадлежит кривой")

        # P + O = P
        if P.is_infinity:
            return Q

        # O + Q = Q
        if Q.is_infinity:
            return P

        x1, y1 = P.x, P.y
        x2, y2 = Q.x, Q.y

        # Если точки совпадают, выполняем удвоение.
        if P == Q:
            return self.double(P)

        # Вертикальная прямая: результат O.
        if x1 == x2:
            return self.infinity()

        # s = (y2-y1)/(x2-x1) mod p
        numerator = (y2 - y1) % self.p
        denominator = (x2 - x1) % self.p

        s = self.field.mul(
            numerator,
            self.field.inverse(denominator)
        )

        # x3 = s^2 - x1 - x2 mod p
        x3 = (
            s * s - x1 - x2
        ) % self.p

        # y3 = s*(x1-x3)-y1 mod p
        y3 = (
            s * (x1 - x3) - y1
        ) % self.p

        return Point(x3, y3)

    def multiply(self, k: int, P: Point) -> Point:
        """
        Скалярное умножение Double-and-Add:

        R = k * P
        """

        if not self.is_on_curve(P):
            raise ValueError("Точка не принадлежит кривой")

        if k < 0:
            return self.multiply(-k, self.negate(P))

        result = self.infinity()
        current = P

        while k > 0:

            if k & 1:
                result = self.add(result, current)

            current = self.double(current)
            k >>= 1

        return result
