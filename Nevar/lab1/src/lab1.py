import itertools
import math
import sys
import time
from collections import Counter
from datetime import datetime

import matplotlib.pyplot as plt


def timestamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def chi_square_critical_95(df):
    table = {
        1: 3.841459,
        2: 5.991465,
        3: 7.814728,
        4: 9.487729,
        14: 23.684791,
        224: 259.914409,
    }
    if df in table:
        return table[df]
    if df > 30:
        return df + 1.644854 * math.sqrt(2.0 * df) + 2.0 * (1.644854 ** 2) / 3.0
    return None


def frequency_test(sequence, alphabet_size):
    n = len(sequence)
    if n == 0 or alphabet_size <= 0:
        return {
            "counts": [],
            "expected": 0.0,
            "chi_square": 0.0,
            "degrees_of_freedom": 0,
            "critical": None,
            "accepted": False,
            "valid": False,
        }
    counts = [0] * alphabet_size
    for value in sequence:
        if 0 <= value < alphabet_size:
            counts[value] += 1
    expected = n / alphabet_size
    chi = sum((count - expected) ** 2 / expected for count in counts)
    degrees = alphabet_size - 1
    critical = chi_square_critical_95(degrees)
    valid = expected >= 5.0 and critical is not None
    return {
        "counts": counts,
        "expected": expected,
        "chi_square": chi,
        "degrees_of_freedom": degrees,
        "critical": critical,
        "accepted": valid and chi <= critical,
        "valid": valid,
    }


def binary_runs_test(bits):
    if not bits:
        return {"runs": 0, "expected": 0.0, "variance": 0.0, "z": 0.0, "accepted": False, "valid": False}
    n0 = bits.count(0)
    n1 = bits.count(1)
    n = float(len(bits))
    runs = 1 + sum(1 for i in range(1, len(bits)) if bits[i] != bits[i - 1])
    expected = 1.0 + 2.0 * n0 * n1 / n
    variance = 0.0
    if n > 1:
        variance = 2.0 * n0 * n1 * (2.0 * n0 * n1 - n) / (n * n * (n - 1.0))
    z = (runs - expected) / math.sqrt(variance) if variance > 0 else 0.0
    valid = n0 > 0 and n1 > 0 and variance > 0
    return {
        "runs": runs,
        "expected": expected,
        "variance": variance,
        "z": z,
        "accepted": valid and abs(z) <= 1.96,
        "valid": valid,
    }


def serial_pairs_test(sequence, alphabet_size):
    counts = Counter()
    total = 0
    for i in range(0, len(sequence) - 1, 2):
        counts[(sequence[i], sequence[i + 1])] += 1
        total += 1
    if total == 0:
        return {
            "counts": counts,
            "expected": 0.0,
            "chi_square": 0.0,
            "degrees_of_freedom": 0,
            "critical": None,
            "accepted": False,
            "valid": False,
        }
    categories = alphabet_size * alphabet_size
    expected = total / categories
    chi = 0.0
    for a in range(alphabet_size):
        for b in range(alphabet_size):
            observed = counts[(a, b)]
            chi += (observed - expected) ** 2 / expected
    df = categories - 1
    critical = chi_square_critical_95(df)
    valid = expected >= 5.0 and critical is not None
    return {
        "counts": counts,
        "expected": expected,
        "chi_square": chi,
        "degrees_of_freedom": df,
        "critical": critical,
        "accepted": valid and chi <= critical,
        "valid": valid,
    }


def binary_autocorrelation(bits, max_lag):
    if not bits:
        return {"values": [], "max_abs": 0.0}
    limit = min(max_lag, len(bits) - 1)
    transformed = [1.0 if bit else -1.0 for bit in bits]
    values = []
    max_abs = 0.0
    for lag in range(1, limit + 1):
        pairs = len(bits) - lag
        total = sum(transformed[i] * transformed[i + lag] for i in range(pairs))
        value = total / pairs
        values.append(value)
        max_abs = max(max_abs, abs(value))
    return {"values": values, "max_abs": max_abs}


def general_autocorrelation(sequence, max_lag):
    if not sequence:
        return {"values": [], "max_abs": 0.0}
    mean = sum(sequence) / len(sequence)
    centered = [x - mean for x in sequence]
    values = []
    max_abs = 0.0
    for lag in range(1, min(max_lag, len(sequence) - 1) + 1):
        left = centered[:-lag]
        right = centered[lag:]
        left_energy = sum(x * x for x in left)
        right_energy = sum(x * x for x in right)
        denominator = math.sqrt(left_energy * right_energy)
        value = sum(left[i] * right[i] for i in range(len(left))) / denominator if denominator > 0 else 0.0
        values.append(value)
        max_abs = max(max_abs, abs(value))
    return {"values": values, "max_abs": max_abs}


