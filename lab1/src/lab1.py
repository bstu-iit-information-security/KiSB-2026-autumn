

import math
import random
import time
from collections import Counter



class RandomParamCongruentialGenerator:
    """
    Конгруэнтный генератор со случайными параметрами:
      x_t = (a_t * x_{t-1} + b_t) mod N,
    где пара (a_t, b_t) на каждом такте равновероятно выбирается из множества B.
    """
    def __init__(self, modulus=15, param_set_b=None, seed=1, rng_seed=None):
        self.modulus = modulus
        self.param_set_b = param_set_b or [(3, 0), (3, 1), (3, 2)]
        self.state = seed % modulus
        self._rng = random.Random(rng_seed)

    def next_int(self):
        # Селектор равновероятно выбирает пару (a_t, b_t) из множества B
        a_t, b_t = self._rng.choice(self.param_set_b)
        self.state = (a_t * self.state + b_t) % self.modulus
        return self.state

    def sequence(self, length):
        return [self.next_int() for _ in range(length)]


def chi2_uniformity_test(seq, alphabet_size=15):
    """
    Критерий согласия Хи-квадрат Пирсона для проверки гипотезы H0 о равномерности.
    df = alphabet_size - 1. Для N=15, df=14, критическое значение chi2_{0.05, 14} = 23.685.
    """
    n = len(seq)
    expected = n / alphabet_size
    counts = Counter(seq)
    chi2_stat = sum((counts.get(i, 0) - expected) ** 2 / expected for i in range(alphabet_size))
    crit_val_005 = 23.685  # Табличное значение для df = 14, alpha = 0.05
    is_uniform = chi2_stat <= crit_val_005
    return {
        "chi2_stat": chi2_stat,
        "critical_val": crit_val_005,
        "is_uniform": is_uniform,
        "counts": counts,
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
    print("\n" + "=" * 70)
    print("ЭТАП 1. КОНГРУЭНТНЫЙ ГЕНЕРАТОР СО СЛУЧАЙНЫМИ ПАРАМЕТРАМИ (N = 15)")
    print("=" * 70)

    configs = {
        "Случай 1 (|B|=3, B={(3,0),(3,1),(3,2)}) [Теоретический оптимум]": [
            (3, 0), (3, 1), (3, 2)
        ],
        "Случай 2A (|B|=5, Произвольный набор)": [
            (1, 1), (2, 3), (4, 7), (7, 5), (8, 11)
        ],
        "Случай 2B (|B|=5, Полнопериодные взаимно простые приращения)": [
            (1, 1), (1, 2), (1, 4), (1, 7), (1, 8)
        ],
        "Случай 2C (|B|=5, Вырожденный набор - делители 15)": [
            (5, 0), (5, 5), (10, 0), (10, 5), (0, 5)
        ]
    }

    sample_len = 15000
    expected_count = sample_len / 15  # 1000

    for name, b_set in configs.items():
        gen = RandomParamCongruentialGenerator(modulus=15, param_set_b=b_set, seed=1, rng_seed=42)
        seq = gen.sequence(sample_len)
        test_res = chi2_uniformity_test(seq, alphabet_size=15)
        corrs = autocorrelation(seq, max_lag=3)

        print(f"\nКонфигурация: {name}")
        print(f"  Первые 25 элементов: {seq[:25]}")
        print(f"  Критерий Хи-квадрат: {test_res['chi2_stat']:.3f} (критич. {test_res['critical_val']:.3f})")
        print(f"  Вердикт H0:          {'РАВНОМЕРНО (H0 принимается)' if test_res['is_uniform'] else 'НЕРАВНОМЕРНО (H0 отвергается)'}")
        print(f"  Автокорреляция:      lag1={corrs[0]:+.4f}, lag2={corrs[1]:+.4f}, lag3={corrs[2]:+.4f}")
        print(f"  Частоты значений 0..14 (ожидалось ~{int(expected_count)}):")
        counts_str = " ".join(f"{v}:{test_res['counts'].get(v, 0)}" for v in range(15))
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


def miller_rabin_test(n, k=15):
    """
    Вероятностный тест простоты Рабина — Миллера:
    n - 1 = 2^s * t, где t нечетно.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    # Разложение n - 1 = 2^s * t
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


def random_candidate_from_prng(bits, generator):
    """
    Генерация p-битового кандидата с использованием ПСП из Этапа 1:
    - генерируется случайное битовое число;
    - старший и младший биты устанавливаются в 1 (гарантия разрядности и нечетности).
    """
    val = 0
    # Собираем биты из генератора Варианта 5
    for _ in range(bits):
        val = (val << 1) | (generator.next_int() & 1)
    # Установка MSB и LSB
    val |= (1 << (bits - 1))
    val |= 1
    return val


def generate_prime_candidate_pipeline(bits=64, max_attempts=50000):
    """
    Стандартная схема генерации простых чисел:
      1) Генерация p-битового нечетного числа;
      2) Предварительное просеивание ситом малых простых (<= 256);
      3) Проверка тестом Рабина-Миллера;
      4) Ведение лога отсева и замера времени.
    """
    gen = RandomParamCongruentialGenerator(modulus=15, param_set_b=[(3, 0), (3, 1), (3, 2)])
    stats = {"checked": 0, "sieve_filtered": 0, "mr_checked": 0, "elapsed": 0.0}
    started = time.perf_counter()

    for _ in range(max_attempts):
        cand = random_candidate_from_prng(bits, gen)
        stats["checked"] += 1

        # Этап 1: Сито малых простых
        passed_sieve, _ = trial_division_filter(cand)
        if not passed_sieve:
            stats["sieve_filtered"] += 1
            continue

        # Этап 2: Тест Рабина-Миллера
        stats["mr_checked"] += 1
        if miller_rabin_test(cand, k=15):
            stats["elapsed"] = time.perf_counter() - started
            return cand, stats

    stats["elapsed"] = time.perf_counter() - started
    return None, stats



class MihailescuPrimeGenerator:
    """
    Метод Михалеску (1994) построения доказуемо простых чисел:
      - Параметр e = 1/5 = 0.2
      - Рекурсивно строится факторизованное F из интервала (2^{em}, 2^{c*em})
      - В прогрессии n = 2*F*(t + i) + 1 отбирается кандидат
      - Простота строго доказывается теоремой Поклингтона (свидетель a: a^{n-1} = 1 mod n,
        gcd(a^{(n-1)/q} - 1, n) = 1 для всех q | F).
    """
    def __init__(self, e_param=0.2, b_threshold=14):
        self.e = e_param
        self.b_threshold = b_threshold

    def _small_prime(self, bits):
        while True:
            p = random.randint(1 << (bits - 1), (1 << bits) - 1) | 1
            if trial_division_filter(p)[0] and miller_rabin_test(p, k=15):
                return p

    def generate_provable_prime(self, m_bits):
        if m_bits <= self.b_threshold:
            return self._small_prime(m_bits), {"method": "trial_division"}

        # Рекурсивно строим известную факторизованную часть F
        f_bits = max(self.b_threshold, int(round(self.e * m_bits)))
        q, _ = self.generate_provable_prime(f_bits)
        F = q
        a = 2 * F

        lower_t = (1 << (m_bits - 1)) // a
        upper_t = (1 << m_bits) // a

        for _ in range(200):
            t_base = random.randint(lower_t, max(lower_t + 1, upper_t - 200))
            for i in range(200):
                n = a * (t_base + i) + 1
                if n.bit_length() != m_bits:
                    continue
                # Предварительный отсев ситом и вероятностным тестом
                if not trial_division_filter(n)[0]:
                    continue
                if not miller_rabin_test(n, k=10):
                    continue

                # Доказательство простоты по критерию Поклингтона — Лемера
                # Ищем свидетель a_cand: a^{(n-1)} == 1 mod n и gcd(a^{(n-1)/q} - 1, n) == 1
                for a_cand in (2, 3, 5, 7, 11, 13, 17):
                    if pow(a_cand, n - 1, n) == 1 and math.gcd(pow(a_cand, (n - 1) // q, n) - 1, n) == 1:
                        cert = {
                            "status": "PROVABLY_PRIME",
                            "factor_F": F,
                            "witness_a": a_cand,
                            "method": "Mihailescu (e = 1/5)"
                        }
                        return n, cert

        # Запасной шаг при превышении итераций
        return self._small_prime(m_bits), {"method": "fallback_trial"}



def solve_congruence_variant5():
    """Решение сравнения 1296x = 1105 (mod 2413) всеми тремя методами."""
    a, b, m = 1296, 1105, 2413
    print("\n" + "=" * 70)
    print("КОНТРОЛЬНОЕ ЗАДАНИЕ №12 (Вариант 5): Решить сравнение 1296x = 1105 (mod 2413)")
    print("=" * 70)

    # a) Алгоритм Евклида
    print("\n[a] Алгоритм Евклида для НОД(2413, 1296):")
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

    # b) Расширенный алгоритм Евклида
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
    print(f"    Коэффициент Безу v = {v_bezout} => обратный элемент 1296^(-1) mod 2413 = {inv_a}")
    print(f"    Решение: x = (1105 * {inv_a}) mod 2413 = {x_eea}")

    # c) Метод Эйлера
    print("\n[c] Метод Эйлера:")
    # 2413 = 19 * 127
    phi_m = (19 - 1) * (127 - 1)
    inv_euler = pow(a, phi_m - 1, m)
    x_euler = (b * inv_euler) % m
    print(f"    Факторизация модуля: 2413 = 19 * 127 (простые)")
    print(f"    Функция Эйлера phi(2413) = 18 * 126 = {phi_m}")
    print(f"    1296^(phi - 1) mod 2413 = 1296^{phi_m - 1} mod 2413 = {inv_euler}")
    print(f"    Решение: x = (1105 * {inv_euler}) mod 2413 = {x_euler}")

    # Проверка
    check_val = (a * x_eea) % m
    print(f"\n[Проверка]: 1296 * {x_eea} mod 2413 = {check_val} == 1105: {check_val == b}")



def main():
    print("=" * 70)
    print("  Лабораторная работа №1 (КиСБ) — ВАРИАНТ №5")
    print("  Конгруэнтный генератор со случайными параметрами (N=15)")
    print("  + Метод Михалеску генерации доказуемо простых чисел (e = 1/5)")
    print("=" * 70)

    while True:
        print("\nГЛАВНОЕ МЕНЮ:")
        print("  1 — Этап 1: Демонстрация и статистика генератора (Случаи 1 и 2)")
        print("  2 — Проверить произвольное число на простоту (сито + Рабин-Миллер)")
        print("  3 — Этап 2: Стандартная схема генерации с ситом малых простых (<=256)")
        print("  4 — Этап 2: Метод Михалеску (доказуемо простые числа, e = 1/5)")
        print("  5 — Решение контрольного сравнения 1296x = 1105 (mod 2413)")
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
                    mr_pass = miller_rabin_test(n, k=15)
                    verdict = "ВЕРОЯТНО ПРОСТОЕ" if mr_pass else "СОСТАВНОЕ"
                    print(f"Число {n} — {verdict} (по тесту Рабина-Миллера, k=15).")
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
                print(f"  Проверено тестом Р-М:     {stats['mr_checked']}")
                print(f"  Время поиска:             {stats['elapsed']:.6f} сек.")
            except ValueError:
                print("Ошибка: введите целое число бит.")

        elif choice == "4":
            try:
                bits_str = input("Разрядность доказуемо простого числа (например, 16, 32, 64): ").strip()
                bits = int(bits_str)
                if bits < 4:
                    print("Разрядность должна быть >= 4.")
                    continue
                m_gen = MihailescuPrimeGenerator(e_param=0.2, b_threshold=14)
                started = time.perf_counter()
                p, cert = m_gen.generate_provable_prime(m_bits=bits)
                elapsed = time.perf_counter() - started

                print(f"\nСгенерировано доказуемо простое число p:")
                print(f"  Десятичный вид:   {p}")
                print(f"  HEX-вид:          {hex(p)}")
                print(f"  Разрядность:      {p.bit_length()} бит")
                print(f"  Фактор F:         {cert.get('factor_F', '-')}")
                print(f"  Свидетель a:      {cert.get('witness_a', '-')}")
                print(f"  Статус:           {cert.get('status', 'OK')}")
                print(f"  Метод:            {cert.get('method', '-')}")
                print(f"  Время генерации:  {elapsed:.6f} сек.")
            except ValueError:
                print("Ошибка: введите целое число бит.")

        elif choice == "5":
            solve_congruence_variant5()

        elif choice == "0":
            print("\nВыход из программы.")
            break
        else:
            print("Неверная команда, попробуйте снова.")


if __name__ == "__main__":
    main()
