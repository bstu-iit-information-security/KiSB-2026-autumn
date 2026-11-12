"""
Модуль вероятностного теста Соловея — Штрассена (Solovay — Strassen test).
Используется для сравнительного анализа и верификации.
"""

import math
import random
from typing import Optional


def jacobi_symbol(a: int, n: int) -> int:
    """
    Вычисление символа Якоби (a / n) для нечетного n > 0.
    """
    if n <= 0 or n % 2 == 0:
        raise ValueError("Модуль n должен быть положительным нечетным числом")

    a = a % n
    t = 1
    while a != 0:
        while a % 2 == 0:
            a //= 2
            r = n % 8
            if r == 3 or r == 5:
                t = -t
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            t = -t
        a = a % n
    return t if n == 1 else 0


def solovay_strassen_test(n: int, k: int = 15, rng: Optional[random.Random] = None) -> bool:
    """
    Вероятностный тест Соловея — Штрассена:
    Проверяет, выполняется ли критерий Эйлера a^((n - 1) / 2) = (a / n) (mod n).
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    if rng is None:
        rng = random.Random()

    exp = (n - 1) // 2

    for _ in range(k):
        a = rng.randint(2, n - 2)
        j = jacobi_symbol(a, n)
        if j == 0:
            return False

        # Символ Якоби по модулю n: если j == -1, это n - 1
        j_mod = (j + n) % n
        t = pow(a, exp, n)

        if t != j_mod:
            return False

    return True