def evaluate_binary_sequence(bits):
    return {
        "frequency": frequency_test(bits, 2),
        "runs": binary_runs_test(bits),
        "serial": serial_pairs_test(bits, 2),
        "autocorrelation": binary_autocorrelation(bits, 12),
    }


def evaluate_congruential_sequence(sequence, modulus):
    return {
        "frequency": frequency_test(sequence, modulus),
        "serial": serial_pairs_test(sequence, modulus),
        "autocorrelation": general_autocorrelation(sequence, 12),
    }


def binary_prefix(bits, count):
    return "".join("1" if bit else "0" for bit in bits[:count])


class ParameterSelector:
    def __init__(self, size, multiplier=1, increment=1, start=0):
        self.size = size
        self.multiplier = multiplier
        self.increment = increment
        self.start = start % size
        self.position = self.start

    def reset(self, start=None):
        if start is not None:
            self.start = start % self.size
        self.position = self.start

    def next_index(self):
        current = self.position
        self.position = (self.multiplier * self.position + self.increment) % self.size
        return current

    def period(self):
        self.reset()
        start = self.position
        seen = set()
        period = 0
        while self.position not in seen:
            seen.add(self.position)
            self.next_index()
            period += 1
            if self.position == start:
                return period
        return period


class CongruentialRandomParametersGenerator:
    MODULUS = 15
    FIXED_B = ((3, 0), (3, 1), (3, 2))
    ARBITRARY_B = ((13, 8), (7, 1), (8, 12), (2, 0), (1, 11))

    def __init__(self, b_set, x0=0, order=None, selector_multiplier=1, selector_increment=1, selector_start=0):
        self.b_set = tuple(b_set)
        self.x0 = x0 % self.MODULUS
        self.order = tuple(order) if order is not None else self.b_set
        self.selector = ParameterSelector(
            len(self.order),
            selector_multiplier,
            selector_increment,
            selector_start,
        )
        self.x = self.x0

    def reset(self, x0=None, selector_start=None):
        if x0 is not None:
            self.x0 = x0 % self.MODULUS
        self.x = self.x0
        self.selector.reset(selector_start)

    def next(self):
        index = self.selector.next_index()
        a, b = self.order[index]
        self.x = (a * self.x + b) % self.MODULUS
        return self.x

    def generate(self, length):
        return [self.next() for _ in range(length)]

    def current_state(self):
        return self.x, self.selector.position

    def detect_period(self):
        self.reset()
        start_state = self.current_state()
        seen = {start_state: 0}
        step = 0
        max_states = self.MODULUS * len(self.order)
        while True:
            self.next()
            step += 1
            state = self.current_state()
            if state in seen:
                return seen[state], step - seen[state]
            seen[state] = step
            if step > max_states:
                return 0, 0


def selector_parameter_candidates(size):
    candidates = []
    for multiplier in range(size):
        for increment in range(size):
            if math.gcd(increment, size) != 1:
                continue
            selector = ParameterSelector(size, multiplier, increment, 0)
            if selector.period() == size:
                candidates.append((multiplier, increment))
    return candidates


def best_configuration_for_b(b_set):
    best = None
    selector_candidates = selector_parameter_candidates(len(b_set))
    for order in itertools.permutations(b_set):
        for multiplier, increment in selector_candidates:
            for selector_start in range(len(order)):
                for x0 in range(CongruentialRandomParametersGenerator.MODULUS):
                    generator = CongruentialRandomParametersGenerator(
                        b_set,
                        x0=x0,
                        order=order,
                        selector_multiplier=multiplier,
                        selector_increment=increment,
                        selector_start=selector_start,
                    )
                    tau, period = generator.detect_period()
                    candidate = (period, -tau, -x0, -selector_start, order, multiplier, increment)
                    if best is None or candidate > best[0]:
                        best = (candidate, {
                            "period": period,
                            "tau": tau,
                            "x0": x0,
                            "selector_start": selector_start,
                            "order": order,
                            "selector_multiplier": multiplier,
                            "selector_increment": increment,
                        })
    return best[1]


