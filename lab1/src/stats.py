from math import sqrt
from collections import Counter


def freq_test(bits):
    """Частотный тест (доля единиц).
    Возвращает словарь со статистикой."""
    n = len(bits)
    ones = sum(bits)
    zeros = n - ones
    p_hat = ones / n

    # z-статистика
    # Для хорошего генератора |z| должно быть меньше 1.96 (при alpha=0.05)
    z = abs(ones - n / 2) / sqrt(n / 4)

    return {
        "n": n,
        "ones": ones,
        "zeros": zeros,
        "p_hat": round(p_hat, 4),
        "z": round(z, 3),
        "uniform": z < 1.96
    }


def chi_square_test(seq, alphabet_size=2):
    """Вычисляет статистику Хи-квадрат для проверки равномерности.
    Для битов alphabet_size=2."""
    cnt = Counter(seq)
    n = len(seq)
    expected = n / alphabet_size

    chi2 = 0
    for k in range(alphabet_size):
        observed = cnt.get(k, 0)
        chi2 += (observed - expected) ** 2 / expected

    # Критическое значение для df = alphabet_size - 1 = 1 и alpha=0.05 равно 3.841
    # Если chi2 < 3.841, гипотеза о равномерности НЕ отвергается
    return round(chi2, 3)