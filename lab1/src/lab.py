import math
import time
import csv
from collections import Counter
import matplotlib.pyplot as plt

# Лабораторная работа №1, вариант 3
# Часть 1: инверсный генератор Эйхенауэра — Лена, алфавит N=20.
# Часть 2: полиномиальный тест простоты AKS.

N = 20
MODULUS = 1009
A = 2
C = 1
X0 = 1
SEED = 42


# -------------------- Часть 1 --------------------


def next_state(x, a=A, c=C, modulus=MODULUS):
    """Один шаг инверсного конгруэнтного генератора."""
    inverse = 0 if x == 0 else pow(x, -1, modulus)
    return (a * inverse + c) % modulus


def generate_sequence(length, a=A, c=C, x0=X0, modulus=MODULUS):
    """Генерирует последовательность символов алфавита {0,...,N-1}."""
    if length < 0:
        raise ValueError("Длина последовательности не может быть отрицательной")
    x = x0 % modulus
    result = []
    for _ in range(length):
        result.append(x % N)
        x = next_state(x, a, c, modulus)
    return result


def generate_states(length, a=A, c=C, x0=X0, modulus=MODULUS):
    """Возвращает внутренние состояния; они же используются для кандидатов."""
    x = x0 % modulus
    states = []
    for _ in range(length):
        states.append(x)
        x = next_state(x, a, c, modulus)
    return states


def find_period(a=A, c=C, x0=X0, modulus=MODULUS):
    """Точный период внутреннего состояния от заданного x0."""
    seen = {}
    x = x0 % modulus
    step = 0
    while x not in seen:
        seen[x] = step
        x = next_state(x, a, c, modulus)
        step += 1
    return step - seen[x]


def search_parameters(modulus=MODULUS, max_a=30, max_c=30, x0=X0):
    """Ищет лучший период среди ограниченного набора a и c."""
    best = []
    best_period = -1
    for a in range(1, max_a + 1):
        for c in range(1, max_c + 1):
            period = find_period(a, c, x0, modulus)
            if period > best_period:
                best_period = period
                best = [(a, c, period)]
            elif period == best_period:
                best.append((a, c, period))
    return best_period, best


def frequency_test(sequence):
    total = len(sequence)
    if total == 0:
        raise ValueError("Последовательность не должна быть пустой")
    counts = Counter(sequence)
    expected = total / N
    chi2 = sum((counts.get(i, 0) - expected) ** 2 / expected for i in range(N))
    return counts, chi2


