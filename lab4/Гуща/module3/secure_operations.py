
import secrets


class SecureOperations:
    def __init__(self, curve):
        self.curve = curve

    @staticmethod
    def conditional_select(a: int, b: int, bit: int) -> int:
        mask = -bit

        return (a & ~mask) | (b & mask)

    def secure_inverse(self, value: int) -> int:
        p = self.curve.p
        value %= p

        if value == 0:
            raise ZeroDivisionError("Обратного элемента не существует")

        exponent = p - 2
        result = 1
        base = value

        bits = p.bit_length()

        for i in range(bits - 1, -1, -1):

            squared = (result * result) % p
            multiplied = (squared * base) % p

            bit = (exponent >> i) & 1

            result = self.conditional_select(
                squared,
                multiplied,
                bit
            )

        return result

    def secure_multiply(self, scalar: int, point):
        if scalar < 0:
            raise ValueError("Скаляр должен быть неотрицательным")

        if not self.curve.is_on_curve(point):
            raise ValueError("Точка не принадлежит кривой")

        R0 = self.curve.infinity()
        R1 = point

        bits = self.curve.q.bit_length()

        if scalar >= (1 << bits):
            raise ValueError("Скаляр превышает допустимую длину")

        for i in range(bits - 1, -1, -1):

            bit = (scalar >> i) & 1

            if bit == 0:
                R1 = self.curve.add(R0, R1)
                R0 = self.curve.double(R0)

            else:
                R0 = self.curve.add(R0, R1)
                R1 = self.curve.double(R1)

        return R0

    def blind_scalar(self, scalar: int) -> int:

        if not 0 <= scalar < self.curve.q:
            raise ValueError("Скаляр должен принадлежать [0, q-1]")

        random_value = secrets.randbits(64)

        return scalar + random_value * self.curve.q

    def secure_multiply_blinded(self, scalar: int, point):
        blinded = self.blind_scalar(scalar)
        return self.curve.multiply(blinded, point)
