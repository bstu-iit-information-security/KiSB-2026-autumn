import random
import math
from math import gcd, isqrt, log2, ceil
from collections import Counter


# ЧАСТЬ 1.

class QuadraticCongruentialGenerator:
    def __init__(self, a, b, c, x0, N=10):
        if N <= 0:
            raise ValueError("N должно быть > 0")
        self.a = a % N
        self.b = b % N
        self.c = c % N
        self.x0 = x0 % N
        self.N = N
        self.reset()

    def reset(self):
        self.x = self.x0
        self._history = [self.x]

    def next(self):
        # Один шаг генератора по формуле
        self.x = (self.a * self.x * self.x + self.b * self.x + self.c) % self.N
        self._history.append(self.x)
        return self.x

    def generate(self, length):
        # Генерация последовательности заданной длины
        self.reset()
        seq = [self.x]
        for _ in range(length - 1):
            seq.append(self.next())
        return seq

    def find_period(self):
        seen = {}
        self.reset()
        x = self.x
        i = 0
        while x not in seen:
            seen[x] = i
            x = self.next()
            i += 1
        tau = seen[x]
        T = i - tau
        return tau, T


def find_best_params(N=10, c=0):
    best = (None, None, None, -1, -1)
    for a in range(1, N):
        for b in range(N):
            for x0 in range(N):
                gen = QuadraticCongruentialGenerator(a, b, c, x0, N)
                tau, T = gen.find_period()
                if T > best[3]:
                    best = (a, b, x0, T, tau)
    return best


# Статистические тесты

def chi_square_test(seq, N=10):
    # Критерий хи-квадрат: проверка равномерности распределения
    n = len(seq)
    observed = Counter(seq)
    expected = n / N
    chi2 = sum((observed.get(k, 0) - expected) ** 2 / expected for k in range(N))
    df = N - 1
    critical = {
        1: 3.841, 2: 5.991, 3: 7.815, 4: 9.488, 5: 11.070,
        6: 12.592, 7: 14.067, 8: 15.507, 9: 16.919,
        10: 18.307
    }.get(df, 16.919)
    return chi2, df, critical, chi2 < critical


def frequency_test(seq, N=10):
    # Относительные частоты каждого значения алфавита
    n = len(seq)
    freq = Counter(seq)
    return {k: freq.get(k, 0) / n for k in range(N)}


def runs_test(seq, N=10):
    # Тест серий: число серий подряд идущих одинаковых значений
    n = len(seq)
    if n < 2:
        return 0, 0
    runs = 1
    for i in range(1, n):
        if seq[i] != seq[i - 1]:
            runs += 1
    expected = n * (1 - 1 / N)
    return runs, expected


def serial_correlation_test(seq, lag=1):
    # Выборочная автокорреляция с заданным лагом
    n = len(seq)
    if n <= lag:
        return 0.0
    mean = sum(seq) / n
    num = sum((seq[i] - mean) * (seq[i + lag] - mean) for i in range(n - lag))
    den = sum((x - mean) ** 2 for x in seq)
    return num / den if den != 0 else 0.0