def print_binary_statistics(stats, title):
    frequency = stats["frequency"]
    runs = stats["runs"]
    serial = stats["serial"]
    autocorrelation = stats["autocorrelation"]
    print(title)
    print(
        f"Частотный тест: 0={frequency['counts'][0]}, 1={frequency['counts'][1]}, "
        f"chi^2={frequency['chi_square']:.6f}, "
        f"результат={'принято' if frequency['accepted'] else 'отклонено'}"
    )
    print(
        f"Тест серий: R={runs['runs']}, E(R)={runs['expected']:.6f}, "
        f"Var(R)={runs['variance']:.6f}, z={runs['z']:.6f}, "
        f"результат={'принято' if runs['accepted'] else 'отклонено'}"
    )
    print(
        f"Серийный тест пар: 00={serial['counts'][(0, 0)]}, 01={serial['counts'][(0, 1)]}, "
        f"10={serial['counts'][(1, 0)]}, 11={serial['counts'][(1, 1)]}, "
        f"chi^2={serial['chi_square']:.6f}, "
        f"результат={'принято' if serial['accepted'] else 'отклонено'}"
    )
    values = " ".join(f"{value:.6f}" for value in autocorrelation["values"])
    print(f"Автокорреляция, лаги 1..12: {values}")
    print(f"Максимум |rho|={autocorrelation['max_abs']:.6f}")


def print_congruential_statistics(stats, modulus):
    frequency = stats["frequency"]
    serial = stats["serial"]
    auto = stats["autocorrelation"]
    frequency_result = "не применяется" if not frequency["valid"] else ("принято" if frequency["accepted"] else "отклонено")
    serial_result = "не применяется" if not serial["valid"] else ("принято" if serial["accepted"] else "отклонено")
    print(
        f"Частотный тест по {modulus} значениям: chi^2={frequency['chi_square']:.6f}, "
        f"df={frequency['degrees_of_freedom']}, критическое={frequency['critical']:.6f}, "
        f"результат={frequency_result}, E={frequency['expected']:.6f}"
    )
    print(
        f"Серийный тест пар: chi^2={serial['chi_square']:.6f}, "
        f"df={serial['degrees_of_freedom']}, критическое={serial['critical']:.6f}, "
        f"результат={serial_result}, E={serial['expected']:.6f}"
    )
    values = " ".join(f"{value:.6f}" for value in auto["values"])
    print(f"Автокорреляция, лаги 1..12: {values}")
    print(f"Максимум |rho|={auto['max_abs']:.6f}")


def congruential_parameter_index_sequence(configuration, count):
    order = configuration["order"]
    selector = ParameterSelector(
        len(order),
        configuration["selector_multiplier"],
        configuration["selector_increment"],
        configuration["selector_start"],
    )
    result = []
    for _ in range(count):
        result.append(order[selector.next_index()])
    return result


def make_congruential_graphs(experiments):
    cases = sorted(set(row["case"] for row in experiments))

    plt.figure(figsize=(10, 6))
    for case in cases:
        rows = [row for row in experiments if row["case"] == case and row["expected_frequency"] >= 5]
        rows.sort(key=lambda x: x["length"])
        x = [row["length"] for row in rows]
        y = [row["frequency_chi_square"] for row in rows]
        plt.plot(x, y, marker="o", label=case)
    plt.axhline(23.684791, linestyle="--", label="95% critical value, df=14")
    plt.xlabel("Длина последовательности")
    plt.ylabel("Статистика chi^2")
    plt.title("Частотный тест конгруэнтного генератора")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show(block=False)

    plt.figure(figsize=(10, 6))
    for case in cases:
        rows = [row for row in experiments if row["case"] == case]
        rows.sort(key=lambda x: x["length"])
        x = [row["length"] for row in rows]
        y = [row["max_abs_rho"] for row in rows]
        plt.plot(x, y, marker="o", label=case)
    plt.xlabel("Длина последовательности")
    plt.ylabel("max |rho|")
    plt.title("Изменение автокорреляции конгруэнтного генератора")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show(block=False)

    plt.figure(figsize=(10, 6))
    for case in cases:
        rows = [row for row in experiments if row["case"] == case]
        rows.sort(key=lambda x: x["length"])
        x = [row["length"] for row in rows]
        y = [row["unique_values"] for row in rows]
        plt.plot(x, y, marker="o", label=case)
    plt.xlabel("Длина последовательности")
    plt.ylabel("Число различных значений")
    plt.title("Изменение охвата алфавита")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show(block=False)


