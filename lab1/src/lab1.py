import math
import random
import time
from collections import Counter


class LFSR:
    """
    Регистр сдвига с линейной обратной связью (LFSR) в конфигурации Фибоначчи.
    Обратная связь: fb = sum_{t in taps} s_{deg - t} mod 2.
    Сдвиг вправо, выходной бит — младший разряд (LSB).
    """
    def __init__(self, taps, degree, seed=1):
        self.taps = sorted(taps, reverse=True)
        self.degree = degree
        self.mask = (1 << degree) - 1
        self.state = seed & self.mask if (seed & self.mask) != 0 else 1

    def next_bit(self):
        out = self.state & 1
        fb = 0
        for t in self.taps:
            fb ^= ((self.state >> (self.degree - t)) & 1)
        self.state = (self.state >> 1) | (fb << (self.degree - 1))
        return out

    def measure_period(self, max_steps=100000):
        init = self.state
        steps = 0
        while steps < max_steps:
            self.next_bit()
            steps += 1
            if self.state == init:
                return steps
        return -1


class ShrinkingGenerator:
    """
    Генератор на основе псевдослучайного прореживания (Shrinking Generator, SG-генератор):
      - LFSR G1 порождает элементарную последовательность a_t;
      - LFSR G2 порождает селектирующую последовательность s_t;
      - Если s_t = 1, бит a_t выдается на выход; если s_t = 0, бит отбрасывается.

    Теоретический период при НОД(2^n - 1, 2^m - 1) = 1:
      T = (2^n - 1) * 2^(m - 1).
      Для n = 7 (G1) и m = 9 (G2):
      T_max = (2^7 - 1) * 2^(9 - 1) = 127 * 256 = 32 512 бит.
    """
    def __init__(self, taps_g1=(7, 3, 2, 1), deg_g1=7, taps_g2=(9, 4), deg_g2=9, seed1=0b1010101, seed2=0b110011001):
        self.g1 = LFSR(taps_g1, deg_g1, seed1)
        self.g2 = LFSR(taps_g2, deg_g2, seed2)
        self.total_clocks = 0
        self.discarded = 0

    def next_bit(self):
        while True:
            a = self.g1.next_bit()
            s = self.g2.next_bit()
            self.total_clocks += 1
            if s == 1:
                return a
            self.discarded += 1

    def sequence(self, length):
        return [self.next_bit() for _ in range(length)]


def chi2_uniformity_test(seq, alphabet_size=16):
    """
    Критерий согласия Хи-квадрат Пирсона для проверки гипотезы H0 о равномерности.
    По умолчанию проверяются 4-битные блоки (размер алфавита 16, df = 15).
    Критическое значение chi2_{0.05, 15} = 24.996.
    """
    n = len(seq)
    expected = n / alphabet_size
    counts = Counter(seq)
    chi2_stat = sum((counts.get(i, 0) - expected) ** 2 / expected for i in range(alphabet_size))
    crit_val_005 = 24.996  # Табличное значение для df = 15, alpha = 0.05
    is_uniform = chi2_stat <= crit_val_005
    return {
        "chi2_stat": chi2_stat,
        "critical_val": crit_val_005,
        "is_uniform": is_uniform,
        "counts": counts,
        "expected": expected
    }


def autocorrelation(seq, max_lag=5):
    """Вычисление выборочных коэффициентов автокорреляции R(d)."""
    n = len(seq)
    mean = sum(seq) / n
    var = sum((x - mean) ** 2 for x in seq)
    if var == 0:
        return [0.0] * max_lag
    corrs = []
    for lag in range(1, max_lag + 1):
        cov = sum((seq[t] - mean) * (seq[t + lag] - mean) for t in range(n - lag))
        corrs.append(cov / var)
    return corrs


