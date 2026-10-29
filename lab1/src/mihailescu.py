import random
import time
from math import gcd
from primality import SMALL_PRIMES, trial_division, miller_rabin, factor_small


def build_F(e_bits, max_attempts=200):
    """Строит число F с известной факторизацией (произведение малых простых).
    Размер F примерно e_bits бит."""
    for _ in range(max_attempts):
        F = 1
        factors = {}
        # Набираем произведение случайных малых простых
        while F.bit_length() < e_bits:
            p = random.choice(SMALL_PRIMES[:40])
            F *= p
            factors[p] = factors.get(p, 0) + 1
        # Проверяем, что не перелетели сильно за диапазон
        if F.bit_length() <= e_bits + 1:
            return F, factors
    raise RuntimeError("Не удалось построить F")


def pocklington_prove(n, known_factors):
    """Доказательство простоты n по Поклингтону.
    n-1 = 2 * t * F. known_factors — все известные простые делители n-1."""
    for q in known_factors:
        found = False
        # Ищем "свидетеля" (a)
        for _ in range(100):
            a = random.randrange(2, n - 1)
            if pow(a, n - 1, n) != 1:
                continue
            if gcd(pow(a, (n - 1) // q, n) - 1, n) == 1:
                found = True
                break
        if not found:
            return False  # не удалось доказать для этого q
    return True


def generate_prime_mihailescu(m_bits, e=0.5, s=200):
    """Генерация доказуемо простого числа по методу Михалеску.

    Параметры:
      m_bits — требуемая битовая длина числа n
      e      — параметр (для варианта 10: 0.5)
      s      — сколько кандидатов перебрать за раз
    """
    t0 = time.time()

    # ШАГ 2: F из диапазона [2^(e*m), 2^(e*m+1)]
    e_bits = max(8, int(e * m_bits))
    F, F_factors = build_F(e_bits)

    # ШАГ 3: t ∈ (2^(m-1)/(2F), 2^m/(2F))
    lo = (1 << (m_bits - 1)) // (2 * F) + 1
    hi = (1 << m_bits) // (2 * F)

    if hi <= lo:
        # F получилось слишком большим, рекурсивно пробуем еще раз
        return generate_prime_mihailescu(m_bits, e, s)

    attempts = 0
    # ШАГ 4: перебор кандидатов
    for _ in range(s):
        attempts += 1
        t = random.randint(lo, max(lo, hi - 1))
        n = 2 * t * F + 1  # Формула Михалеску

        # 4.1: Пробные деления (быстрый отсев)
        if not trial_division(n):
            continue

        # 4.2: Фильтр Рабина-Миллера (если он не прошел, дальше смысла нет)
        if not miller_rabin(n, k=5):
            continue

        # 4.3: Доказательство простоты (Поклингтон)
        # n-1 = 2 * t * F. Нам нужны все простые делители (t и F)
        known = set(F_factors.keys())
        t_f = factor_small(t)
        known |= set(t_f.keys())

        if pocklington_prove(n, known):
            return {
                'n': n, 'F': F, 't': t, 'attempts': attempts,
                'time': time.time() - t0, 'proven': True,
            }

    return {
        'n': None, 'F': F, 't': None, 'attempts': attempts,
        'time': time.time() - t0, 'proven': False,
    }