def run_congruential_part(length):
    print("=== Часть 1A: Конгруэнтный генератор со случайными параметрами, вариант 5 ===")
    print("Модуль N = 15")
    print("Формула: x_t = (a_t*x_(t-1) + b_t) mod 15")
    print("Вариант 5 рассматривает фиксированное B={(3,0),(3,1),(3,2)} и произвольное B, |B|=5")

    fixed = best_configuration_for_b(CongruentialRandomParametersGenerator.FIXED_B)
    arbitrary = best_configuration_for_b(CongruentialRandomParametersGenerator.ARBITRARY_B)

    for name, b_set, configuration in (
        ("fixed_B", CongruentialRandomParametersGenerator.FIXED_B, fixed),
        ("arbitrary_B", CongruentialRandomParametersGenerator.ARBITRARY_B, arbitrary),
    ):
        print(f"\nСлучай: {name}")
        print(f"B = {b_set}")
        print(f"Порядок B: {configuration['order']}")
        print(f"x0 = {configuration['x0']}")
        print(f"Начальная позиция селектора = {configuration['selector_start']}")
        print(f"Параметры селектора: alpha={configuration['selector_multiplier']}, gamma={configuration['selector_increment']}")
        print(f"tau = {configuration['tau']}")
        print(f"Максимальный найденный период: {configuration['period']}")
        print(f"Теоретическая верхняя граница совместного состояния: {15 * len(b_set)}")

    fixed_generator = CongruentialRandomParametersGenerator(
        fixed["order"],
        fixed["x0"],
        fixed["order"],
        fixed["selector_multiplier"],
        fixed["selector_increment"],
        fixed["selector_start"],
    )
    arbitrary_generator = CongruentialRandomParametersGenerator(
        arbitrary["order"],
        arbitrary["x0"],
        arbitrary["order"],
        arbitrary["selector_multiplier"],
        arbitrary["selector_increment"],
        arbitrary["selector_start"],
    )
    fixed_length = fixed["period"] if length == 0 else length
    arbitrary_length = arbitrary["period"] if length == 0 else length
    fixed_sequence = fixed_generator.generate(fixed_length)
    arbitrary_sequence = arbitrary_generator.generate(arbitrary_length)

    print("\nПервые параметры и значения для фиксированного B:")
    print(congruential_parameter_index_sequence(fixed, min(20, fixed_length)))
    print(fixed_sequence[:40])
    print_congruential_statistics(evaluate_congruential_sequence(fixed_sequence, 15), 15)

    print("\nПервые параметры и значения для произвольного B:")
    print(congruential_parameter_index_sequence(arbitrary, min(20, arbitrary_length)))
    print(arbitrary_sequence[:40])
    print_congruential_statistics(evaluate_congruential_sequence(arbitrary_sequence, 15), 15)

    rows = []
    x0_rows = []
    length_sweep = (75, 150, 375, 750, 1125, 2250, 4500)

    for case, b_set, configuration in (
        ("fixed_B", CongruentialRandomParametersGenerator.FIXED_B, fixed),
        ("arbitrary_B", CongruentialRandomParametersGenerator.ARBITRARY_B, arbitrary),
    ):
        for x0 in range(15):
            generator = CongruentialRandomParametersGenerator(
                b_set,
                x0=x0,
                order=configuration["order"],
                selector_multiplier=configuration["selector_multiplier"],
                selector_increment=configuration["selector_increment"],
                selector_start=configuration["selector_start"],
            )
            tau, period = generator.detect_period()
            sequence = generator.generate(max(1, min(4500, max(period, 75))))
            stats = evaluate_congruential_sequence(sequence, 15)
            x0_rows.append({
                "case": case,
                "x0": x0,
                "tau": tau,
                "period": period,
                "sample_length": len(sequence),
                "frequency_chi_square": stats["frequency"]["chi_square"],
                "frequency_expected": stats["frequency"]["expected"],
                "pairs_chi_square": stats["serial"]["chi_square"],
                "pairs_expected": stats["serial"]["expected"],
                "max_abs_rho": stats["autocorrelation"]["max_abs"],
                "unique_values": len(set(sequence)),
            })
        for current_length in length_sweep:
            generator = CongruentialRandomParametersGenerator(
                b_set,
                x0=configuration["x0"],
                order=configuration["order"],
                selector_multiplier=configuration["selector_multiplier"],
                selector_increment=configuration["selector_increment"],
                selector_start=configuration["selector_start"],
            )
            sequence = generator.generate(current_length)
            stats = evaluate_congruential_sequence(sequence, 15)
            rows.append({
                "case": case,
                "length": current_length,
                "x0": configuration["x0"],
                "period": configuration["period"],
                "frequency_chi_square": stats["frequency"]["chi_square"],
                "expected_frequency": stats["frequency"]["expected"],
                "frequency_accepted": stats["frequency"]["accepted"],
                "pairs_chi_square": stats["serial"]["chi_square"],
                "expected_pairs": stats["serial"]["expected"],
                "pairs_accepted": stats["serial"]["accepted"],
                "max_abs_rho": stats["autocorrelation"]["max_abs"],
                "unique_values": len(set(sequence)),
            })

    make_congruential_graphs(rows)

    print("\nТаблица влияния x0 для конгруэнтного генератора:")
    print("case\tx0\ttau\tperiod\tchi2\tpairs_chi2\tmax|rho|\tunique")
    for row in x0_rows:
        print(
            f"{row['case']}\t{row['x0']}\t{row['tau']}\t{row['period']}\t"
            f"{row['frequency_chi_square']:.6f}\t{row['pairs_chi_square']:.6f}\t"
            f"{row['max_abs_rho']:.6f}\t{row['unique_values']}"
        )

    return arbitrary