def show_generator_demo():
    print("\n" + "=" * 75)
    print("ЭТАП 1. КОМБИНИРОВАНИЕ LFSR МЕТОДОМ ПРОРЕЖИВАНИЯ (SG-ГЕНЕРАТОР)")
    print("Селектор G2: g(x) = x^9 + x^4 + 1 (deg = 9, период = 511)")
    print("=" * 75)

    configs = {
        "f1 (Полином 1: x^7 + x^3 + x^2 + x + 1) [Примитивный]": {
            "taps": [7, 3, 2, 1], "deg": 7, "is_prim": True, "t_theor": 32512
        },
        "f2 (Полином 2: x^7 + x + 1) [Примитивный]": {
            "taps": [7, 1], "deg": 7, "is_prim": True, "t_theor": 32512
        },
        "f3 (Полином 3: x^7 + x^3 + 1) [Примитивный]": {
            "taps": [7, 3], "deg": 7, "is_prim": True, "t_theor": 32512
        },
        "f_deg (Приводимый полином: x^7 + x^6 + x^2 + 1) [Вырожденный]": {
            "taps": [7, 6, 2], "deg": 7, "is_prim": False, "t_theor": 2304
        }
    }

    sample_bits = 16000  # Выборка бит
    block_size = 4
    num_blocks = sample_bits // block_size

    for name, cfg in configs.items():
        gen = ShrinkingGenerator(taps_g1=cfg["taps"], deg_g1=cfg["deg"])
        bits = gen.sequence(sample_bits)

        # Преобразуем биты в 4-битные символы алфавита 0..15
        symbols = []
        for i in range(num_blocks):
            val = 0
            for b in bits[i * block_size : (i + 1) * block_size]:
                val = (val << 1) | b
            symbols.append(val)

        test_res = chi2_uniformity_test(symbols, alphabet_size=16)
        corrs = autocorrelation(bits, max_lag=3)

        ones_count = sum(bits)
        zeros_count = sample_bits - ones_count

        print(f"\nКонфигурация: {name}")
        print(f"  Примитивность над GF(2): {'ДА (максимальный период)' if cfg['is_prim'] else 'НЕТ (приводимый)'}")
        print(f"  Теоретический период T:  {cfg['t_theor']} бит")
        print(f"  Первые 32 бита потока:   {''.join(map(str, bits[:32]))}")
        print(f"  Баланс 0 / 1:            нулей={zeros_count} ({zeros_count/sample_bits*100:.1f}%), единиц={ones_count} ({ones_count/sample_bits*100:.1f}%)")
        print(f"  Критерий Хи-квадрат:     {test_res['chi2_stat']:.3f} (критич. {test_res['critical_val']:.3f})")
        print(f"  Вердикт H0:              {'РАВНОМЕРНО (H0 принимается)' if test_res['is_uniform'] else 'НЕРАВНОМЕРНО (H0 отвергается)'}")
        print(f"  Автокорреляция бит:      lag1={corrs[0]:+.4f}, lag2={corrs[1]:+.4f}, lag3={corrs[2]:+.4f}")
        print(f"  Частоты блоков 0..15 (ожидалось ~{int(test_res['expected'])}):")
        counts_str = " ".join(f"{v}:{test_res['counts'].get(v, 0)}" for v in range(16))
        print(f"    {counts_str}")


