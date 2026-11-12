class Field:
    def __init__(self, p: int):
        if p <= 2:
            raise ValueError("Модуль p должен быть простым числом больше 2")
        self.p = p

    def normalize(self, a: int) -> int:
        return a % self.p

    def add(self, a: int, b: int) -> int:
        return (a + b) % self.p

    def sub(self, a: int, b: int) -> int:
        return (a - b) % self.p

    def mul(self, a: int, b: int) -> int:
        return (a * b) % self.p

    def power(self, a: int, n: int) -> int:
        if n < 0:
            raise ValueError("Отрицательная степень не поддерживается")
        return pow(a, n, self.p)

    def inverse(self, a: int) -> int:
        """
        Модульная инверсия по малой теореме Ферма.

        a^(-1) = a^(p-2) mod p
        """

        a %= self.p

        if a == 0:
            raise ZeroDivisionError(
                "Нельзя найти обратный элемент для нуля"
            )

        return pow(a, self.p - 2, self.p)

    def div(self, a: int, b: int) -> int:
          return self.mul(a, self.inverse(b))

    def __repr__(self):
        return f"Field(GF({self.p}))"
