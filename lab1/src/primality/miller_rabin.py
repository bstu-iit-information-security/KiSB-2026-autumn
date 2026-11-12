"""
Модуль вероятностного теста Рабина — Миллера (Miller — Rabin test).
"""

import random
from typing import Optional


def miller_rabin_test(n: int, k: int = 15, rng: Optional[random.Random] = None) -> bool:
    """
    Вероятностный тест Рабина — Миллера:
    n - 1 = 2^s * t, где t нечетно.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    if rng is None:
        rng = random.Random()

    # Разложение n - 1 = 2^s * t
    s = 0
    t = n - 1
    while t % 2 == 0:
        s += 1
        t //= 2

    for _ in range(k):
        a = rng.randint(2, n - 2)
        x = pow(a, t, n)
        if x == 1 or x == n - 1:
            continue
        composite = True
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                composite = False
                break
        if composite:
            return False

    return True

