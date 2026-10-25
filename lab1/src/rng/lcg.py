"""
Линейный конгруэнтный генератор (ЛКГ), см. методичку §4.1, формула (1):

    x_{t+1} = (a * x_t + c) mod N

Используется как "простой" генератор G1 (алфавит {0..N-1}) и
G2 (алфавит {0..K-1}) для комбинирования методом Макларена-Марсальи (§4.8).
"""
from __future__ import annotations


class LCG:
    def __init__(self, a: int, c: int, N: int, x0: int):
        if N <= 0:
            raise ValueError("N должно быть положительным")
        self.a = a
        self.c = c
        self.N = N
        self.x0 = x0 % N
        self._x = self.x0

    @property
    def state(self) -> int:
        """Текущее значение x_t (без продвижения генератора)."""
        return self._x

    def reset(self) -> None:
        """Вернуть генератор в начальное состояние x0."""
        self._x = self.x0

    def next(self) -> int:
        """Сделать один шаг рекурренты и вернуть новое значение x_{t+1}."""
        self._x = (self.a * self._x + self.c) % self.N
        return self._x

    def sequence(self, length: int) -> list[int]:
        """Сгенерировать последовательность длины length, начиная с x0 (со сбросом)."""
        self.reset()
        return [self.next() for _ in range(length)]

    def full_period(self, max_len: int | None = None) -> tuple[int | None, int | None]:
        """
        Определить период и предпериод последовательности, начиная с x0.
        Возвращает (период T, предпериод tau).
        Если период не найден в пределах max_len шагов - (None, None).
        """
        self.reset()
        seen = {self.x0: 0}
        limit = max_len or (self.N + 5)
        t = 0
        x = self.x0
        while t < limit:
            x = (self.a * x + self.c) % self.N
            t += 1
            if x in seen:
                tau = seen[x]
                return t - tau, tau
            seen[x] = t
        return None, None

    def satisfies_max_period_condition(self) -> bool:
        """
        Проверка достаточного условия максимального периода T_max = N
        для смешанного конгруэнтного генератора (§4.1, свойство 4):
          a) НОД(c, N) = 1
          b) (a - 1) кратно каждому простому делителю N
          c) (a - 1) кратно 4, если N кратно 4
        Не проверяет условия для чисто мультипликативного случая (c=0), см. свойство 5-6.
        """
        from math import gcd

        if gcd(self.c, self.N) != 1:
            return False

        b = self.a - 1
        n = self.N
        p = 2
        while p * p <= n:
            if n % p == 0:
                if b % p != 0:
                    return False
                while n % p == 0:
                    n //= p
            p += 1
        if n > 1:  # оставшийся простой множитель > sqrt(N)
            if b % n != 0:
                return False

        if self.N % 4 == 0 and b % 4 != 0:
            return False

        return True