def demo_qcg():
    print("\nЧасть 1")
    print("Квадратичный конгруэнтный генератор (N = 10)")

    N = 10

    print("\nСлучай 1: Генератор Ковью (c = 0)")
    a, b, x0, T, tau = find_best_params(N, c=0)
    print(f"Лучшие параметры: a={a}, b={b}, c=0, x0={x0}")
    print(f"Период T = {T}, предпериод tau = {tau}")

    gen = QuadraticCongruentialGenerator(a, b, 0, x0, N)
    seq = gen.generate(1000)
    print(f"Первые 30 элементов: {seq[:30]}")

    chi2, df, crit, passed = chi_square_test(seq, N)
    print(f"\nХи-квадрат: {chi2:.4f}, df={df}, крит.={crit:.4f} → "
          f"{'Пройден' if passed else 'Не пройден'}")
    freq = frequency_test(seq, N)
    print("Частоты:", {k: round(v, 4) for k, v in freq.items()})
    runs, expected_runs = runs_test(seq, N)
    print(f"Число серий: {runs} (ожидается ≈ {expected_runs:.0f})")
    print(f"Автокорреляция (lag=1): {serial_correlation_test(seq, 1):.4f}")

    print("\nСлучай 2: c ≠ 0")
    best = (None, None, None, None, -1, -1)
    for c in range(1, N):
        for a in range(1, N):
            for b in range(N):
                for x0 in range(N):
                    g = QuadraticCongruentialGenerator(a, b, c, x0, N)
                    t, T = g.find_period()
                    if T > best[4]:
                        best = (a, b, c, x0, T, t)
    a, b, c, x0, T, tau = best
    print(f"Лучшие параметры: a={a}, b={b}, c={c}, x0={x0}")
    print(f"Период T = {T}, предпериод tau = {tau}")

    gen = QuadraticCongruentialGenerator(a, b, c, x0, N)
    seq = gen.generate(1000)
    print(f"Первые 30 элементов: {seq[:30]}")

    chi2, df, crit, passed = chi_square_test(seq, N)
    print(f"\nХи-квадрат: {chi2:.4f}, df={df}, крит.={crit:.4f} → "
          f"{'Пройден' if passed else 'Не пройден'}")
    freq = frequency_test(seq, N)
    print("Частоты:", {k: round(v, 4) for k, v in freq.items()})
    runs, expected_runs = runs_test(seq, N)
    print(f"Число серий: {runs} (ожидается ≈ {expected_runs:.0f})")
    print(f"Автокорреляция (lag=1): {serial_correlation_test(seq, 1):.4f}")

    print("\nСравнение статистических свойств при разных параметрах")
    print(f"{'a':>3} {'b':>3} {'c':>3} {'x0':>3} {'T':>5} {'chi2':>9} {'прошёл':>8}")
    test_cases = [
        (5, 2, 0, 1), (3, 5, 0, 2), (7, 3, 1, 4),
        (2, 3, 2, 1), (4, 1, 3, 2), (5, 6, 1, 0),
    ]
    for (ta, tb, tc, tx) in test_cases:
        g = QuadraticCongruentialGenerator(ta, tb, tc, tx, N)
        t, T = g.find_period()
        s = g.generate(1000)
        chi2, _, _, passed = chi_square_test(s, N)
        print(f"{ta:>3} {tb:>3} {tc:>3} {tx:>3} {T:>5} {chi2:>9.4f} "
              f"{'да' if passed else 'нет':>8}")


# ЧАСТЬ 2.

def is_perfect_power(n: int) -> bool:
    # Проверка, является ли n совершенной степенью a^b (b >= 2)
    if n <= 1:
        return False
    max_b = int(log2(n)) + 1
    for b in range(2, max_b + 1):
        a = round(n ** (1 / b))
        if a ** b == n:
            return True
    return False


def is_prime_small(n: int) -> bool:
    # Проверка простоты для небольших чисел
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def largest_prime_factor(m: int) -> int:
    # Наибольший простой делитель числа m
    largest = 1
    d = 2
    while d * d <= m:
        while m % d == 0:
            largest = d
            m //= d
        d += 1 if d == 2 else 2
    if m > 1:
        largest = m
    return largest


def mod_pow(base: int, exp: int, mod: int) -> int:
    return pow(base, exp, mod)


def poly_mod_mul(p, q, r, n):
    # Умножение полиномов по модулю (x^r - 1) с коэффициентами mod n
    res = [0] * r
    for i, pi in enumerate(p):
        if pi == 0:
            continue
        for j, qj in enumerate(q):
            if qj == 0:
                continue
            res[(i + j) % r] = (res[(i + j) % r] + pi * qj) % n
    return res


def poly_mod_pow(base_poly, exp, r, n):
    # Возведение полинома в степень exp по модулю (x^r - 1, n)
    result = [1] + [0] * (r - 1)
    base = base_poly[:]
    while exp > 0:
        if exp & 1:
            result = poly_mod_mul(result, base, r, n)
        base = poly_mod_mul(base, base, r, n)
        exp >>= 1
    return result


def check_poly_congruence(n: int, a: int, r: int) -> bool:
    # Проверка сравнения (x + a)^n ≡ x^n + a (mod n, x^r - 1)
    left = poly_mod_pow([a % n, 1] + [0] * (r - 2), n, r, n)
    right = [0] * r
    right[n % r] = (right[n % r] + 1) % n
    right[0] = (right[0] + a) % n
    return left == right


# Полиномиальный тест

