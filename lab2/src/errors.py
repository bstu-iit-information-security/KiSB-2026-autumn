# errors.py
"""
Генерация ошибок заданной кратности в кодовом слове.
"""

import random


def inject_errors(Xn, i, rng=None):
    """
    Инвертировать i случайно выбранных бит в Xn.
    Xn: список бит (кодовое слово).
    i: кратность ошибки (сколько бит испортить).
    rng: генератор случайных чисел (для воспроизводимости).
    Возвращает (Yn, sorted_positions).
    """
    if rng is None:
        rng = random

    n = len(Xn)
    if i < 0 or i > n:
        raise ValueError(f"Кратность ошибки i={i} выходит за пределы [0, {n}]")

    # Выбираем i уникальных позиций для инверсии
    positions = rng.sample(range(n), i)
    positions.sort()

    Yn = list(Xn)
    for p in positions:
        Yn[p] ^= 1  # инверсия бита

    return Yn, positions


# ---------- Самопроверка ----------
if __name__ == "__main__":
    Xn = [0, 1, 0, 1, 1, 0, 0, 1]
    print("Исходное Xn:", "".join(map(str, Xn)))

    # Вносим 2 ошибки
    rng = random.Random(42)  # фиксируем зерно для повторяемости
    Yn, pos = inject_errors(Xn, 2, rng)

    print(f"\nКратность i=2, позиции: {pos}")
    print("Испорченное Yn:", "".join(map(str, Yn)))

    # Проверка, что изменилось ровно 2 бита
    diff = [i for i in range(len(Xn)) if Xn[i] != Yn[i]]
    assert diff == pos, "Ошибка: изменены не те биты!"
    print(f"Проверка: изменены ровно биты {diff} — OK")

    # Вносим 1 ошибку
    Yn1, pos1 = inject_errors(Xn, 1, rng)
    print(f"\nКратность i=1, позиция: {pos1}")
    print("Испорченное Yn1:", "".join(map(str, Yn1)))

    # Вносим 0 ошибок
    Yn0, pos0 = inject_errors(Xn, 0, rng)
    assert Yn0 == Xn and len(pos0) == 0
    print("\nКратность i=0: слово не изменилось — OK")

    print("\nВсе тесты errors пройдены.")