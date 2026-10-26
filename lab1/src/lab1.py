# -*- coding: utf-8 -*-
"""
Лабораторная работа №1, вариант 15.
Этап 1: генератор Эйхенауэра – Лена с обращением, N = 15.
Этап 2: генерация больших простых чисел, полиномиальный тест распознавания простоты (AKS).
"""
import math
import time
import secrets
from collections import Counter

import matplotlib.pyplot as plt

# ======================================================================
#                ЭТАП 1. ГЕНЕРАТОР ЭЙХЕНАУЭРА – ЛЕНА
# ======================================================================
N = 15  # размер алфавита по варианту


def carmichael(n):
    """Функция Кармайкла lambda(n) (перебором, n небольшое)."""
    units = [x for x in range(1, n) if math.gcd(x, n) == 1]
    k = 1
    while any(pow(x, k, n) != 1 for x in units):
        k += 1
    return k


LAMBDA = carmichael(N)  # lambda(15) = 4


def inverse(x, n=N):
    """Обобщённый обратный элемент x^(-1) = x^(lambda(n)-1) mod n.
    Для x, взаимно простых с n, это обычный обратный (x * x^-1 = 1 mod n);
    для x = 0 даёт 0 (тогда x_{t+1} = c, как в формуле (3));
    для делителей нуля (3, 5, 6, 9, 10, 12) — обратный по каждому простому
    модулю 3 и 5 отдельно (по китайской теореме об остатках)."""
    return pow(x, LAMBDA - 1, n)


class EichenauerLehn:
    """x_{t+1} = (a * x_t^{-1} + c) mod N, если x_t >= 1;  x_{t+1} = c, если x_t = 0."""

    def __init__(self, a, c, x0, n=N):
        self.a, self.c, self.n = a % n, c % n, n
        self.x = x0 % n

    def next(self):
        if self.x == 0:
            self.x = self.c
        else:
            self.x = (self.a * inverse(self.x, self.n) + self.c) % self.n
        return self.x

    def sequence(self, length):
        """Последовательность произвольной длины."""
        return [self.next() for _ in range(length)]


def period(a, c, x0, n=N):
    """Возвращает (длина предпериода, период T)."""
    seen, x, t = {}, x0 % n, 0
    g = EichenauerLehn(a, c, x0, n)
    while x not in seen:
        seen[x] = t
        x = g.next()
        t += 1
    return seen[x], t - seen[x]


