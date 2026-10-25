"""
Символ Якоби (a/n) для нечётного n > 0 - обобщение символа Лежандра,
необходим для теста Соловея-Штрассена (§6.5, сравнение (2)).

Реализация без факторизации n, через закон квадратичной взаимности
(аналогично расширенному алгоритму Евклида), сложность O(log n).
"""
from __future__ import annotations


def jacobi_symbol(a: int, n: int) -> int:
    if n <= 0 or n % 2 == 0:
        raise ValueError("n должно быть положительным нечётным числом")

    a = a % n
    result = 1
    while a != 0:
        while a % 2 == 0:
            a //= 2
            r = n % 8
            if r in (3, 5):
                result = -result
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            result = -result
        a = a % n

    return result if n == 1 else 0
