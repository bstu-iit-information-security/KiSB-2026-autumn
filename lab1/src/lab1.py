import math
import time
from typing import List, Tuple

# =====================================================================
# ЭТАП 1: ГЕНЕРАТОР ЭЙХЕНАУЭРА - ЛЕНА С ОБРАЩЕНИЕМ (ICG)
# =====================================================================

def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """Расширенный алгоритм Евклида: возвращает (gcd, x, y), где a*x + b*y = gcd."""
    if b == 0:
        return a, 1, 0
    g, x1, y1 = extended_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

def mod_inverse(x: int, n: int) -> int:
    """Вычисление обратного элемента x^(-1) mod n. Возвращает 0, если gcd(x, n) != 1."""
    if x <= 0:
        return 0
    g, inv, _ = extended_gcd(x, n)
    if g != 1:
        return 0
    return (inv % n + n) % n

class EichenauerLehnGenerator:
    """Генератор Эйхенауэра - Лена с обращением."""
    def __init__(self, a: int, c: int, N: int, x0: int):
        self.a = a
        self.c = c
        self.N = N
        self.state = x0 % N

    def next(self) -> int:
        cur = self.state
        if cur >= 1:
            inv = mod_inverse(cur, self.N)
            if inv != 0:
                self.state = (self.a * inv + self.c) % self.N
            else:
                self.state = self.c % self.N
        else:
            self.state = self.c % self.N
        return cur

    def generate_sequence(self, length: int) -> List[int]:
        return [self.next() for _ in range(length)]

    def measure_period(self) -> int:
        """Быстрый и корректный подсчет длины периода через запоминание состояний."""
        saved_state = self.state
        seen = {}
        step = 0
        while self.state not in seen:
            seen[self.state] = step
            self.next()
            step += 1
        period = step - seen[self.state]
        self.state = saved_state
        return period

    def generate_bits(self, count: int) -> int:
        """Генерация p случайных бит для формирования числа."""
        bits = 0
        for _ in range(count):
            val = self.next()
            bit = (val ^ (val >> 1) ^ (val >> 2)) & 1
            bits = (bits << 1) | bit
        return bits

def chi_squared_uniformity_test(sequence: List[int], N: int) -> Tuple[float, float, bool]:
    """Проверка гипотезы равномерности по критерию хи-квадрат Пирсона."""
    m = len(sequence)
    expected = m / N
    freq = [0] * N
    for x in sequence:
        if 0 <= x < N:
            freq[x] += 1

    chi2 = sum((obs - expected) ** 2 / expected for obs in freq)
    
    # Аппроксимация Вилсона-Хилферти для критического значения (alpha = 0.05)
    df = N - 1
    if df > 0:
        z = 1.644853  # квантиль для уровня значимости 5%
        crit = df * ((1 - 2 / (9 * df) + z * math.sqrt(2 / (9 * df))) ** 3)
    else:
        crit = 0.0
    return chi2, crit, chi2 <= crit

# =====================================================================
# ЭТАП 2: ПОЛИНОМИАЛЬНЫЙ ТЕСТ ПРОСТОТЫ (AKS) И СИТО
# =====================================================================

SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
    239, 241, 251
]

def is_perfect_power(n: int) -> bool:
    """Шаг 1 теста: проверка, является ли n точной степенью a^b (b >= 2)."""
    if n <= 3:
        return False
    max_b = int(math.log2(n)) + 1
    for b in range(2, max_b + 1):
        root = int(round(n ** (1.0 / b)))
        if root ** b == n:
            return True
    return False

def poly_mul_mod(p1: List[int], p2: List[int], r: int, n: int) -> List[int]:
    """Умножение двух полиномов в фактор-кольце (Z/nZ)[x] / (x^r - 1)."""
    res = [0] * r
    for i, c1 in enumerate(p1):
        if c1 == 0:
            continue
        for j, c2 in enumerate(p2):
            if c2 == 0:
                continue
            idx = (i + j) % r
            res[idx] = (res[idx] + c1 * c2) % n
    return res

def poly_pow_mod(poly: List[int], exp: int, r: int, n: int) -> List[int]:
    """Быстрое бинарное возведение многочлена в степень exp mod (x^r - 1, n)."""
    res = [0] * r
    res[0] = 1
    base = poly[:]
    while exp > 0:
        if exp & 1:
            res = poly_mul_mod(res, base, r, n)
        base = poly_mul_mod(base, base, r, n)
        exp >>= 1
    return res