def is_primitive_quadratic(a, c, p):
    """Проверка примитивности многочлена f(x) = x^2 - c*x - a над GF(p)
    (достаточное условие максимального периода по модулю простого p)."""
    def mulmod(u, v):  # умножение многочленов степени < 2 по модулю f
        # u, v = (u0 + u1*x); x^2 = c*x + a
        u0, u1 = u
        v0, v1 = v
        r0 = u0 * v0
        r1 = u0 * v1 + u1 * v0
        r2 = u1 * v1
        return ((r0 + r2 * a) % p, (r1 + r2 * c) % p)

    def powx(e):
        res, base = (1, 0), (0, 1)
        while e:
            if e & 1:
                res = mulmod(res, base)
            base = mulmod(base, base)
            e >>= 1
        return res

    if a % p == 0:
        return False
    order = p * p - 1
    if powx(order) != (1, 0):
        return False
    for q in prime_factors(order):
        if powx(order // q) == (1, 0):
            return False
    return True


def search_parameters(n=N):
    """Полный перебор a, c, x0 ∈ A: таблица максимальных периодов."""
    table = {}
    for a in range(n):
        for c in range(n):
            table[(a, c)] = max(period(a, c, x0, n)[1] for x0 in range(n))
    return table


# ----------------------- статистические тесты -------------------------
def chi2_critical(df, alpha=0.05):
    """Критическое значение chi^2 (аппроксимация Уилсона–Хилферти)."""
    z = {0.05: 1.6449, 0.01: 2.3263}[alpha]
    return df * (1 - 2 / (9 * df) + z * math.sqrt(2 / (9 * df))) ** 3


def frequency_test(seq, n=N):
    """Частотный тест (критерий хи-квадрат), df = N - 1."""
    cnt = Counter(seq)
    e = len(seq) / n
    chi2 = sum((cnt.get(k, 0) - e) ** 2 / e for k in range(n))
    return chi2, chi2_critical(n - 1), cnt


def serial_test(seq, n=N):
    """Тест серий (пар соседних элементов), df = N^2 - 1."""
    pairs = list(zip(seq[0::2], seq[1::2]))
    cnt = Counter(pairs)
    e = len(pairs) / (n * n)
    chi2 = sum((cnt.get((i, j), 0) - e) ** 2 / e for i in range(n) for j in range(n))
    return chi2, chi2_critical(n * n - 1), len(cnt)


def autocorrelation(seq, lag=1):
    m = sum(seq) / len(seq)
    num = sum((seq[i] - m) * (seq[i + lag] - m) for i in range(len(seq) - lag))
    den = sum((v - m) ** 2 for v in seq)
    return num / den if den else 1.0


def moments(seq, n=N):
    """Выборочные среднее и дисперсия vs теоретические для равномерного на {0..N-1}."""
    m = sum(seq) / len(seq)
    d = sum((v - m) ** 2 for v in seq) / len(seq)
    return m, d, (n - 1) / 2, (n * n - 1) / 12


def stage1(length=15000):
    print("=" * 78)
    print("ЭТАП 1. Генератор Эйхенауэра – Лена с обращением, N =", N)
    print("=" * 78)
    print(f"lambda({N}) = {LAMBDA}, обратный элемент: x^-1 = x^{LAMBDA - 1} mod {N}")
    print("Таблица обратных элементов:")
    print("  x   :", " ".join(f"{x:2d}" for x in range(N)))
    print("  x^-1:", " ".join(f"{inverse(x):2d}" for x in range(N)))

    table = search_parameters()
    dist = Counter(table.values())
    print("\nРаспределение максимального периода по всем парам (a, c), a, c ∈ [0, 14]:")
    for T in sorted(dist):
        print(f"  T = {T:2d}: {dist[T]:3d} пар")
    best = [k for k, v in table.items() if v == N]
    print(f"\nПары (a, c) с максимальным периодом T_max = {N}: {best}")
    print("Проверка условия: x^2 - c*x - a примитивен над GF(3) и GF(5):")
    for a, c in best:
        print(f"  a={a:2d}, c={c:2d}: GF(3) -> {is_primitive_quadratic(a, c, 3)}, "
              f"GF(5) -> {is_primitive_quadratic(a, c, 5)}, "
              f"периоды при x0=0..14: {sorted(set(period(a, c, x0)[1] for x0 in range(N)))}")

    # наборы параметров для сравнения
    sets = [(7, 2, 1), (13, 4, 3), (2, 3, 1), (1, 1, 2), (4, 2, 1), (3, 5, 1), (0, 0, 5)]
    print(f"\nСтатистическое тестирование, длина последовательности L = {length}, alpha = 0.05")
    hdr = (f"{'a':>3}{'c':>4}{'x0':>4}{'пред.':>6}{'T':>4}{'chi2 част.':>12}{'крит.':>8}"
           f"{'chi2 пар':>11}{'крит.':>8}{'пар':>5}{'r(1)':>8}{'M':>7}{'D':>7}  итог")
    print(hdr)
    print("-" * len(hdr))
    results = []
    for a, c, x0 in sets:
        pre, T = period(a, c, x0)
        seq = EichenauerLehn(a, c, x0).sequence(length)
        chi_f, crit_f, cnt = frequency_test(seq)
        chi_s, crit_s, npairs = serial_test(seq)
        r1 = autocorrelation(seq)
        m, d, _, _ = moments(seq)
        ok = "равномерно" if chi_f < crit_f else "НЕ равномерно"
        print(f"{a:>3}{c:>4}{x0:>4}{pre:>6}{T:>4}{chi_f:>12.2f}{crit_f:>8.2f}"
              f"{chi_s:>11.1f}{crit_s:>8.1f}{npairs:>5}{r1:>8.3f}{m:>7.2f}{d:>7.2f}  {ok}")
        results.append(((a, c, x0, T), seq, cnt))
    print(f"Теоретические M = {(N - 1) / 2:.2f}, D = {(N * N - 1) / 12:.2f}")

    a, c, x0 = sets[0]
    print(f"\nПервые 45 элементов при a={a}, c={c}, x0={x0}:")
    print(" ".join(map(str, EichenauerLehn(a, c, x0).sequence(45))))

    # --- графики ---
    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    for ax, ((a, c, x0, T), seq, cnt) in zip(axes.flat, results):
        ax.bar(range(N), [cnt.get(k, 0) for k in range(N)], color="steelblue")
        ax.axhline(length / N, color="red", ls="--", lw=1)
        ax.set_title(f"a={a}, c={c}, x0={x0}, T={T}")
        ax.set_xticks(range(N))
    ax = axes.flat[-1]
    ax.bar(sorted(dist), [dist[t] for t in sorted(dist)], color="darkorange")
    ax.set_title("Число пар (a,c) с данным T_max")
    ax.set_xlabel("T")
    fig.suptitle("Частоты появления элементов (красная линия — L/N)")
    fig.tight_layout()
    fig.savefig("stage1_hist.png", dpi=110)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    for ax, idx in zip(axes, (0, 2, 4)):
        (a, c, x0, T), seq, _ = results[idx]
        ax.scatter(seq[:-1][:300], seq[1:][:300], s=60, alpha=0.5)
        ax.set_title(f"(x_t, x_t+1): a={a}, c={c}, T={T}")
        ax.set_xlim(-1, N)
        ax.set_ylim(-1, N)
        ax.grid(True)
    fig.tight_layout()
    fig.savefig("stage1_pairs.png", dpi=110)
    plt.show()
    return best


# ======================================================================
#        ЭТАП 2. ГЕНЕРАЦИЯ ПРОСТЫХ ЧИСЕЛ, ПОЛИНОМИАЛЬНЫЙ ТЕСТ (AKS)
# ======================================================================
def small_primes(limit):
    """Решето Эратосфена."""
    s = bytearray([1]) * (limit + 1)
    s[0:2] = b"\x00\x00"
    for i in range(2, int(limit ** 0.5) + 1):
        if s[i]:
            s[i * i::i] = bytearray(len(s[i * i::i]))
    return [i for i in range(limit + 1) if s[i]]


def prime_factors(m):
    f, d = set(), 2
    while d * d <= m:
        while m % d == 0:
            f.add(d)
            m //= d
        d += 1
    if m > 1:
        f.add(m)
    return f


def integer_root(n, b):
    """Целый корень floor(n^(1/b)) методом Ньютона (без float — работает для любых n)."""
    if n < 2:
        return n
    x = 1 << ((n.bit_length() + b - 1) // b)   # начальное приближение сверху
    while True:
        y = ((b - 1) * x + n // x ** (b - 1)) // b
        if y >= x:
            return x
        x = y


def is_perfect_power(n):
    """Шаг 1: n = a^b, b > 1?"""
    for b in range(2, n.bit_length() + 1):
        a = integer_root(n, b)
        if a > 1 and a ** b == n:
            return True
    return False


def check_congruence(a, n, r):
    """(x + a)^n ≡ x^n + a  (mod x^r - 1, n).

    Многочлен степени < r хранится списком коэффициентов. Возведение в степень —
    «слева направо»: на каждом бите n — возведение в квадрат, а если бит = 1,
    ещё умножение на (x + a), т.е. сдвиг на x плюс a·f (это дёшево, O(r)).
    Квадрат считается через подстановку Кронекера: коэффициенты упаковываются
    в одно большое целое (по W бит на коэффициент), оно возводится в квадрат
    встроенной длинной арифметикой Python, затем свёртка по x^r = 1 делается
    одним сдвигом и сложением, и коэффициенты распаковываются по модулю n."""
    a %= n
    W = ((2 * r * n * n).bit_length() + 8) // 8 * 8   # бит на коэффициент
    s = W // 8
    rW = r * W
    mask = (1 << rW) - 1

    def square(c):
        X = int.from_bytes(b"".join(v.to_bytes(s, "little") for v in c), "little")
        P = X * X
        P = (P & mask) + (P >> rW)                     # x^(r+i) = x^i
        H = P.to_bytes(r * s, "little")
        return [int.from_bytes(H[i * s:(i + 1) * s], "little") % n for i in range(r)]

    c = [0] * r
    c[0], c[1] = a, 1                                  # x + a
    for bit in bin(n)[3:]:
        c = square(c)
        if bit == "1":                                 # c(x)·(x + a) mod (x^r - 1)
            c = [(c[i - 1] + a * c[i]) % n for i in range(r)]
    right = [0] * r
    right[0] = a
    right[n % r] = (right[n % r] + 1) % n
    return c == right


def aks_classic(n, log=False, only_r=False):
    """Полиномиальный тест распознавания простоты по методичке (п. 6.8,
    исходный вариант Агравала–Каяла–Саксены 2002 г.).
    only_r=True — только найти r и число проверок (сами сравнения не считать):
    в этой редакции r получается очень большим, и уже для n ~ 10^6 проверка
    сравнений в Python занимает часы."""
    if n < 2:
        return False
    if is_perfect_power(n):                     # шаг 1
        return False
    lg = math.log2(n)
    r = 2                                       # шаг 2
    while r < n:                                # шаг 3
        if math.gcd(r, n) != 1:                 # шаг 4
            return False
        if all(r % p for p in range(2, int(r ** 0.5) + 1)):   # шаг 5: r простое
            q = max(prime_factors(r - 1)) if r > 2 else 1
            if q >= 4 * math.sqrt(r) * lg and pow(n, (r - 1) // q, r) != 1:
                break
        r += 1                                  # шаг 6
    if r == n:                                  # шаг 8 (все r < n взаимно просты с n)
        if log:
            print(f"    r дошло до n = {n}: все r < n взаимно просты с n -> простое")
        return (r, 0) if only_r else True
    limit = int(2 * math.sqrt(r) * lg)          # шаг 10
    if log:
        print(f"    r = {r}, нужно проверить a = 1..{limit} "
              f"(многочлены степени < {r})")
    if only_r:
        return r, limit
    for a in range(1, limit + 1):
        if not check_congruence(a, n, r):       # шаг 11
            return False
    return True                                 # шаг 12


def multiplicative_order(n, r):
    k, x = 1, n % r
    while x != 1:
        x = x * n % r
        k += 1
    return k


def euler_phi(m):
    res = m
    for p in prime_factors(m):
        res -= res // p
    return res


def aks(n, log=False, progress=False):
    """Полиномиальный тест AKS (улучшенная редакция 2004 г.: тот же критерий
    (x - a)^n ≡ x^n - a (mod x^r - 1, n), но меньшее r — ord_r(n) > log2(n)^2)."""
    if n < 2:
        return False
    if is_perfect_power(n):                                   # 1
        return False
    lg = math.log2(n)
    r = 2                                                     # 2
    while True:
        if math.gcd(r, n) == 1 and multiplicative_order(n, r) > lg * lg:
            break
        r += 1
    for a in range(2, min(r, n - 1) + 1):                     # 3
        if 1 < math.gcd(a, n) < n:
            return False
    if n <= r:                                                # 4
        return True
    limit = int(math.sqrt(euler_phi(r)) * lg)                 # 5
    if log:
        print(f"    AKS: r = {r}, проверяем a = 1..{limit}")
    progress = progress and r * limit > 100_000   # индикатор только для долгих проверок
    step = max(1, limit // 20)
    for a in range(1, limit + 1):
        if progress and a % step == 0:
            print(f"\r    AKS n={n}: r={r}, a = {a}/{limit}", end="", flush=True)
        if not check_congruence(a, n, r):
            if progress and a >= step:
                print("\r" + " " * 70 + "\r", end="")
            return False
    if progress and limit >= step:
        print("\r" + " " * 70 + "\r", end="")
    return True                                               # 6


class BitSource:
    """Источник случайных чисел на основе генератора Эйхенауэра – Лена.

    У генератора с N = 15 период не больше 15, поэтому одна его траектория
    содержит не более 15 разных состояний: если брать все цифры p-битового
    числа из одной траектории, то при 8 парах (a, c) и 15 значениях x0 получится
    всего 8 * 15 = 120 разных чисел при любой разрядности p. Поэтому (как в
    «конгруэнтном генераторе со случайными параметрами», п. 4.10) перед каждой
    цифрой генератор перезапускается со случайной парой (a, c) с T = 15 и
    случайным x0. Так как при T = 15 отображение x0 -> x1 — перестановка
    алфавита, каждая цифра равномерно распределена на {0, ..., 14}."""

    def __init__(self, params):
        self.params = params

    def digit(self):
        a, c = self.params[secrets.randbelow(len(self.params))]
        return EichenauerLehn(a, c, secrets.randbelow(N)).next()

    def random_int(self, p):
        """Случайное число из [0, 2^p): k цифр в системе по основанию 15,
        затем остаток по модулю 2^p (запас в 2 цифры уменьшает смещение)."""
        k = math.ceil(p / math.log2(N)) + 2
        value = 0
        for _ in range(k):
            value = value * N + self.digit()
        return value % (1 << p)


def generate_prime(p, src, primes, log=True, test=aks):
    """Стандартная схема: случайное p-битовое n, старший и младший биты = 1,
    т.е. 2^(p-1) <= n < 2^p (разрядность p — число ДВОИЧНЫХ разрядов),
    просеивание малыми простыми, финальная проверка тестом варианта.
    После неудачи кандидат увеличивается на 2 (последовательный перебор)."""
    if p < 2:
        raise ValueError("разрядность p должна быть >= 2 бит")
    t0 = time.perf_counter()
    n = src.random_int(p) | (1 << (p - 1)) | 1
    stats = {"кандидатов": 0, "отсеяно делением": 0, "отсеяно AKS": 0}
    while True:
        if n.bit_length() != p:                     # вышли за разрядность — заново
            n = src.random_int(p) | (1 << (p - 1)) | 1
        stats["кандидатов"] += 1
        if any(n % q == 0 and n != q for q in primes):
            stats["отсеяно делением"] += 1
        elif test(n, progress=log):
            break
        else:
            stats["отсеяно AKS"] += 1
        n += 2
    stats["время, с"] = time.perf_counter() - t0
    if log:
        print(f"  p={p:3d}  n={n}  (двоичная запись {bin(n)[2:]}, "
              f"{n.bit_length()} бит, {len(str(n))} дес. цифр)")
        print(f"         кандидатов={stats['кандидатов']:4d}  "
              f"делением={stats['отсеяно делением']:4d}  AKS={stats['отсеяно AKS']:3d}  "
              f"t={stats['время, с']:.3f} с")
    return n, stats


def trial_division(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def stage2(best):
    print("\n" + "=" * 78)
    print("ЭТАП 2. Генерация простых чисел, полиномиальный тест распознавания простоты")
    print("=" * 78)

    # 1) проверка корректности тестов на малых числах
    lim = 3000
    print(f"Проверка AKS на всех n из [2, {lim}) (сравнение с пробным делением)...")
    t0 = time.perf_counter()
    ref = [n for n in range(2, lim) if trial_division(n)]
    got1 = [n for n in range(2, lim) if aks(n)]
    got2 = [n for n in range(2, 600) if aks_classic(n)]
    print(f"AKS (2004) на [2, {lim}): найдено {len(got1)} простых, совпадает с "
          f"пробным делением: {got1 == ref}  ({time.perf_counter() - t0:.1f} с)")
    print(f"AKS (методичка) на [2, 600): совпадает с пробным делением: "
          f"{got2 == [n for n in ref if n < 600]}")

    print("\nПроверка известных чисел:")
    tests = [561, 1105, 1729, 2465, 41041, 75361,          # числа Кармайкла
             7919, 104729, 1299709, 15485863,                # простые
             1024, 3 ** 13, 999983 * 1000003,                # степень и составное
             2 ** 19 - 1]                                    # простое Мерсенна 524287
    for n in tests:
        t0 = time.perf_counter()
        res = aks(n)
        print(f"  {n:>16}: {'простое' if res else 'составное':10} "
              f"(эталон: {'простое' if trial_division(n) else 'составное'}), "
              f"{time.perf_counter() - t0:.3f} с")
    print("  Редакция из методички (2002 г.):")
    print("   n = 997:", "простое" if aks_classic(997, log=True) else "составное")
    print("   n = 1000003 (только выбор r, сравнения не считаем — слишком долго):")
    aks_classic(1000003, log=True, only_r=True)

    # 2) генерация простых чисел
    src = BitSource(best)
    for bound in (256, 2000):
        primes = small_primes(bound)
        print(f"\nГенерация простых чисел (просеивание простыми ≤ {bound}, "
              f"{len(primes)} шт.):")
        for p in (8, 12, 16, 20, 24):
            generate_prime(p, src, primes)

    # 3) доля отсеянных малыми простыми
    print("\nДоля нечётных чисел, отсеянных делением на малые простые "
          "(10000 случайных 32-битных кандидатов):")
    cands = [src.random_int(32) | (1 << 31) | 1 for _ in range(10000)]
    for bound in (7, 100, 256, 2000):
        pr = [q for q in small_primes(bound) if q > 2]
        cut = sum(1 for n in cands if any(n % q == 0 for q in pr))
        theory = 1 - 1.12 / math.log(bound) if bound > 7 else 1 - (2 / 3) * (4 / 5) * (6 / 7)
        print(f"  простые ≤ {bound:4d}: отсеяно {cut / len(cands) * 100:5.1f} %  "
              f"(теория ≈ {theory * 100:4.1f} %)")


def main():
    while True:
        print("\nМЕНЮ\n 1 — Этап 1 (генератор Эйхенауэра – Лена)\n"
              " 2 — Этап 2 (простые числа, тест AKS)\n"
              " 3 — Сгенерировать простое число заданной разрядности\n"
              " 0 — Выполнить всё и выйти")
        ch = input("Выбор: ").strip()
        if ch == "1":
            stage1()
        elif ch == "2":
            stage2([k for k, v in search_parameters().items() if v == N])
        elif ch == "3":
            try:
                p = int(input("Разрядность p в битах (двоичных разрядах), "
                              "2 ≤ p, рекомендуется ≤ 28: "))
                best = [k for k, v in search_parameters().items() if v == N]
                generate_prime(p, BitSource(best), small_primes(2000))
            except ValueError as e:
                print("Ошибка:", e)
        elif ch == "0":
            stage2(stage1())
            break


if __name__ == "__main__":
    main()