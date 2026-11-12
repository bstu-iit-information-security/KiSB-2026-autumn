# Лабораторная работа №1. Часть 2. Вариант 7 (Метод Михалеску)
import random


def miller_rabin(n, k=5):
    """Тест Рабина-Миллера для проверки простоты"""
    if n < 2: return False
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]:
        if n % p == 0: return n == p
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1: continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1: break
        else:
            return False
    return True


def generate_michalescu_prime(bits, e=1 / 3):
    """Генерация простого числа методом Михалеску"""
    if bits < 20:
        while True:
            p = random.getrandbits(bits) | (1 << (bits - 1)) | 1
            if miller_rabin(p): return p

    # Строим F рекурсивно (примерно 1/3 от длины)
    f_bits = int(bits * e)
    F = generate_michalescu_prime(f_bits, e)

    # Ищем простое в арифметической прогрессии
    while True:
        # t * 2F + 1
        t = random.getrandbits(bits - f_bits) | 1
        n0 = t * 2 * F + 1
        if n0.bit_length() != bits:
            continue

        for i in range(1000):
            p = n0 + i * 2 * F
            if miller_rabin(p):
                return p


if __name__ == "__main__":
    print("--- Генерация простого числа (Метод Михалеску, e=1/3) ---")
    bits = 64  # Генерируем 64-битное число
    prime = generate_michalescu_prime(bits)

    print(f"Сгенерировано простое число ({bits} бит):")
    print(prime)

    print(f"\nПроверка тестом Рабина-Миллера: {'Простое' if miller_rabin(prime) else 'Составное'}")