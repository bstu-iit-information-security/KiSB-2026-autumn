import time
import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chisquare

class MWCGenerator:

    def __init__(self, a, seed, carry=0, alphabet_size=30):
        self.a = a
        self.m = 2 ** 32
        self.x = seed
        self.carry = carry
        self.alphabet_size = alphabet_size

    def next_int(self):
        t = self.a * self.x + self.carry
        self.carry = t >> 32
        self.x = t & 0xFFFFFFFF
        return self.x

    def next_symbol(self):
        """Возвращает символ из алфавита 0..(alphabet_size - 1)"""
        return self.next_int() % self.alphabet_size

    def generate_sequence(self, N):
        return [self.next_symbol() for _ in range(N)]

def analyze_sequence(seq, alphabet_size=30):
    freq = [0] * alphabet_size
    for s in seq:
        freq[s] += 1

    mean = np.mean(seq)
    var = np.var(seq)

    # Проверка гипотезы о равномерном распределении (Критерий хи-квадрат Пирсона)
    expected = [len(seq) / alphabet_size] * alphabet_size
    chi2_stat, p_value = chisquare(f_obs=freq, f_exp=expected)

    return freq, mean, var, chi2_stat, p_value


def plot_comparative_histograms(results):
    fig, axes = plt.subplots(1, len(results), figsize=(14, 5))
    if len(results) == 1:
        axes = [axes]

    for ax, (name, freq, _, _, _, _) in zip(axes, results):
        ax.bar(range(len(freq)), freq, color='skyblue', edgecolor='black')
        ax.set_title(f"Распределение:\n{name}")
        ax.set_xlabel("Символ")
        ax.set_ylabel("Частота")
        ax.grid(axis='y', alpha=0.7)

    plt.tight_layout()
    plt.show()


def autocorrelation(seq, lag):
    seq = np.array(seq)
    mean = np.mean(seq)
    num = np.sum((seq[:-lag] - mean) * (seq[lag:] - mean))
    den = np.sum((seq - mean) ** 2)
    return num / den


def plot_comparative_autocorrelation(results, seqs):
    lags = range(1, 21)
    fig, axes = plt.subplots(1, len(results), figsize=(14, 5))
    if len(results) == 1:
        axes = [axes]

    for ax, (name, _, _, _, _, _), seq in zip(axes, results, seqs):
        values = [autocorrelation(seq, lag) for lag in lags]
        ax.plot(lags, values, marker='o', color='coral')
        ax.set_title(f"Автокорреляция:\n{name}")
        ax.set_xlabel("Лаг")
        ax.set_ylabel("Корреляция")
        ax.set_ylim(-0.2, 1.0)
        ax.grid(True, linestyle='--', alpha=0.7)

    plt.tight_layout()
    plt.show()

def generate_base_candidate(bits, gen):
    byte_len = (bits + 7) // 8
    data = bytearray(gen.next_int() & 0xFF for _ in range(byte_len))

    shift = (8 - (bits % 8)) % 8
    data[0] |= (1 << (7 - shift))
    data[-1] |= 1

    return int.from_bytes(data, "big")


def small_primes_up_to(limit):
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for p in range(2, int(math.sqrt(limit)) + 1):
        if sieve[p]:
            for j in range(p * p, limit + 1, p):
                sieve[j] = False
    return [i for i in range(2, limit + 1) if sieve[i]]


def sieve_small_primes(n, primes):
    for p in primes:
        if n % p == 0:
            return n == p
    return True


def jacobi(a, n):
    if n <= 0 or n % 2 == 0:
        raise ValueError("n must be positive odd")
    a %= n
    result = 1
    while a != 0:
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            result = -result
        a %= n
    return result if n == 1 else 0


def random_in_range(min_val, max_val, gen):
    while True:
        r = gen.next_int()
        if max_val - min_val > 0:
            return min_val + (r % (max_val - min_val + 1))
        return min_val


def solovay_strassen(n, iterations, gen):
    if n < 2: return False
    if n % 2 == 0: return n == 2

    for _ in range(iterations):
        a = random_in_range(2, min(n - 2, 100000), gen)
        jac = jacobi(a, n)
        if jac == 0:
            return False
        exp = (n - 1) // 2
        mod_pow = pow(a, exp, n)
        if jac == -1:
            jac += n
        if mod_pow != jac % n:
            return False
    return True


