import random
import sys

import matplotlib.pyplot as plt

OUTPUT_LINES = []
MAX_ROUNDS = 10
DEFAULT_MESSAGE = "Nevar"
HAMMING_ERRORS = (0, 1, 2, 3)
ITERATIVE_ERRORS = (1, 2, 3, 4)
GROUP_NAMES = (
    "Горизонтальные паритеты",
    "Вертикальные паритеты",
    "Диагональные паритеты",
    "Обратные диагональные паритеты",
    "Паритеты по оси z",
)
VARIANT_CASES = (
    {"k1": 5, "k2": 8, "z": 1, "groups": (2, 3)},
    {"k1": 4, "k2": 10, "z": 1, "groups": (2, 3)},
    {"k1": 5, "k2": 4, "z": 2, "groups": (2, 3, 4, 5)},
    {"k1": 2, "k2": 10, "z": 2, "groups": (2, 3, 4, 5)},
)


def emit(text=""):
    print(text)
    OUTPUT_LINES.append(str(text))


def popcount(value):
    return bin(value).count("1")


def read_message(path):
    try:
        with open(path, encoding="utf-8") as file:
            text = file.read().strip()
    except OSError:
        text = ""
    return text if len(text.encode("utf-8")) >= 2 else DEFAULT_MESSAGE


def text_to_bits(text):
    return [int(bit) for byte in text.encode("utf-8") for bit in format(byte, "08b")]


def bits_to_string(bits):
    return "".join(str(bit) for bit in bits)


def int_to_bits(value, width):
    return [(value >> (width - 1 - t)) & 1 for t in range(width)]