def aks_polynomial_primality_test(n: int) -> bool:
    """Полиномиальный тест простоты AKS (п. 6.8 методических указаний)."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    # Шаг 1: Проверка на степень
    if is_perfect_power(n):
        return False

    # Шаг 2: Поиск наименьшего r
    log2n = math.log2(n)
    max_k = max(1, int(log2n ** 2))
    
    r = 2
    while r < n:
        g = math.gcd(r, n)
        if 1 < g < n:
            return False
        if g == 1:
            cur = pow(n, 1, r)
            k = 1
            while cur != 1 and k <= max_k:
                cur = (cur * n) % r
                k += 1
            if cur != 1:
                break
        r += 1

    if r >= n:
        return True

    # Шаг 3: Проверка полиномиальных сравнений
    max_a = max(1, int(math.sqrt(r) * log2n))
    max_a = min(max_a, n - 1)

    for a in range(1, max_a + 1):
        p_base = [0] * r
        p_base[1 % r] = 1
        p_base[0] = (-a) % n
        lhs = poly_pow_mod(p_base, n, r, n)

        rhs = [0] * r
        rhs[n % r] = (rhs[n % r] + 1) % n
        rhs[0] = (rhs[0] - a) % n

        if lhs != rhs:
            return False

    return True

def trial_division_filter(n: int) -> bool:
    """Предварительное просеивание через малые простые числа до 256."""
    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
    return True

def generate_prime_candidate(
    icg: EichenauerLehnGenerator, bit_length: int
) -> Tuple[int, int, float]:
  start_time = time.time()
  screened_out = 0

  # 1. Стартовый кандидат из генератора
  val = icg.generate_bits(bit_length)
  val |= (1 << (bit_length - 1)) | 1  # нечетный и нужной битности

  while True:
    # 2. Просеивание ситом малых простых делителей
    if not trial_division_filter(val):
      screened_out += 1
      val += 2
      continue

    # 3. Финальный полиномиальный тест AKS
    if aks_polynomial_primality_test(val):
      elapsed = time.time() - start_time
      return val, screened_out, elapsed
    else:
      screened_out += 1
      val += 2

# =====================================================================
# ТОЧКА ВХОДА (ТЕСТИРОВАНИЕ)
# =====================================================================

if __name__ == "__main__":
    print("=" * 75)
    print("ЛАБОРАТОРНАЯ РАБОТА №1 (ВАРИАНТ 3)")
    print("=" * 75)

    # 1. Тестирование генератора Эйхенауэра - Лена
    print("\n--- ЭТАП 1: Анализ генератора Эйхенауэра - Лена с обращением ---")
    configs = [
        (1, 2, 16, 3, "N=16 (2^4): a=1, c=2 (Теоретический максимум T=8)"),
        (3, 2, 16, 3, "N=16 (2^4): a=3, c=2 (Нарушено условие a = 1 mod 4)"),
        (1, 2, 20, 3, "N=20 (по варианту №3): a=1, c=2, x0=3"),
        (3, 4, 20, 1, "N=20 (по варианту №3): a=3, c=4, x0=1"),
    ]

    for a, c, N, x0, desc in configs:
        gen = EichenauerLehnGenerator(a, c, N, x0)
        period = gen.measure_period()
        seq = gen.generate_sequence(1000)
        chi2, crit, is_uniform = chi_squared_uniformity_test(seq, N)
        print(f"\nКонфигурация: {desc}")
        print(f" -> Первые 16 элементов : {seq[:16]}")
        print(f" -> Период T            : {period}")
        print(f" -> Критерий хи-квадрат : {chi2:.2f} (критическое: {crit:.2f}) -> Равномерно: {is_uniform}")

    # 2. Тестирование конвейера генерации простых чисел и теста AKS
    print("\n\n--- ЭТАП 2: Генерация простых чисел полиномиальным тестом (AKS) ---")
    gen_main = EichenauerLehnGenerator(a=1, c=2, N=64, x0=7)

    test_bit_sizes = [10, 12, 14, 16]
    print(f"{'Битность':<10} | {'Простое число':<14} | {'HEX-вид':<14} | {'Отсеяно':<10} | {'Время (с)':<10}")
    print("-" * 75)
    for bits in test_bit_sizes:
        prime, screened, el_time = generate_prime_candidate(gen_main, bits)
        print(f"{bits:<10} | {prime:<14} | {hex(prime):<14} | {screened:<10} | {el_time:<10.4f}")