def generate_prime(bits, sieve_limit, iterations, gen):
    primes = small_primes_up_to(sieve_limit)
    start = time.time()
    candidates = 0
    sieved_out = 0

    n = generate_base_candidate(bits, gen)

    while True:
        candidates += 1

        # Отсеивание делением на малые простые
        if not sieve_small_primes(n, primes):
            sieved_out += 1
            # Последовательный перебор нечетных чисел
            n += 2
            continue

        # Целевой тест Соловея-Штрассена
        if solovay_strassen(n, iterations, gen):
            end = time.time()
            return n, candidates, sieved_out, (end - start)

        n += 2

def run_tests_for_report(gen):
    print("\n=== ТЕСТЫ КОРРЕКТНОСТИ ДЛЯ ОТЧЕТА ===")
    print("Проверка вычисления символа Якоби:")
    j_res = jacobi(1001, 9907)
    print(f"  jacobi(1001, 9907) = {j_res} (Ожидается: -1 -> {'ОК' if j_res == -1 else 'ОШИБКА'})")
    j_res2 = jacobi(19, 45)
    print(f"  jacobi(19, 45) = {j_res2} (Ожидается: 1 -> {'ОК' if j_res2 == 1 else 'ОШИБКА'})")

    print("\nПроверка теста Соловея-Штрассена (5 итераций):")
    is_prime_9907 = solovay_strassen(9907, 5, gen)
    print(
        f"  Тест для 9907 (известное простое): {is_prime_9907} (Ожидается: True -> {'ОК' if is_prime_9907 else 'ОШИБКА'})")
    is_prime_9909 = solovay_strassen(9909, 5, gen)
    print(
        f"  Тест для 9909 (известное составное): {is_prime_9909} (Ожидается: False -> {'ОК' if not is_prime_9909 else 'ОШИБКА'})")
    print("=====================================\n")

if __name__ == "__main__":
    seed = 123456789

    test_gen = MWCGenerator(3636507990, seed)
    run_tests_for_report(test_gen)

    seq_length = 30000

    params = [
        ("Хороший множитель a=3636507990", 3636507990),
        ("Плохой множитель a=15", 15)
    ]

    results = []
    seqs = []

    print("=== ЭТАП 1 — Демонстрация свойств при изменении параметров ===")
    for name, a_val in params:
        gen = MWCGenerator(a_val, seed, alphabet_size=30)
        seq = gen.generate_sequence(seq_length)
        freq, mean, var, chi2, p_val = analyze_sequence(seq)

        results.append((name, freq, mean, var, chi2, p_val))
        seqs.append(seq)

        print(f"\nПараметр: {name}")
        print(f"Среднее: {mean:.4f}, Дисперсия: {var:.4f}")
        print(f"Хи-квадрат: {chi2:.4f}, p-value: {p_val:.4f}")
        if p_val > 0.05:
            print("-> Распределение РАВНОМЕРНОЕ (гипотеза принимается).")
        else:
            print("-> Распределение НЕ РАВНОМЕРНОЕ (гипотеза отклоняется).")

    plot_comparative_histograms(results)
    plot_comparative_autocorrelation(results, seqs)

    print("\n=== ЭТАП 2 — Лог работы генератора простых чисел ===")
    print("Генерация 3-х простых чисел (128 бит)...")

    gen_prime = MWCGenerator(3636507990, seed)

    header = f"| {'Попытка':<8} | {'Битность':<9} | {'Всего кандидатов':<16} | {'Отсеяно (сито)':<14} | {'Время (сек)':<11} |"
    separator = "-" * len(header)
    print(separator)
    print(header)
    print(separator)

    primes_found = []
    for i in range(1, 4):

        p, cand, sieved, t = generate_prime(128, 2000, 5, gen_prime)
        primes_found.append(p)
        print(f"| {i:<8} | {128:<9} | {cand:<16} | {sieved:<14} | {t:<11.4f} |")

    print(separator)
    print("\nСгенерированные числа:")
    for i, p in enumerate(primes_found, 1):
        print(f"{i}: {p}")