class LFSR:
    DEGREE = 12
    MASK = (1 << DEGREE) - 1

    def __init__(self, seed):
        self.state_value = seed & self.MASK
        if self.state_value == 0:
            self.state_value = 1

    def next(self):
        out = self.state_value & 1
        feedback = ((self.state_value >> 6) ^ (self.state_value >> 4) ^ (self.state_value >> 1) ^ self.state_value) & 1
        self.state_value >>= 1
        self.state_value |= feedback << (self.DEGREE - 1)
        return out

    @property
    def state(self):
        return self.state_value


def generate_lfsr_bits(length, seed):
    lfsr = LFSR(seed)
    return [lfsr.next() for _ in range(length)]


def detect_lfsr_period(seed):
    lfsr = LFSR(seed)
    start = lfsr.state
    period = 0
    while True:
        lfsr.next()
        period += 1
        if period > (1 << LFSR.DEGREE):
            return 0
        if lfsr.state == start:
            return period


def make_lfsr_graph(rows):
    seeds = sorted(set(row["seed"] for row in rows))

    plt.figure(figsize=(10, 6))
    for seed in seeds:
        data = sorted((row for row in rows if row["seed"] == seed), key=lambda x: x["length"])
        plt.plot([row["length"] for row in data], [row["frequency_chi_square"] for row in data], marker="o", label=f"seed={seed}")
    plt.axhline(3.841459, linestyle="--", label="95% critical value, df=1")
    plt.xlabel("Длина последовательности")
    plt.ylabel("chi^2")
    plt.title("Частотный тест LFSR")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show(block=False)

    plt.figure(figsize=(10, 6))
    for seed in seeds:
        data = sorted((row for row in rows if row["seed"] == seed), key=lambda x: x["length"])
        plt.plot([row["length"] for row in data], [row["max_abs_rho"] for row in data], marker="o", label=f"seed={seed}")
    plt.xlabel("Длина последовательности")
    plt.ylabel("max |rho|")
    plt.title("Автокорреляция LFSR")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show(block=False)


def run_lfsr_part(requested_length, seed):
    if seed == 0:
        seed = 1
    print("\n=== Часть 1B: LFSR, пункт 11, вариант 5 ===")
    print("g(x) = x^12 + x^6 + x^4 + x + 1")
    print(f"seed = {seed}")
    print(f"Теоретический максимальный период = {(1 << 12) - 1}")
    period = detect_lfsr_period(seed)
    print(f"Фактически обнаруженный период = {period}")
    length = period if requested_length == 0 else requested_length
    bits = generate_lfsr_bits(length, seed)
    print(f"Длина сформированной последовательности = {len(bits)}")
    print(f"Первые 64 бита = {binary_prefix(bits, 64)}")
    print_binary_statistics(evaluate_binary_sequence(bits), "Статистические тесты основной выборки")

    rows = []
    seeds = (1, 0xACE, 0xFFF)
    lengths = (256, 1024, 4095)
    for current_seed in seeds:
        for current_length in lengths:
            sample = generate_lfsr_bits(current_length, current_seed)
            stats = evaluate_binary_sequence(sample)
            rows.append({
                "seed": current_seed,
                "length": current_length,
                "period": detect_lfsr_period(current_seed),
                "frequency_chi_square": stats["frequency"]["chi_square"],
                "frequency_accepted": stats["frequency"]["accepted"],
                "runs_z": stats["runs"]["z"],
                "runs_accepted": stats["runs"]["accepted"],
                "pairs_chi_square": stats["serial"]["chi_square"],
                "pairs_accepted": stats["serial"]["accepted"],
                "max_abs_rho": stats["autocorrelation"]["max_abs"],
            })
            print(
                f"seed={current_seed}, N={current_length}: "
                f"chi2={stats['frequency']['chi_square']:.6f}, "
                f"runs_z={stats['runs']['z']:.6f}, "
                f"pairs_chi2={stats['serial']['chi_square']:.6f}, "
                f"max_abs_rho={stats['autocorrelation']['max_abs']:.6f}"
            )
    make_lfsr_graph(rows)