def run_part1():
    print("=" * 62)
    print("ЧАСТЬ 1. ИНВЕРСНЫЙ ГЕНЕРАТОР ЭЙХЕНАУЭРА — ЛЕНА")
    print("=" * 62)
    length = 10000
    sequence = generate_sequence(length)
    period = find_period()
    counts, chi2 = frequency_test(sequence)

    print(f"Алфавит N={N}; модуль={MODULUS}; a={A}; c={C}; x0={X0}")
    print(f"Длина последовательности: {length}")
    print(f"Период внутреннего состояния: {period}")
    print(f"Ожидаемая частота каждого символа: {length / N:.2f}")
    print(f"Статистика хи-квадрат: {chi2:.4f}")
    print("Символ | Количество | Частота, %")
    for symbol in range(N):
        count = counts.get(symbol, 0)
        print(f"{symbol:6} | {count:10} | {count / length * 100:9.2f}")

    with open("frequency_table.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "count", "frequency_percent"])
        for symbol in range(N):
            count = counts.get(symbol, 0)
            writer.writerow([symbol, count, count / length * 100])

    plt.figure(figsize=(10, 5))
    plt.bar(range(N), [counts.get(i, 0) for i in range(N)])
    plt.axhline(length / N, linestyle="--", label="Ожидаемая частота")
    plt.xlabel("Символ алфавита")
    plt.ylabel("Количество появлений")
    plt.title("Частотное распределение символов (N=20)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("frequencies.png", dpi=150)
    plt.close()

    # Сравнение периодов для разных параметров
    variants = [(2, 1, 1), (3, 1, 1), (5, 7, 1), (7, 11, 1)]
    print("\nСравнение периодов:")
    labels, periods = [], []
    for a, c, x0 in variants:
        p = find_period(a, c, x0)
        labels.append(f"a={a}, c={c}")
        periods.append(p)
        print(f"a={a}, c={c}, x0={x0}: период={p}")

    plt.figure(figsize=(8, 5))
    plt.bar(labels, periods)
    plt.ylabel("Период внутреннего состояния")
    plt.title("Сравнение периодов при разных параметрах")
    plt.tight_layout()
    plt.savefig("periods.png", dpi=150)
    plt.close()

    print("\nПоиск лучшего периода для 1 <= a,c <= 30...")
    best_period, best_params = search_parameters()
    print(f"Лучший найденный период в этом диапазоне: {best_period}")
    print("Параметры (a, c, период):", best_params[:10])
    print(
        "Примечание: это максимум только среди проверенных параметров, не доказательство глобального максимума."
    )
    return sequence


# -------------------- Часть 2: AKS --------------------


def is_perfect_power(n):
    if n < 4:
        return False
    max_exp = n.bit_length()
    for exponent in range(2, max_exp + 1):
        low, high = 2, 1 << ((n.bit_length() + exponent - 1) // exponent)
        while low <= high:
            mid = (low + high) // 2
            value = mid**exponent
            if value == n:
                return True
            if value < n:
                low = mid + 1
            else:
                high = mid - 1
    return False


def multiplicative_order(n, r):
    if math.gcd(n, r) != 1:
        return 0
    value = 1
    for k in range(1, r + 1):
        value = value * n % r
        if value == 1:
            return k
    return 0


def euler_phi(n):
    result = n
    value = n
    p = 2
    while p * p <= value:
        if value % p == 0:
            while value % p == 0:
                value //= p
            result -= result // p
        p += 1
    if value > 1:
        result -= result // value
    return result


def poly_mul(left, right, r, modulus):
    result = [0] * r
    for i, x in enumerate(left):
        if not x:
            continue
        for j, y in enumerate(right):
            if y:
                result[(i + j) % r] = (result[(i + j) % r] + x * y) % modulus
    return result


def poly_pow(base, exponent, r, modulus):
    result = [0] * r
    result[0] = 1
    base = base[:]
    while exponent:
        if exponent & 1:
            result = poly_mul(result, base, r, modulus)
        base = poly_mul(base, base, r, modulus)
        exponent >>= 1
    return result


def aks_is_prime(n):
    """Детерминированный AKS для учебных чисел; на больших n может быть медленным."""
    if n < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False

    if is_perfect_power(n):
        return False

    log_bound = math.ceil(math.log2(n) ** 2)
    r = 2
    while True:
        if math.gcd(n, r) == 1 and multiplicative_order(n, r) > log_bound:
            break
        r += 1

    for a in range(2, min(r, n)):
        d = math.gcd(a, n)
        if 1 < d < n:
            return False

    if n <= r:
        return True

    bound = int(math.sqrt(euler_phi(r)) * math.log2(n))
    for a in range(1, bound + 1):
        base = [a % n, 1] + [0] * (r - 2)
        left = poly_pow(base, n, r, n)
        right = [0] * r
        right[0] = a % n
        right[n % r] = (right[n % r] + 1) % n
        if left != right:
            return False
    return True


def small_prime_sieve(n, limit=2000):
    """True, если кандидат не делится на простые числа <= limit."""
    if n < 2:
        return False
    for p in range(2, min(limit, math.isqrt(n)) + 1):
        prime = True
        for d in range(2, math.isqrt(p) + 1):
            if p % d == 0:
                prime = False
                break
        if prime:
            if n == p:
                return True
            if n % p == 0:
                return False
    return True


def candidate_from_generator(bits, sequence):
    """Получает биты из внутреннего состояния генератора варианта 3."""
    if bits < 2:
        raise ValueError("bits должно быть >= 2")
    needed = bits
    bit_string = []
    # Берём младший бит каждого внутреннего состояния.
    # Для учебной демонстрации; это не криптографический генератор.
    for state in sequence:
        bit_string.append(str(state & 1))
        if len(bit_string) >= needed:
            break
    while len(bit_string) < needed:
        # Продолжаем последовательность при необходимости.
        bit_string.append("0")
    n = int("".join(bit_string), 2)
    n |= 1 << (bits - 1)  # старший бит = 1
    n |= 1  # младший бит = 1
    return n


def generate_prime(bits, sequence, max_candidates=10000):
    """Возвращает найденное простое число и счётчики фильтрации."""
    tested = sieve_rejected = aks_rejected = 0
    start = time.perf_counter()
    offset = 0

    while tested < max_candidates:
        # Перестраиваем кандидат из разных участков потока генератора.
        # Для кандидата используем внутренние состояния генератора,
        # а не символы алфавита после операции % N.
        chunk = generate_states(bits, x0=(X0 + offset) % MODULUS)
        offset += bits
        n = candidate_from_generator(bits, chunk)
        tested += 1

        if not small_prime_sieve(n, 2000):
            sieve_rejected += 1
            continue
        if not aks_is_prime(n):
            aks_rejected += 1
            continue

        elapsed = time.perf_counter() - start
        return n, tested, sieve_rejected, aks_rejected, elapsed

    raise RuntimeError("Не удалось найти простое число: увеличьте max_candidates")


def run_part2(sequence):
    print("\n" + "=" * 62)
    print("ЧАСТЬ 2. ПОЛИНОМИАЛЬНЫЙ ТЕСТ ПРОСТОТЫ AKS")
    print("=" * 62)
    test_numbers = [2, 3, 17, 25, 97, 121, 257, 561, 1009]
    print("Проверка тестовых чисел:")
    for n in test_numbers:
        print(f"{n:5} -> {'простое' if aks_is_prime(n) else 'составное'}")

    bits = 12
    prime, tested, sieve_rejected, aks_rejected, elapsed = generate_prime(
        bits, sequence
    )
    print(f"\nНайдено простое число ({bits} бит): {prime}")
    print(f"Повторная проверка AKS: {aks_is_prime(prime)}")
    print(f"Всего проверено кандидатов: {tested}")
    print(f"Отсеяно просеиванием: {sieve_rejected}")
    print(f"Отсеяно тестом AKS: {aks_rejected}")
    print(f"Время поиска: {elapsed:.6f} сек.")

    with open("prime_search_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "bits",
                "prime",
                "candidates_tested",
                "sieve_rejected",
                "aks_rejected",
                "elapsed_seconds",
            ]
        )
        writer.writerow(
            [bits, prime, tested, sieve_rejected, aks_rejected, f"{elapsed:.6f}"]
        )


if __name__ == "__main__":
    # Фиксируем воспроизводимость эксперимента.
    print("Лабораторная работа №1. Вариант 3")
    sequence = run_part1()
    run_part2(sequence)
    print(
        "\nФайлы результатов: frequencies.png, periods.png, frequency_table.csv, prime_search_log.csv"
    )
