import secrets

from curve import Curve, INFINITY, Point


class FixedWindow:

    def __init__(self, curve: Curve, point: Point, width=4):
        if width != 4:
            raise ValueError("В этой реализации окно равно четырём битам")
        self.curve = curve
        self.width = width
        self.table_size = 1 << width
        self.coordinate_size = curve.coordinate_size
        self.point_size = 2 * self.coordinate_size
        self.table = bytearray(self.table_size * self.point_size)

        current = INFINITY
        for index in range(self.table_size):
            self._store(index, current)
            current = curve.add(current, point)

    def _store(self, index, point):
        offset = index * self.point_size
        if point.is_infinity:
            encoded = bytes(self.point_size)
        else:
            encoded = (point.x.to_bytes(self.coordinate_size, "little") +
                       point.y.to_bytes(self.coordinate_size, "little"))
        self.table[offset:offset + self.point_size] = encoded

    def select(self, digit):
        selected = bytearray(self.point_size)
        for index in range(self.table_size):
            mask = -int(index == digit) & 0xFF
            offset = index * self.point_size
            for position in range(self.point_size):
                selected[position] |= self.table[offset + position] & mask
        return self.curve.decode_point(bytes(selected))

    def multiply(self, scalar):
        if not 0 <= scalar < self.curve.order:
            raise ValueError("Скаляр вне диапазона")
        windows = (self.curve.order.bit_length() + self.width - 1) // self.width
        result = INFINITY
        for window in range(windows - 1, -1, -1):
            for _ in range(self.width):
                result = self.curve.double(result)
            digit = (scalar >> (window * self.width)) & (self.table_size - 1)
            result = self.curve.add(result, self.select(digit))
        return result


class PointBlinding:

    def __init__(self, curve: Curve):
        self.curve = curve

    def _random_point(self):
        random_scalar = secrets.randbelow(self.curve.order - 1) + 1
        return self.curve.multiply_classic(random_scalar, self.curve.generator)

    def secure_multiply(self, scalar, point):
        if not 0 <= scalar < self.curve.order:
            raise ValueError("Скаляр вне диапазона")
        if point.is_infinity:
            return INFINITY

        blinded = INFINITY
        while blinded.is_infinity:
            random_point = self._random_point()
            blinded = self.curve.add(point, random_point)

        left = FixedWindow(self.curve, blinded).multiply(scalar)
        right = FixedWindow(self.curve, random_point).multiply(scalar)
        return self.curve.add(left, self.curve.negate(right))
