"""
Тест Соловея-Штрассена (§6.5, теорема 2) - целевой тест простоты для варианта 1.

Один раунд:
  1. Выбрать случайное a из [2, n-2] (или [1, n-1], здесь [2, n-2] чтобы
     избежать тривиальных a=1,n-1).
  2. НОД(a, n) != 1  => n составное.
  3. a^((n-1)/2) mod n сравнить с символом Якоби (a/n) mod n.
     Несовпадение => n составное.
  4. Совпадение => "не известно" (n простое либо псевдопростое по Эйлеру по этому a).

После k независимых раундов вероятность необнаруженного составного <= 2^-k.
"""
from __future__ import annotations

import random
from math import gcd

from .jacobi import jacobi_symbol


def solovay_strassen_round(n: int, rng: random.Random | None = None) -> bool:
    """Один раунд теста. True - "вероятно простое" по этому основанию, False - точно составное."""
    rng = rng or random
    if n == 2:
        return True
    if n < 2 or n % 2 == 0:
        return False
    if n == 3:
        return True

    a = rng.randrange(2, n - 1)
    if gcd(a, n) != 1:
        return False

    x = jacobi_symbol(a, n)
    if x == 0:
        return False

    left = pow(a, (n - 1) // 2, n)
    right = x % n
    return left == right


def is_probable_prime(n: int, rounds: int = 5, rng: random.Random | None = None) -> bool:
    """Тест Соловея-Штрассена за k=rounds раундов. Вероятность ошибки <= 2^-rounds."""
    if n < 2:
        return False
    for _ in range(rounds):
        if not solovay_strassen_round(n, rng):
            return False
    return True
