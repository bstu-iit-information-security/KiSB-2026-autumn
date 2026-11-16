import random
from math import gcd


# 1. Вероятностный тест Миллера-Рабина
def is_prime_miller_rabin(n: int, k: int = 5) -> bool:
    if n <= 1: return False
    if n <= 3: return True
    if n % 2 == 0: return False

    # Представляем n-1 в виде d * 2^s
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for _ in range(k):
        a = random.randint(2, n - 2)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue

        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False  # Составное
    return True  # Вероятно простое


# 2. Решето Эратосфена для фильтрации
def sieve_of_eratosthenes(limit: int) -> list[int]:
    is_prime = [True] * (limit + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(limit ** 0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, limit + 1, i):
                is_prime[j] = False
    return [i for i in range(2, limit + 1) if is_prime[i]]


# 3. Генератор случайного числа из битов
def generate_random_bits(gen, p: int) -> list[int]:
    return gen.next_bits(p)


def bits_to_int(bits: list[int]) -> int:
    val = 0
    for bit in bits:
        val = (val << 1) | bit
    return val