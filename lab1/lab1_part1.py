# Лабораторная работа №1. Часть 1. Вариант 7 (LFSR)
# ИСПРАВЛЕННАЯ И РАБОЧАЯ ВЕРСИЯ

def find_period(taps, n=6):
    """Ищет период последовательности (до 2^n - 1)."""
    state = [1] + [0] * (n - 1)  # Начальное состояние 100000
    initial_state = state[:]
    period = 0
    max_period = 2 ** n - 1

    while True:
        # Вычисляем бит обратной связи (XOR всех отводов)
        feedback = 0
        for tap in taps:
            feedback ^= state[tap]

        # Сдвигаем регистр вправо
        state = [feedback] + state[:-1]
        period += 1

        # Если состояние вернулось к начальному — мы нашли период
        if state == initial_state:
            return period
        # Если прошли максимальный период, а состояния не было — он не примитивный
        if period > max_period:
            return -1


def frequency_test(taps, n=6, steps=10000):
    """Генерирует последовательность и считает долю единиц."""
    state = [1] + [0] * (n - 1)
    ones = 0
    for _ in range(steps):
        ones += state[-1]  # Выходной бит - самый правый
        feedback = 0
        for tap in taps:
            feedback ^= state[tap]
        state = [feedback] + state[:-1]

    return ones / steps


print("--- Анализ LFSR (Вариант 7) ---")

# --- Правильные отводы (taps) для каждого многочлена: ---
# 1. f(x) = x^6 + x^3 + 1  -> отводы от x^6 и x^3
poly1_taps = [0, 3]
# 2. f(x) = x^6 + x^2 + x + 1 -> отводы от x^6, x^2, x^1
poly2_taps = [0, 4, 5]
# 3. f(x) = x^6 + x + 1 -> отводы от x^6 и x^1 (ЭТОТ ПРИМИТИВНЫЙ)
poly3_taps = [0, 5]

polys = [
    (poly1_taps, "f(x) = x^6 + x^3 + 1"),
    (poly2_taps, "f(x) = x^6 + x^2 + x + 1"),
    (poly3_taps, "f(x) = x^6 + x + 1")
]

for taps, name in polys:
    period = find_period(taps)
    prob = frequency_test(taps)

    print(f"\nМногочлен: {name}")
    if period == 63:
        print(f"  [V] ПРИМИТИВНЫЙ. Период = {period} (максимальный)")
    else:
        print(f"  [X] НЕ ПРИМИТИВНЫЙ. Период = {period}")
    print(f"  Доля единиц на 10000 битах: {prob:.4f}")