class Stage1RandomSource:
    def __init__(self, configuration, b_set=None):
        selected_b = CongruentialRandomParametersGenerator.ARBITRARY_B if b_set is None else tuple(b_set)
        self.generator = CongruentialRandomParametersGenerator(
            selected_b,
            x0=configuration["x0"],
            order=configuration["order"],
            selector_multiplier=configuration["selector_multiplier"],
            selector_increment=configuration["selector_increment"],
            selector_start=configuration["selector_start"],
        )
        self.modulus = 15

    def next_value(self):
        return self.generator.next()

    def get_bits(self, bit_count):
        if bit_count <= 0:
            return 0
        digit_count = max(1, math.ceil(bit_count / math.log2(self.modulus)))
        base_power = self.modulus ** digit_count
        target = 1 << bit_count
        limit = (base_power // target) * target
        if limit == 0:
            raise ValueError("Недостаточная длина блока для получения требуемого числа бит")
        while True:
            value = 0
            for _ in range(digit_count):
                value = value * self.modulus + self.next_value()
            if value < limit:
                return value % target

    def exact_bits(self, bit_count):
        if bit_count <= 1:
            return 1
        return self.get_bits(bit_count - 1) | (1 << (bit_count - 1))

    def uniform_range(self, low, high):
        if high <= low:
            return low
        width = high - low + 1
        bits = width.bit_length()
        while True:
            value = self.get_bits(bits)
            if value < width:
                return low + value


def sieve_primes(limit):
    composite = bytearray(limit + 1)
    primes = []
    for p in range(2, limit + 1):
        if not composite[p]:
            primes.append(p)
            if p * p <= limit:
                composite[p * p:limit + 1:p] = b"\x01" * (((limit - p * p) // p) + 1)
    return primes


def trial_prime(n, primes):
    if n < 2:
        return False
    for p in primes:
        if p * p > n:
            break
        if n % p == 0:
            return n == p
    return True


def miller_rabin_round(n, a, d, s):
    x = pow(a, d, n)
    if x == 1 or x == n - 1:
        return True
    for _ in range(1, s):
        x = (x * x) % n
        if x == n - 1:
            return True
    return False


def probable_prime(n):
    bases = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    if n < 2:
        return False
    for p in bases:
        if n == p:
            return True
        if n % p == 0:
            return False
    d = n - 1
    s = 0
    while d & 1 == 0:
        d >>= 1
        s += 1
    for a in bases:
        if a >= n:
            continue
        if not miller_rabin_round(n, a, d, s):
            return False
    return True


def pocklington_proof(n, factor_f, factors):
    if n < 3 or n % 2 == 0:
        return n == 2
    if factor_f * factor_f <= n:
        return False
    exponent = n - 1
    for a in range(2, 257):
        if a >= n or math.gcd(a, n) != 1:
            continue
        if pow(a, exponent, n) != 1:
            continue
        all_factors_ok = True
        for q in factors:
            if exponent % q != 0:
                all_factors_ok = False
                break
            part = pow(a, exponent // q, n)
            if math.gcd(part - 1, n) != 1:
                all_factors_ok = False
                break
        if all_factors_ok:
            return True
    return False


def format_factorization(factors):
    parts = []
    for factor in sorted(factors):
        power = factors[factor]
        parts.append(str(factor) if power == 1 else f"{factor}^{power}")
    return " * ".join(parts)


def generate_small_prime(bits_count, source, primes, stats=None):
    if bits_count < 2:
        return 2
    while True:
        n = source.exact_bits(bits_count) | 1
        if stats is not None:
            stats["factor_candidates"] += 1
        divisible = False
        for p in primes:
            if p * p > n:
                break
            if n % p == 0:
                divisible = True
                break
        if not divisible:
            return n
        if stats is not None:
            stats["factor_screened"] += 1


def choose_factor_f(m, source, primes, e_num=1, e_den=5):
    q_bits = max(2, (m * e_num + e_den - 1) // e_den)
    target_bits = m // 2 + 2
    factor_f = 1
    factors = Counter()
    factor_candidates = 0
    factor_screened = 0
    attempts = 0
    while factor_f.bit_length() <= target_bits:
        attempts += 1
        local_stats = {"factor_candidates": 0, "factor_screened": 0}
        q = generate_small_prime(q_bits, source, primes, local_stats)
        factor_candidates += local_stats["factor_candidates"]
        factor_screened += local_stats["factor_screened"]
        factor_f *= q
        factors[q] += 1
        if factor_f >= (1 << target_bits):
            break
    return factor_f, dict(factors), {
        "factor_attempts": attempts,
        "factor_candidates": factor_candidates,
        "factor_screened": factor_screened,
        "q_bits": q_bits,
    }


def standard_candidate_pipeline(bits, source, primes, max_attempts=5000):
    start_time = time.perf_counter()
    started_at = timestamp()
    total = 0
    small_screened = 0
    miller_rejected = 0
    accepted = 0
    candidate_rows = []
    start_bit = 1 << (bits - 1)
    n = 0
    while total < max_attempts:
        total += 1
        n = source.get_bits(bits) | start_bit | 1
        status = "passed_small_primes"
        if any(n % p == 0 for p in primes if p != n):
            small_screened += 1
            status = "small_prime_rejected"
        elif not probable_prime(n):
            miller_rejected += 1
            status = "miller_rabin_rejected"
        else:
            accepted += 1
            status = "probable_prime_found"
        candidate_rows.append({
            "timestamp": timestamp(),
            "candidate_index": total,
            "candidate": n,
            "bit_length": n.bit_length(),
            "status": status,
            "elapsed_seconds": time.perf_counter() - start_time,
        })
        if accepted:
            break
    return {
        "started_at": started_at,
        "finished_at": timestamp(),
        "elapsed_seconds": time.perf_counter() - start_time,
        "total": total,
        "small_screened": small_screened,
        "miller_rejected": miller_rejected,
        "accepted": accepted,
        "candidate": n,
        "candidate_rows": candidate_rows,
    }


class MikhaleskuGenerator:
    def __init__(self, source, small_prime_bound=2000, e_numerator=1, e_denominator=5):
        self.source = source
        self.e_num = e_numerator
        self.e_den = e_denominator
        self.primes = sieve_primes(small_prime_bound)

    def generate(self, m):
        start_time = time.perf_counter()
        started_at = timestamp()
        summary = {
            "candidate_total": 0,
            "small_prime_rejected": 0,
            "miller_rabin_rejected": 0,
            "pocklington_rejected": 0,
            "accepted": 0,
            "factor_build_attempts": 0,
            "factor_candidates": 0,
            "factor_screened": 0,
        }
        candidate_rows = []
        factor_f = 0
        factors = {}
        t = 0
        while True:
            factor_f, factors, factor_stats = choose_factor_f(
                m,
                self.source,
                self.primes,
                self.e_num,
                self.e_den,
            )
            summary["factor_build_attempts"] += 1
            summary["factor_candidates"] += factor_stats["factor_candidates"]
            summary["factor_screened"] += factor_stats["factor_screened"]
            if factor_f * factor_f <= (1 << m):
                continue
            lower = ((1 << (m - 1)) - 1 + 2 * factor_f - 1) // (2 * factor_f)
            upper = ((1 << m) - 2) // (2 * factor_f)
            if upper < lower:
                continue
            t = self.source.uniform_range(lower, upper)
            local_limit = min(512, max(64, upper - t + 1))
            for offset in range(local_limit):
                ti = t + offset
                if ti > upper:
                    break
                n = 2 * factor_f * ti + 1
                if n.bit_length() != m:
                    continue
                summary["candidate_total"] += 1
                status = "passed_small_primes"
                small_divisor = None
                for p in self.primes:
                    if n == p:
                        break
                    if n % p == 0:
                        small_divisor = p
                        break
                if small_divisor is not None:
                    summary["small_prime_rejected"] += 1
                    status = "small_prime_rejected"
                elif not probable_prime(n):
                    summary["miller_rabin_rejected"] += 1
                    status = "miller_rabin_rejected"
                elif not pocklington_proof(n, factor_f, factors):
                    summary["pocklington_rejected"] += 1
                    status = "pocklington_rejected"
                else:
                    summary["accepted"] += 1
                    candidate_rows.append({
                        "timestamp": timestamp(),
                        "candidate_index": summary["candidate_total"],
                        "candidate": n,
                        "bit_length": n.bit_length(),
                        "status": status,
                        "small_divisor": "",
                        "elapsed_seconds": time.perf_counter() - start_time,
                    })
                    summary["elapsed_seconds"] = time.perf_counter() - start_time
                    summary["started_at"] = started_at
                    summary["finished_at"] = timestamp()
                    return {
                        "prime": n,
                        "F": factor_f,
                        "factorization": factors,
                        "bit_length": m,
                        "t": ti,
                        "summary": summary,
                        "candidate_rows": candidate_rows,
                    }
                candidate_rows.append({
                    "timestamp": timestamp(),
                    "candidate_index": summary["candidate_total"],
                    "candidate": n,
                    "bit_length": n.bit_length(),
                    "status": status,
                    "small_divisor": "" if small_divisor is None else small_divisor,
                    "elapsed_seconds": time.perf_counter() - start_time,
                })
            if summary["candidate_total"] > 200000:
                raise RuntimeError("Не удалось получить доказанно простое число за разумное число кандидатов")


def make_prime_graph(standard_result, mikhalesku_result):
    labels = ["малые простые", "Miller-Rabin", "Поколлингтон", "принято"]
    standard_values = [
        standard_result["small_screened"],
        standard_result["miller_rejected"],
        0,
        standard_result["accepted"],
    ]
    m = mikhalesku_result["summary"]
    mikh_values = [m["small_prime_rejected"], m["miller_rabin_rejected"], m["pocklington_rejected"], m["accepted"]]
    x = range(len(labels))
    width = 0.38
    plt.figure(figsize=(10, 6))
    plt.bar([i - width / 2 for i in x], standard_values, width=width, label="Стандартная схема")
    plt.bar([i + width / 2 for i in x], mikh_values, width=width, label="Михалеску")
    plt.xticks(list(x), labels)
    plt.ylabel("Количество кандидатов")
    plt.title("Лог фильтрации кандидатов в простые числа")
    plt.grid(axis="y", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show(block=False)


def run_prime_part(bits, arbitrary_configuration):
    print("\n=== Часть 2: Проверка простоты и генерация больших простых чисел ===")
    print("Целевой метод варианта 5: Михалеску, e=1/5")
    print(f"Размер кандидата: {bits} бит")
    if bits < 16:
        raise ValueError("Для этой реализации размер простого числа должен быть не меньше 16 бит")

    primes = sieve_primes(2000)
    source = Stage1RandomSource(arbitrary_configuration)

    print("\nСтандартная схема кандидата на базе генератора этапа 1")
    standard = standard_candidate_pipeline(bits, source, primes, max_attempts=5000)
    print(f"Время: {standard['elapsed_seconds']:.6f} с")
    print(f"Всего кандидатов: {standard['total']}")
    print(f"Отсеяно малыми простыми: {standard['small_screened']}")
    print(f"Отклонено Miller-Rabin: {standard['miller_rejected']}")
    print(f"Найден вероятно простой кандидат: {standard['candidate']}")

    mikh_source = Stage1RandomSource(arbitrary_configuration)
    generator = MikhaleskuGenerator(mikh_source, small_prime_bound=2000, e_numerator=1, e_denominator=5)
    result = generator.generate(bits)
    summary = result["summary"]
    prime = result["prime"]
    factor_f = result["F"]
    factors = result["factorization"]
    t = result["t"]

    print("\nМетод Михалеску")
    print(f"Найдено доказанно простое число: {prime}")
    print(f"Разрядность: {result['bit_length']}")
    print(f"F = {factor_f}")
    print(f"Факторизация F = {format_factorization(factors)}")
    print(f"t = {t}")
    print(f"Проверка n = 2*F*t + 1: {2 * factor_f * t + 1 == prime}")
    print(f"Проверка n mod (2F): {prime % (2 * factor_f)}")
    print(f"Проверка F^2 > n: {factor_f * factor_f > prime}")
    print(f"Miller-Rabin финального кандидата: {'пройден' if probable_prime(prime) else 'не пройден'}")
    print(f"Время: {summary['elapsed_seconds']:.6f} с")
    print(f"Всего кандидатов n: {summary['candidate_total']}")
    print(f"Отсеяно малыми простыми: {summary['small_prime_rejected']}")
    print(f"Отклонено Miller-Rabin: {summary['miller_rabin_rejected']}")
    print(f"Отклонено Поколлингтоном: {summary['pocklington_rejected']}")
    print(f"Принято: {summary['accepted']}")
    print(f"Проверок при построении F: {summary['factor_candidates']}")
    print(f"Отсеяно при построении F: {summary['factor_screened']}")

    make_prime_graph(standard, result)


def main():
    congruential_length = 0
    lfsr_length = 4095
    lfsr_seed = 1
    prime_bits = 64
    if len(sys.argv) > 1:
        congruential_length = int(sys.argv[1])
    if len(sys.argv) > 2:
        lfsr_length = int(sys.argv[2])
    if len(sys.argv) > 3:
        lfsr_seed = int(sys.argv[3])
    if len(sys.argv) > 4:
        prime_bits = int(sys.argv[4])

    arbitrary_configuration = run_congruential_part(congruential_length)
    run_lfsr_part(lfsr_length, lfsr_seed)
    run_prime_part(prime_bits, arbitrary_configuration)
    print("\nГотово. Закройте окна с графиками, чтобы завершить программу.")
    plt.show()


if __name__ == "__main__":
    main()