def bits_to_int(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def hamming_parity_count(k):
    r = 1
    while (1 << r) < k + r + 1:
        r += 1
    return r


def hamming_build(k, extended):
    r = hamming_parity_count(k)
    info_columns = []
    weight = 2
    while len(info_columns) < k:
        for number in range(1, 1 << r):
            if popcount(number) == weight:
                info_columns.append(number)
                if len(info_columns) == k:
                    break
        weight += 1
    columns = info_columns + [1 << (r - 1 - t) for t in range(r)]
    rows = r
    if extended:
        columns = [(c << 1) | (1 ^ (popcount(c) & 1)) for c in columns] + [1]
        rows = r + 1
    return {
        "k": k,
        "r": rows,
        "n": k + rows,
        "columns": columns,
        "lookup": {column: index for index, column in enumerate(columns)},
    }


def hamming_matrix_rows(code):
    k, r, n = code["k"], code["r"], code["n"]
    rows = []
    for t in range(r):
        line = "".join(str((code["columns"][j] >> (r - 1 - t)) & 1) for j in range(n))
        rows.append(line[:k] + " " + line[k:])
    return rows


def hamming_parity(bits, code):
    value = 0
    for index, bit in enumerate(bits):
        if bit:
            value ^= code["columns"][index]
    return int_to_bits(value, code["r"])


def hamming_trial(info, code, multiplicity, rng):
    k, n = code["k"], code["n"]
    xr = hamming_parity(info, code)
    xn = info + xr
    positions = sorted(rng.sample(range(n), multiplicity))
    yn = xn[:]
    for position in positions:
        yn[position] ^= 1
    yr = yn[k:]
    yr_calculated = hamming_parity(yn[:k], code)
    syndrome = [a ^ b for a, b in zip(yr, yr_calculated)]
    syndrome_value = bits_to_int(syndrome)
    error = [0] * n
    corrected = yn[:]
    found = None
    if syndrome_value:
        found = code["lookup"].get(syndrome_value)
        if found is not None:
            error[found] = 1
            corrected[found] ^= 1
    return {
        "xr": xr,
        "xn": xn,
        "yn": yn,
        "yr": yr,
        "yr_calculated": yr_calculated,
        "syndrome": syndrome,
        "syndrome_value": syndrome_value,
        "error": error,
        "corrected": corrected,
        "positions": positions,
        "found": found,
    }


def hamming_status(trial, multiplicity):
    if trial["syndrome_value"] == 0:
        return "ошибок нет" if multiplicity == 0 else "ошибка не обнаружена"
    if trial["found"] is None:
        return "ошибка обнаружена, не исправлена"
    if trial["corrected"] == trial["xn"]:
        return f"исправлен бит {trial['found'] + 1}"
    return f"ошибочно исправлен бит {trial['found'] + 1}"


def hamming_statistics(code, trials, rng):
    rows = []
    for multiplicity in HAMMING_ERRORS:
        detected = 0
        fixed = 0
        for _ in range(trials):
            word = [rng.randint(0, 1) for _ in range(code["k"])]
            trial = hamming_trial(word, code, multiplicity, rng)
            detected += trial["syndrome_value"] != 0
            fixed += trial["corrected"] == trial["xn"]
        rows.append((multiplicity, detected / trials, fixed / trials))
    return rows


def run_hamming_part(text, info, trials, rng):
    emit("Часть 1. Код Хемминга")
    emit(f"Сообщение: {text}")
    emit(f"Xk = {bits_to_string(info)}")
    results = {}
    for distance in (3, 4):
        code = hamming_build(len(info), distance == 4)
        k, r, n = code["k"], code["r"], code["n"]
        emit()
        emit(f"d_min = {distance}: k = {k}, r = {r}, n = {n}, k/n = {k / n:.3f}")
        if n <= 80:
            emit("Проверочная матрица H:")
            for row in hamming_matrix_rows(code):
                emit(row)
        base = hamming_trial(info, code, 0, rng)
        emit(f"Xr  = {bits_to_string(base['xr'])}")
        emit(f"Xn  = {bits_to_string(base['xn'])}")
        for multiplicity in (0, 1, 2):
            trial = hamming_trial(info, code, multiplicity, rng)
            shown = [p + 1 for p in trial["positions"]]
            emit(f"Ошибок: {multiplicity}, позиции: {shown}, {hamming_status(trial, multiplicity)}")
            emit(f"Yn  = {bits_to_string(trial['yn'])}")
            emit(f"Yr  = {bits_to_string(trial['yr'])}, Yr' = {bits_to_string(trial['yr_calculated'])}, S = {bits_to_string(trial['syndrome'])}")
            emit(f"En  = {bits_to_string(trial['error'])}")
            emit(f"Yn' = {bits_to_string(trial['corrected'])}")
        results[distance] = hamming_statistics(code, trials, rng)
    emit()
    emit(f"Доли обнаруженных/исправленных слов по {trials} словам:")
    for index, multiplicity in enumerate(HAMMING_ERRORS):
        cells = []
        for distance in (3, 4):
            _, detected, fixed = results[distance][index]
            cells.append(f"d_min={distance}: {detected:.3f}/{fixed:.3f}")
        emit(f"i = {multiplicity}: " + ", ".join(cells))
    return results


def iterative_groups(k1, k2, z, count):
    def index(p, i, j):
        return (p * k1 + i) * k2 + j

    horizontal = [[index(p, i, j) for j in range(k2)] for p in range(z) for i in range(k1)]
    vertical = [[index(p, i, j) for i in range(k1)] for p in range(z) for j in range(k2)]
    diagonal = [[index(p, i, (i + d) % k2) for i in range(k1)] for p in range(z) for d in range(k2)]
    reverse = [[index(p, i, (d - i) % k2) for i in range(k1)] for p in range(z) for d in range(k2)]
    planes = [[index(p, i, j) for p in range(z)] for i in range(k1) for j in range(k2)]
    return [horizontal, vertical, diagonal, reverse, planes][:count]


def iterative_build(k1, k2, z, count):
    groups = iterative_groups(k1, k2, z, count)
    k = k1 * k2 * z
    checks = [check for group in groups for check in group]
    r = len(checks)
    info_masks = [sum(1 << b for b in check) for check in checks]
    full_masks = [mask | (1 << (k + c)) for c, mask in enumerate(info_masks)]
    membership = [0] * k
    for c, check in enumerate(checks):
        for b in check:
            membership[b] |= 1 << c
    return {
        "k1": k1,
        "k2": k2,
        "z": z,
        "k": k,
        "r": r,
        "n": k + r,
        "sizes": [len(group) for group in groups],
        "info_masks": info_masks,
        "full_masks": full_masks,
        "membership": membership,
    }


def iterative_encode(info, code):
    word = info
    for c, mask in enumerate(code["info_masks"]):
        if popcount(info & mask) & 1:
            word |= 1 << (code["k"] + c)
    return word


def failed_mask(word, code):
    mask = 0
    for c, check_mask in enumerate(code["full_masks"]):
        if popcount(word & check_mask) & 1:
            mask |= 1 << c
    return mask


def iterative_decode(word, code):
    k = code["k"]
    corrected = word
    for _ in range(MAX_ROUNDS):
        failed = failed_mask(corrected, code)
        if not failed:
            break
        flips = 0
        for b in range(k):
            member = code["membership"][b]
            if failed & member == member:
                flips |= 1 << b
        if not flips:
            break
        corrected ^= flips
    corrected ^= failed_mask(corrected, code) << k
    return corrected


def iterative_trial(info, code, multiplicity, rng):
    xn = iterative_encode(info, code)
    positions = sorted(rng.sample(range(code["n"]), multiplicity))
    yn = xn
    for position in positions:
        yn ^= 1 << position
    corrected = iterative_decode(yn, code)
    return xn, yn, corrected, positions


def word_to_string(word, width):
    return "".join("1" if (word >> p) & 1 else "0" for p in range(width))


def fit_bits(bits, length):
    return (bits + [0] * length)[:length]


def case_label(case):
    parts = [case["k1"], case["k2"]] + ([case["z"]] if case["z"] > 1 else [])
    return "x".join(str(part) for part in parts)


def show_iterative_example(case, count, info_bits, multiplicity, rng):
    code = iterative_build(case["k1"], case["k2"], case["z"], count)
    k, r, n = code["k"], code["r"], code["n"]
    info = bits_to_int(fit_bits(info_bits, k)[::-1])
    xn, yn, corrected, positions = iterative_trial(info, code, multiplicity, rng)
    emit()
    emit(f"Матрица {case_label(case)}, групп паритетов: {count}: k = {k}, r = {r}, n = {n}, k/n = {k / n:.3f}")
    plane = case["k1"] * case["k2"]
    for p in range(case["z"]):
        for i in range(case["k1"]):
            start = p * plane + i * case["k2"]
            emit(word_to_string(xn >> start, case["k2"]))
        if case["z"] > 1 and p < case["z"] - 1:
            emit()
    offset = k
    for name, size in zip(GROUP_NAMES, code["sizes"]):
        emit(f"{name}: {word_to_string(xn >> offset, size)}")
        offset += size
    failed = failed_mask(yn, code)
    changed = [p + 1 for p in range(n) if ((corrected ^ yn) >> p) & 1]
    emit(f"Ошибок: {multiplicity}, позиции: {[p + 1 for p in positions]}")
    emit(f"Неверных проверок: {popcount(failed)}, исправлены позиции: {changed}")
    emit(f"Xn = Yn': {'да' if corrected == xn else 'нет'}")


def run_iterative_part(info_bits, trials, rng):
    emit()
    emit("Часть 2. Итеративные коды, вариант 5, k = 40")
    show_iterative_example(VARIANT_CASES[0], 3, info_bits, 2, rng)
    emit()
    emit(f"Пары N2/N1 и N3/N1 при i = 1, 2, 3, 4 по {trials} словам:")
    emit("Матрица Груп r   k/n    i=1          i=2          i=3          i=4")
    results = []
    for case in VARIANT_CASES:
        for count in case["groups"]:
            code = iterative_build(case["k1"], case["k2"], case["z"], count)
            values = []
            for multiplicity in ITERATIVE_ERRORS:
                identified = 0
                fixed = 0
                for _ in range(trials):
                    info = rng.getrandbits(code["k"])
                    xn, yn, corrected, positions = iterative_trial(info, code, multiplicity, rng)
                    identified += popcount(corrected ^ yn) == multiplicity
                    fixed += corrected == xn
                values.append((identified / trials, fixed / trials))
            results.append({"case": case, "count": count, "code": code, "values": values})
            line = "  ".join(f"{a:.3f}/{b:.3f}" for a, b in values)
            emit(f"{case_label(case):<7}{count:<3}{code['r']:<4}{code['k'] / code['n']:<7.3f}{line}")
    return results


def make_hamming_graph(results):
    figure, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for axis, (distance, rows) in zip(axes, results.items()):
        x = list(range(len(rows)))
        axis.bar([v - 0.2 for v in x], [row[1] for row in rows], width=0.4, label="обнаружено")
        axis.bar([v + 0.2 for v in x], [row[2] for row in rows], width=0.4, label="исправлено")
        axis.set_xticks(x)
        axis.set_xticklabels([str(row[0]) for row in rows])
        axis.set_title(f"Код Хемминга, d_min = {distance}")
        axis.set_xlabel("Кратность ошибки i")
        axis.set_ylabel("Доля слов")
        axis.set_ylim(0, 1.1)
        axis.grid(axis="y", alpha=0.3)
        axis.legend()
    figure.tight_layout()
    plt.show(block=False)


def make_iterative_graph(results):
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    for axis, case in zip(axes.flat, VARIANT_CASES):
        for item in results:
            if item["case"] is case:
                y = [value[1] for value in item["values"]]
                axis.plot(list(ITERATIVE_ERRORS), y, marker="o", label=f"групп паритетов: {item['count']}")
        axis.set_title(f"Матрица {case_label(case)}")
        axis.set_xticks(list(ITERATIVE_ERRORS))
        axis.set_ylim(-0.05, 1.05)
        axis.set_xlabel("Кратность ошибки i")
        axis.set_ylabel("N3/N1")
        axis.grid(True, alpha=0.3)
        axis.legend()
    figure.suptitle("Доля полностью исправленных слов итеративным кодом")
    figure.tight_layout()
    plt.show(block=False)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "message.txt"
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    rng = random.Random(5)
    text = read_message(path)
    info = text_to_bits(text)
    hamming_results = run_hamming_part(text, info, trials, rng)
    iterative_results = run_iterative_part(info, trials, rng)
    with open("lab2_output.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(OUTPUT_LINES) + "\n")
    make_hamming_graph(hamming_results)
    make_iterative_graph(iterative_results)
    plt.show()


if __name__ == "__main__":
    main()