def sieve_primes(limit=256):
    """Решето Эратосфена: генерация простых чисел до заданной границы limit."""
    is_prime = bytearray([1]) * (limit + 1)
    is_prime[0:2] = b"\x00\x00"
    for p in range(2, int(limit ** 0.5) + 1):
        if is_prime[p]:
            is_prime[p * p : limit + 1 : p] = b"\x00" * (((limit - p * p) // p) + 1)
    return [i for i, val in enumerate(is_prime) if val]


SMALL_PRIMES = sieve_primes(256)


def trial_division_filter(n, primes_list=None):
    """
    Предварительное просеивание: проверка делимости на малые простые числа.
    Отсекает до ~80% составных чисел до запуска тяжелых тестов.
    """
    if primes_list is None:
        primes_list = SMALL_PRIMES
    for p in primes_list:
        if n == p:
            return True, None
        if n % p == 0:
            return False, p
    return True, None


def lehmann_test(n, k=15):
    """
    Вероятностный тест простоты Леманна (Целевой алгоритм Варианта 2):
      1. Выбрать случайное число a в диапазоне [2, n - 2];
      2. Вычислить t = a^((n - 1) / 2) mod n;
      3. Если t != 1 и t != -1 (т.е. t != n - 1 mod n), то число n составное;
      4. Повторить k раз. Число признается простым, если t = ±1 и
         не всегда равно 1 (хотя бы раз встретилось t = -1 mod n).
    Вероятность ошибки составного числа <= (1/2)^k.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    exp = (n - 1) // 2
    has_minus_one = False

    for _ in range(k):
        a = random.randint(2, n - 2)
        if math.gcd(a, n) > 1:
            return False

        t = pow(a, exp, n)
        if t != 1 and t != (n - 1):
            return False

        if t == (n - 1):
            has_minus_one = True

    return has_minus_one if k >= 5 else True


def lehmann_test_detailed(n, k=15):
    """Детальный тест Леманна с протоколированием каждого раунда."""
    if n < 2:
        return False, "n < 2", []
    if n in (2, 3):
        return True, "n in {2, 3}", []
    if n % 2 == 0:
        return False, "Четное число > 2", []

    exp = (n - 1) // 2
    rounds_log = []
    has_minus_one = False

    for r in range(1, k + 1):
        a = random.randint(2, n - 2)
        g = math.gcd(a, n)
        if g > 1:
            rounds_log.append((r, a, f"НОД({a}, {n}) = {g} > 1", "СОСТАВНОЕ"))
            return False, f"Найден делитель {g}", rounds_log

        t = pow(a, exp, n)
        t_str = "+1" if t == 1 else ("-1" if t == (n - 1) else f"{t}")

        if t != 1 and t != (n - 1):
            rounds_log.append((r, a, f"t = {t_str} != ±1", "СОСТАВНОЕ"))
            return False, f"a^((n-1)/2) != ±1 на раунде {r}", rounds_log

        if t == (n - 1):
            has_minus_one = True

        rounds_log.append((r, a, f"t = {t_str}", "OK (±1)"))

    if k >= 5 and not has_minus_one:
        return False, "Все раунды дали +1 (нет свидетеля -1)", rounds_log

    return True, f"Пройдено {k} раундов (ошибка <= {1/(2**k):.2e})", rounds_log


def miller_rabin_test(n, k=15):
    """Тест Рабина — Миллера (для сравнения и кросс-проверки)."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    s = 0
    t = n - 1
    while t % 2 == 0:
        s += 1
        t //= 2

    for _ in range(k):
        a = random.randint(2, n - 2)
        x = pow(a, t, n)
        if x == 1 or x == n - 1:
            continue
        composite = True
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                composite = False
                break
        if composite:
            return False
    return True


def jacobi_symbol(a, n):
    """Символ Якоби (a / n) для теста Соловея — Штрассена."""
    a = a % n
    t = 1
    while a != 0:
        while a % 2 == 0:
            a //= 2
            r = n % 8
            if r == 3 or r == 5:
                t = -t
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            t = -t
        a = a % n
    return t if n == 1 else 0


def solovay_strassen_test(n, k=15):
    """Тест Соловея — Штрассена (для сравнительного анализа)."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    exp = (n - 1) // 2
    for _ in range(k):
        a = random.randint(2, n - 2)
        j = jacobi_symbol(a, n)
        if j == 0:
            return False
        j_mod = (j + n) % n
        if pow(a, exp, n) != j_mod:
            return False
    return True


def random_candidate_from_prng(bits, generator):
    """
    Генерация p-битового кандидата с использованием SG-генератора из Этапа 1:
    - генерируется случайное битовое число;
    - старший и младший биты устанавливаются в 1 (гарантия разрядности и нечетности).
    """
    val = 0
    for _ in range(bits):
        val = (val << 1) | generator.next_bit()
    val |= (1 << (bits - 1))
    val |= 1
    return val


def generate_prime_candidate_pipeline(bits=64, max_attempts=50000):
    """
    Стандартная схема генерации простых чисел Варианта 2:
      1) Генерация p-битового нечетного кандидата из SG-генератора;
      2) Предварительное просеивание ситом малых простых (<= 256);
      3) Проверка целевым тестом Леманна (k = 15);
      4) Ведение лога отсева и замера времени.
    """
    gen = ShrinkingGenerator(taps_g1=[7, 3, 2, 1], deg_g1=7, taps_g2=[9, 4], deg_g2=9)
    stats = {"checked": 0, "sieve_filtered": 0, "lehmann_checked": 0, "elapsed": 0.0}
    started = time.perf_counter()

    for _ in range(max_attempts):
        cand = random_candidate_from_prng(bits, gen)
        stats["checked"] += 1

        # Этап 1: Сито малых простых
        passed_sieve, _ = trial_division_filter(cand)
        if not passed_sieve:
            stats["sieve_filtered"] += 1
            continue

        # Этап 2: Тест Леманна
        stats["lehmann_checked"] += 1
        if lehmann_test(cand, k=15):
            stats["elapsed"] = time.perf_counter() - started
            return cand, stats

    stats["elapsed"] = time.perf_counter() - started
    return None, stats


def solve_congruence_variant2():
    """Решение сравнения 5x ≡ 3 (mod 12) тремя методами (Контрольный вопрос 12, Вариант 2)."""
    a, b, m = 5, 3, 12
    print("\n" + "=" * 70)
    print("КОНТРОЛЬНОЕ ЗАДАНИЕ №12 (Вариант 2): Решить сравнение 5x ≡ 3 (mod 12)")
    print("=" * 70)

    # a) Алгоритм Евклида
    print("\n[a] Алгоритм Евклида для НОД(12, 5):")
    r0, r1 = m, a
    steps = []
    while r1 != 0:
        q = r0 // r1
        rem = r0 % r1
        steps.append((r0, q, r1, rem))
        print(f"    {r0} = {q} * {r1} + {rem}")
        r0, r1 = r1, rem
    gcd_val = r0
    print(f"    НОД({m}, {a}) = {gcd_val} (числа взаимно просты, решение единственно).")
    print("    Обратный ход (выражение 1 через остатки):")
    print("    1 = 5 - 2 * 2")
    print("    1 = 5 - 2 * (12 - 2 * 5) = 5 * 5 - 2 * 12")
    print(f"    Отсюда: 5 * 5 ≡ 1 (mod 12) => 5^(-1) ≡ 5 (mod 12).")
    x_euclid = (b * 5) % m
    print(f"    Решение: x ≡ (3 * 5) mod 12 = {x_euclid}")

    # b) Расширенный алгоритм Евклида (EEA)
    print("\n[b] Расширенный алгоритм Евклида (EEA):")
    # u*m + v*a = 1
    u0, u1 = 1, 0
    v0, v1 = 0, 1
    r_prev, r_curr = m, a
    while r_curr != 0:
        q = r_prev // r_curr
        r_prev, r_curr = r_curr, r_prev % r_curr
        u0, u1 = u1, u0 - q * u1
        v0, v1 = v1, v0 - q * v1
    v_bezout = v0
    inv_a = v_bezout % m
    x_eea = (b * inv_a) % m
    print(f"    Коэффициент Безу v = {v_bezout} => обратный элемент 5^(-1) mod 12 = {inv_a}")
    print(f"    Решение: x = (3 * {inv_a}) mod 12 = {x_eea}")

    # c) Метод Эйлера
    print("\n[c] Метод Эйлера:")
    # 12 = 2^2 * 3
    phi_m = 12 * (1 - 1/2) * (1 - 1/3)  # = 4
    phi_m = int(round(phi_m))
    inv_euler = pow(a, phi_m - 1, m)
    x_euler = (b * inv_euler) % m
    print(f"    Факторизация модуля: 12 = 2^2 * 3")
    print(f"    Функция Эйлера phi(12) = 12 * (1 - 1/2) * (1 - 1/3) = {phi_m}")
    print(f"    Взаимно простые с 12 числа: {{1, 5, 7, 11}}")
    print(f"    5^(phi - 1) mod 12 = 5^{phi_m - 1} mod 12 = 5^3 mod 12 = 125 mod 12 = {inv_euler}")
    print(f"    Решение: x = (3 * {inv_euler}) mod 12 = {x_euler}")

    # Проверка
    check_val = (a * x_eea) % m
    print(f"\n[Проверка]: 5 * {x_eea} mod 12 = {check_val} == 3: {check_val == b}")


def compare_primality_benchmarks():
    """Сравнительное тестирование алгоритмов Леманна, Миллера-Рабина и Соловея-Штрассена."""
    print("\n" + "=" * 70)
    print("СРАВНИТЕЛЬНЫЙ АНАЛИЗ ТЕСТОВ ПРОСТОТЫ (Леманн, Рабин-Миллер, Соловей-Штрассен)")
    print("=" * 70)
    bit_sizes = [16, 32, 64, 128]
    gen = ShrinkingGenerator()

    print(f"{'Разрядность':<12} | {'Кандидатов':<12} | {'Сито (<=256)':<14} | {'Леманн (мс)':<14} | {'Р-М (мс)':<12} | {'С-Ш (мс)':<12}")
    print("-" * 85)

    for bits in bit_sizes:
        candidates = [random_candidate_from_prng(bits, gen) for _ in range(50)]
        sieve_filtered = sum(1 for c in candidates if not trial_division_filter(c)[0])

        t0 = time.perf_counter()
        for c in candidates:
            lehmann_test(c, k=15)
        t_leh = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        for c in candidates:
            miller_rabin_test(c, k=15)
        t_mr = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        for c in candidates:
            solovay_strassen_test(c, k=15)
        t_ss = (time.perf_counter() - t0) * 1000

        pct = (sieve_filtered / 50) * 100
        print(f"{bits:<12} | {50:<12} | {sieve_filtered} ({pct:.0f}%)        | {t_leh:<14.3f} | {t_mr:<12.3f} | {t_ss:<12.3f}")


def main():
    print("=" * 70)
    print("  Лабораторная работа №1 (КиСБ) — ВАРИАНТ №2")
    print("  Комбинирование LFSR методом псевдослучайного прореживания (SG-генератор)")
    print("  + Вероятностный тест простоты Леманна (Lehmann test)")
    print("=" * 70)

    while True:
        print("\nГЛАВНОЕ МЕНЮ:")
        print("  1 — Этап 1: Демонстрация и статистика SG-генератора (полиномы f1, f2, f3)")
        print("  2 — Проверить произвольное число на простоту (сито + тест Леманна)")
        print("  3 — Этап 2: Стандартная схема генерации с ситом малых простых (<=256)")
        print("  4 — Этап 2: Сравнительный анализ тестов (Леманн vs Рабин-Миллер vs Соловей-Штрассен)")
        print("  5 — Решение контрольного сравнения 5x ≡ 3 (mod 12)")
        print("  0 — Выход")

        choice = input("Выберите действие [0-5]: ").strip()

        if choice == "1":
            show_generator_demo()

        elif choice == "2":
            try:
                num_str = input("Введите натуральное число n: ").strip()
                n = int(num_str)
                started = time.perf_counter()
                sieve_pass, div = trial_division_filter(n)
                if not sieve_pass:
                    print(f"Число {n} — СОСТАВНОЕ (делится на малое простое {div}).")
                else:
                    passed, reason, r_log = lehmann_test_detailed(n, k=15)
                    verdict = "ВЕРОЯТНО ПРОСТОЕ" if passed else "СОСТАВНОЕ"
                    print(f"\nЧисло {n} — {verdict} (по тесту Леманна, k=15).")
                    print(f"Причина: {reason}")
                    if r_log:
                        print("Первые раунды теста:")
                        for r_item in r_log[:6]:
                            print(f"  Раунд {r_item[0]:02d}: a={r_item[1]} {r_item[2]} -> {r_item[3]}")
                print(f"Время проверки: {time.perf_counter() - started:.6f} сек.")
            except ValueError:
                print("Ошибка: необходимо ввести натуральное число.")

        elif choice == "3":
            try:
                bits_str = input("Разрядность простого числа в битах (например, 16, 32, 64): ").strip()
                bits = int(bits_str)
                if bits < 4:
                    print("Разрядность должна быть >= 4.")
                    continue
                p, stats = generate_prime_candidate_pipeline(bits=bits)
                pct = (stats["sieve_filtered"] / stats["checked"]) * 100 if stats["checked"] else 0
                print(f"\nНайдено простое число: {p}")
                print(f"  В шестнадцатеричном виде: {hex(p)}")
                print(f"  Разрядность:              {p.bit_length()} бит")
                print(f"  Кандидатов проверено:     {stats['checked']}")
                print(f"  Отсеяно ситом (<= 256):   {stats['sieve_filtered']} ({pct:.2f}%)")
                print(f"  Проверено тестом Леманна: {stats['lehmann_checked']}")
                print(f"  Время поиска:             {stats['elapsed']:.6f} сек.")
            except ValueError:
                print("Ошибка: введите целое число бит.")

        elif choice == "4":
            compare_primality_benchmarks()

        elif choice == "5":
            solve_congruence_variant2()

        elif choice == "0":
            print("\nВыход из программы.")
            break
        else:
            print("Неверная команда, попробуйте снова.")


if __name__ == "__main__":
    main()