def aks_primality_test(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0:
        return False

    # Шаг 1: проверка на совершенную степень
    if is_perfect_power(n):
        return False

    # Шаги 2–7: поиск подходящего r
    r = 2
    while r < n:
        if gcd(n, r) != 1:
            return False  # найден делитель n

        if is_prime_small(r):
            q = largest_prime_factor(r - 1)
            # Условие выхода из цикла: q > 4*sqrt(r)*log2(n) и n^((r-1)/q) != 1 (mod r)
            if q > 4 * math.sqrt(r) * log2(n):
                if mod_pow(n, (r - 1) // q, r) != 1:
                    break
        r += 1

    if r >= n:
        return True  # n простое

    # Шаги 9–10: проверка полиномиальных сравнений
    limit = int(2 * math.sqrt(r) * log2(n))

    if n - 1 <= limit:
        # Для очень маленьких n достаточно проверить НОД
        for a in range(1, n):
            if gcd(a, n) != 1:
                return False
        return True

    # Перебор всех a от 1 до limit
    for a in range(1, limit + 1):
        if not check_poly_congruence(n, a, r):
            return False

    return True

SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
    239, 241, 251
]


def is_divisible_by_small_prime(n: int) -> bool:
    # Проверка делимости на малые простые (<= 256)
    for p in SMALL_PRIMES:
        if n == p:
            return False
        if n % p == 0:
            return True
    return False


class QCGBitSource:
    # Источник битов на основе ККГ из части 1

    def __init__(self, bits: int):
        self.bits = bits
        self.N = 1 << bits

        # Параметры ККГ, обеспечивающие большой период
        a = (1 << (bits - 1)) + 3
        b = (1 << (bits - 2)) + 1
        c = 1
        x0 = ((1 << bits) - 1) // 3 + 1

        self.gen = QuadraticCongruentialGenerator(a, b, c, x0, self.N)

    def getrandbits(self, bits: int) -> int:
        # Извлечение случайных битов из последовательных значений ККГ
        result = 0
        collected = 0
        while collected < bits:
            x = self.gen.next()
            take = min(self.bits, bits - collected)
            chunk = x & ((1 << take) - 1)
            result = (result << take) | chunk
            collected += take
        return result


def generate_prime(bits: int, max_attempts: int = 100000) -> int:
    # Генерация простого числа
    if bits < 2:
        raise ValueError("bits >= 2")

    qcg_source = QCGBitSource(bits)

    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        # Шаг 1: случайное p-битовое число (биты из ККГ)
        n = qcg_source.getrandbits(bits)
        # Шаг 2: установка старшего и младшего битов
        n |= (1 << (bits - 1)) | 1
        # Шаг 3: отсев по малым простым
        if is_divisible_by_small_prime(n):
            continue
        # Шаг 4: полиномиальный тест простоты
        if aks_primality_test(n):
            return n
    raise RuntimeError("Не удалось сгенерировать простое число")


def demo_aks():
    print("\nЧасть 2")
    print("Полиномиальный тест распознавания простоты (AKS)")

    print("\nТесты корректности на известных числах")
    test_numbers = [
        (2, True), (3, True), (4, False), (5, True),
        (17, True), (25, False), (97, True), (100, False),
        (101, True), (121, False), (341, False),
        (561, False),   
        (1105, False), 
        (1729, False),  
    ]
    all_ok = True
    for num, expected in test_numbers:
        result = aks_primality_test(num)
        status = "OK" if result == expected else "FAIL"
        if result != expected:
            all_ok = False
        print(f"  n = {num:7d}  →  {'простое' if result else 'составное':10s}  [{status}]")
    print(f"\nВсе тесты: {'Пройдены' if all_ok else 'Есть ошибки'}")


    print("\nГенерация простых чисел заданной битовой длины")
    print("(источник битов — квадратичный конгруэнтный генератор из части 1)")
    for bits in (8, 12):
        p = generate_prime(bits)
        check = aks_primality_test(p)
        print(f"  {bits:2d}-битовое простое: {p:12d}  "
              f"(проверка AKS: {'простое' if check else 'составное'})")

    print("\nПроверка отвержения составных чисел")
    composite_tests = [
        4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 22, 24, 25, 26, 27, 28,
        30, 32, 33, 34, 35, 36, 38, 39, 40, 42, 44, 45, 46, 48, 49, 50,
        51, 52, 54, 55, 56, 57, 58, 60, 62, 63, 64, 65, 66, 68, 69, 70,
    ]
    rejected = sum(1 for x in composite_tests if not aks_primality_test(x))
    print(f"  Отвергнуто {rejected} из {len(composite_tests)} составных чисел")


if __name__ == "__main__":
    demo_qcg()   # Часть 1
    demo_aks()   # Часть 2