import os
import random
import sys
from typing import List, Tuple, Dict, Optional

# Безопасная настройка кодировки консоли для Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def text_to_bits(text: str) -> List[int]:
    """Преобразование текста в список битов (ASCII / UTF-8 побайтово)."""
    data = text.encode('utf-8')
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_str(bits: List[int]) -> str:
    """Форматирование списка битов в строку."""
    return "".join(str(b) for b in bits)


def calc_hamming_r(k: int) -> int:
    """
    Вычисление числа проверочных символов r для классического кода Хемминга (d_min = 3)
    по неравенству 2^r >= k + r + 1 (согласно формуле из методички).
    """
    r = 1
    while (1 << r) < (k + r + 1):
        r += 1
    return r


def build_hamming_H(k: int, d_min: int = 3) -> Tuple[List[List[int]], int, int]:
    """
    Построение проверочной матрицы Хемминга H = [P' | I] в каноническом виде:
    - Сначала выбираются столбцы веса wt = 2, затем wt = 3 и т.д. (числа от 3 в двоичном виде).
    - Для d_min = 4 добавляется дополнительный бит четности (расширенный код Хемминга)
      и приводится к каноническому виду H = [P'_ext | I_{r+1}].
    Возвращает (H, r_total, n_total).
    """
    r_base = calc_hamming_r(k)
    
    # Формируем k столбцов подматрицы P' размерности (r_base x k)
    p_cols = []
    wt = 2
    while len(p_cols) < k and wt <= r_base:
        for num in range(3, 1 << r_base):
            bin_str = format(num, f'0{r_base}b')
            if bin_str.count('1') == wt:
                col = [int(ch) for ch in bin_str]
                p_cols.append(col)
                if len(p_cols) == k:
                    break
        wt += 1

    # Собираем базовую матрицу H_base (r_base x (k + r_base)) = [P' | I_{r_base}]
    n_base = k + r_base
    H_base = [[0] * n_base for _ in range(r_base)]
    for col_idx in range(k):
        for row_idx in range(r_base):
            H_base[row_idx][col_idx] = p_cols[col_idx][row_idx]
    for i in range(r_base):
        H_base[i][k + i] = 1

    if d_min == 3:
        return H_base, r_base, n_base
    elif d_min == 4:
        # Расширенный код Хемминга (d_min = 4) в каноническом виде H = [P'_ext | I_{r+1}]
        r_ext = r_base + 1
        n_ext = k + r_ext
        H_ext = [[0] * n_ext for _ in range(r_ext)]
        
        for row_idx in range(r_base):
            for col_idx in range(k):
                H_ext[row_idx][col_idx] = H_base[row_idx][col_idx]
            H_ext[row_idx][k + row_idx] = 1

        for col_idx in range(k):
            col_sum = sum(H_ext[row_idx][col_idx] for row_idx in range(r_base))
            H_ext[r_base][col_idx] = (col_sum + 1) % 2
        H_ext[r_base][k + r_base] = 1

        return H_ext, r_ext, n_ext
    else:
        raise ValueError("Поддерживаются только d_min = 3 или d_min = 4.")


def encode_hamming(x_k: List[int], H: List[List[int]], k: int, r: int) -> Tuple[List[int], List[int]]:
    """Вычисление избыточных символов X_r и формирование кодового слова X_n = [X_k | X_r]."""
    x_r = []
    for i in range(r):
        ones_pairs = sum(1 for j in range(k) if x_k[j] == 1 and H[i][j] == 1)
        x_r.append(ones_pairs % 2)
    x_n = x_k[:] + x_r
    return x_r, x_n


def inject_errors(x_n: List[int], num_errors: int, rng: Optional[random.Random] = None) -> Tuple[List[int], List[int]]:
    """Внесение заданного числа случайных ошибок в кодовое слово X_n."""
    if rng is None:
        rng = random.Random()
    n = len(x_n)
    num_errors = max(0, min(num_errors, n))
    positions = sorted(rng.sample(range(n), num_errors))
    y_n = x_n[:]
    for pos in positions:
        y_n[pos] ^= 1
    return y_n, positions


def decode_hamming(y_n: List[int], H: List[List[int]], k: int, r: int, d_min: int = 3) -> Dict[str, object]:
    """
    Декодирование принятого слова Y_n = [Y_k | Y_r]:
    - Вычисление Y'_r для принятой информационной части Y_k
    - Вычисление синдрома S = Y_r XOR Y'_r
    - Определение позиции одиночной ошибки (совпадение синдрома со столбцом H)
    - Формирование унарного вектора ошибки E_n и исправление Y_n_corr = Y_n XOR E_n.
    """
    n = k + r
    y_k = y_n[:k]
    y_r = y_n[k:]

    y_r_prime = []
    for i in range(r):
        ones_pairs = sum(1 for j in range(k) if y_k[j] == 1 and H[i][j] == 1)
        y_r_prime.append(ones_pairs % 2)

    syndrome = [1 if y_r[i] != y_r_prime[i] else 0 for i in range(r)]

    e_n = [0] * n
    error_pos = None
    status = ""

    if all(s == 0 for s in syndrome):
        status = "Ошибок не обнаружено (нулевой синдром S = 0)"
    else:
        for col_idx in range(n):
            col = [H[row_idx][col_idx] for row_idx in range(r)]
            if col == syndrome:
                error_pos = col_idx
                break

        if error_pos is not None:
            e_n[error_pos] = 1
            if d_min == 3:
                status = f"Локализована одиночная ошибка в позиции {error_pos + 1} (индекс {error_pos}); при кратности >=2 возможна ложная коррекция"
            else:
                status = f"Обнаружена и исправлена одиночная ошибка в позиции {error_pos + 1} (индекс {error_pos})"
        else:
            if d_min == 4:
                status = "Обнаружена двукратная ошибка (синдром S != 0, не совпадает ни с одним столбцом H; исправление невозможно)"
            else:
                status = "Обнаружена многократная ошибка (синдром S != 0, не совпадает со столбцами H)"

    y_n_corrected = [y_n[i] ^ e_n[i] for i in range(n)]

    return {
        "Y_k": y_k,
        "Y_r": y_r,
        "Y_r_prime": y_r_prime,
        "syndrome": syndrome,
        "E_n": e_n,
        "error_pos": error_pos,
        "Y_n_corrected": y_n_corrected,
        "status": status
    }


def print_hamming_report(msg_text: str, x_k: List[int], d_min: int = 3) -> None:
    """Форматированный вывод полного отчета по Части 1 (Код Хемминга)."""
    k = len(x_k)
    H, r, n = build_hamming_H(k, d_min=d_min)
    x_r, x_n = encode_hamming(x_k, H, k, r)

    print("=" * 88)
    print(f"ЧАСТЬ 1. КОД ХЕММИНГА (d_min = {d_min})")
    print("=" * 88)
    print(f"Исходное текстовое сообщение : '{msg_text}'")
    print(f"Параметры кода (n, k, r)     : k = {k}, r = {r}, n = {n}, R = k/n = {k/n:.4f}")
    print(f"Информационное слово X_k     : {bits_to_str(x_k)}")
    print(f"Проверочные символы X_r      : {bits_to_str(x_r)}")
    print(f"Кодовое слово X_n            : {bits_to_str(x_n)}")
    print("\nПроверочная матрица Хемминга H_(n,k) = [P' | I]:")
    for row_idx, row in enumerate(H):
        p_part = "".join(str(v) for v in row[:k])
        i_part = "".join(str(v) for v in row[k:])
        print(f"  Строка {row_idx + 1:2d}: {p_part} | {i_part}")

    rng = random.Random(42 + d_min)
    for num_err in (0, 1, 2):
        print("-" * 88)
        y_n, true_pos = inject_errors(x_n, num_err, rng=rng)
        res = decode_hamming(y_n, H, k, r, d_min=d_min)
        pos_str = ", ".join(f"{p + 1} (инд. {p})" for p in true_pos) if true_pos else "нет"
        print(f"[Эксперимент: кратность ошибки = {num_err}] Истинные позиции ошибок: {pos_str}")
        print(f"  Принятое слово Y_n         : {bits_to_str(y_n)}")
        print(f"  Принятая инф. часть Y_k    : {bits_to_str(res['Y_k'])}")
        print(f"  Принятые пров. биты Y_r    : {bits_to_str(res['Y_r'])}")
        print(f"  Вновь вычисленные Y'_r     : {bits_to_str(res['Y_r_prime'])}")
        print(f"  Синдром S = Y_r XOR Y'_r   : {bits_to_str(res['syndrome'])}")
        print(f"  Унарный вектор ошибки E_n  : {bits_to_str(res['E_n'])}")
        print(f"  Результат анализа синдрома : {res['status']}")
        print(f"  Слово после коррекции Y'_n : {bits_to_str(res['Y_n_corrected'])}")
        is_exact = (res['Y_n_corrected'] == x_n)
        print(f"  Совпадение Y'_n == X_n     : {'ДА (успешно восстановлено)' if is_exact else 'НЕТ (ошибка не исправлена / ложная коррекция)'}")
    print("=" * 88 + "\n")


# ==============================================================================
# ЧАСТЬ 2. ИТЕРАТИВНЫЕ КОДЫ (ВАРИАНТ 2, k = 20 бит)
# ==============================================================================
# Вариант 2 из Таблицы 5.2 методических указаний:
# Длина информационного слова k = 20 бит:
# 1) 2D: k1 = 4, k2 = 5,  Z = None, Количество групп паритетов: 2; 3
# 2) 2D: k1 = 2, k2 = 10, Z = None, Количество групп паритетов: 2; 3
# 3) 3D: k1 = 2, k2 = 5,  Z = 2,    Количество групп паритетов: 2; 3; 4; 5
# 4) 3D: k1 = 2, k2 = 2,  Z = 5,    Количество групп паритетов: 2; 3; 4; 5

VARIANT_2_CONFIGS = [
    {"id": 1, "dim": 2, "k": 20, "k1": 4, "k2": 5,  "z": 1, "parity_groups": [2, 3]},
    {"id": 2, "dim": 2, "k": 20, "k1": 2, "k2": 10, "z": 1, "parity_groups": [2, 3]},
    {"id": 3, "dim": 3, "k": 20, "k1": 2, "k2": 5,  "z": 2, "parity_groups": [2, 3, 4, 5]},
    {"id": 4, "dim": 3, "k": 20, "k1": 2, "k2": 2,  "z": 5, "parity_groups": [2, 3, 4, 5]},
]


class IterativeCodeEngine:
    """
    Универсальный кодер/декодер многомерного линейного итеративного кода
    для двумерных (Z=1) и трехмерных (Z>1) матриц с поддержкой 2, 3, 4 и 5 групп паритетов
    и контрольного бита паритета паритетов X_hv.
    """

    def __init__(self, k1: int, k2: int, z: int = 1, num_groups: int = 2, include_xhv: bool = True):
        self.k1 = k1
        self.k2 = k2
        self.z = z
        self.k = k1 * k2 * z
        self.num_groups = num_groups
        self.include_xhv = include_xhv

        self.parity_checks: List[Tuple[str, List[int]]] = []
        self._build_parity_structure()

        self.r = len(self.parity_checks)
        self.n = self.k + self.r

        self.bit_to_checks: List[List[int]] = [[] for _ in range(self.k)]
        for chk_idx, (_, bit_indices) in enumerate(self.parity_checks):
            for b_idx in bit_indices:
                self.bit_to_checks[b_idx].append(chk_idx)

    def _coord_to_idx(self, plane: int, row: int, col: int) -> int:
        return plane * (self.k1 * self.k2) + row * self.k2 + col

    def _build_parity_structure(self) -> None:
        # 1. Группа 1: Горизонтальные паритеты X_h
        if self.num_groups >= 1:
            for p in range(self.z):
                for r in range(self.k1):
                    indices = [self._coord_to_idx(p, r, c) for c in range(self.k2)]
                    self.parity_checks.append((f"H(z={p},r={r})", indices))

        # 2. Группа 2: Вертикальные паритеты X_v
        if self.num_groups >= 2:
            for p in range(self.z):
                for c in range(self.k2):
                    indices = [self._coord_to_idx(p, r, c) for r in range(self.k1)]
                    self.parity_checks.append((f"V(z={p},c={c})", indices))

        # 3. Группа 3: Диагональные паритеты X_d1
        if self.num_groups >= 3:
            for p in range(self.z):
                for d_sum in range(self.k1 + self.k2 - 1):
                    indices = [
                        self._coord_to_idx(p, r, c)
                        for r in range(self.k1)
                        for c in range(self.k2)
                        if r + c == d_sum
                    ]
                    self.parity_checks.append((f"D1(z={p},s={d_sum})", indices))

        # 4. Группа 4: Вторые диагональные паритеты X_d2 (антидиагонали r - c = const)
        if self.num_groups >= 4:
            for p in range(self.z):
                for d_diff in range(-(self.k2 - 1), self.k1):
                    indices = [
                        self._coord_to_idx(p, r, c)
                        for r in range(self.k1)
                        for c in range(self.k2)
                        if r - c == d_diff
                    ]
                    self.parity_checks.append((f"D2(z={p},d={d_diff})", indices))

        # 5. Группа 5: Поперечные Z-паритеты между плоскостями
        if self.num_groups >= 5 and self.z > 1:
            for r in range(self.k1):
                for c in range(self.k2):
                    indices = [self._coord_to_idx(p, r, c) for p in range(self.z)]
                    self.parity_checks.append((f"Z(r={r},c={c})", indices))

        # Контрольный бит паритета паритетов X_hv
        if self.include_xhv:
            all_indices = list(range(self.k))
            self.parity_checks.append(("X_hv", all_indices))

    def encode(self, x_k: List[int]) -> Tuple[List[int], List[int]]:
        """Вычисление проверочных бит X_r и формирование кодового слова X_n = [X_k | X_r]."""
        if len(x_k) != self.k:
            raise ValueError(f"Длина информационного слова ({len(x_k)}) не равна k = {self.k}")
        x_r = []
        for _, indices in self.parity_checks:
            parity = sum(x_k[idx] for idx in indices) % 2
            x_r.append(parity)
        x_n = x_k[:] + x_r
        return x_r, x_n

    def compute_syndrome(self, y_n: List[int]) -> List[int]:
        """Сравнение принятых паритетов Y_r и вновь вычисленных Y'_r для принятого слова Y_n."""
        y_k = y_n[:self.k]
        y_r = y_n[self.k:]
        syndrome = []
        for chk_idx, (_, indices) in enumerate(self.parity_checks):
            recalc = sum(y_k[idx] for idx in indices) % 2
            syndrome.append(y_r[chk_idx] ^ recalc)
        return syndrome

    def decode(self, y_n: List[int], max_iters: int = 12) -> Dict[str, object]:
        """Итеративное мажоритарное декодирование принятого слова Y_n."""
        y_corr = y_n[:]
        initial_syndrome = self.compute_syndrome(y_corr)
        error_detected = any(s == 1 for s in initial_syndrome)

        if not error_detected:
            return {
                "error_detected": False,
                "estimated_multiplicity": 0,
                "corrected_word": y_corr,
                "flipped_positions": [],
                "initial_syndrome": initial_syndrome,
                "final_syndrome": initial_syndrome,
            }

        flipped_positions: List[int] = []

        for _ in range(max_iters):
            syndrome = self.compute_syndrome(y_corr)
            total_violated = sum(syndrome)
            if total_violated == 0:
                break

            # Одиночная ошибка в проверочном бите
            if total_violated == 1:
                chk_idx = syndrome.index(1)
                pos = self.k + chk_idx
                y_corr[pos] ^= 1
                if pos in flipped_positions:
                    flipped_positions.remove(pos)
                else:
                    flipped_positions.append(pos)
                break

            # Точное совпадение синдрома с профилем одного информационного бита
            exact_data_bit = None
            for b_idx in range(self.k):
                chk_set = set(self.bit_to_checks[b_idx])
                if all((syndrome[c] == 1 if c in chk_set else syndrome[c] == 0) for c in range(self.r)):
                    exact_data_bit = b_idx
                    break

            if exact_data_bit is not None:
                y_corr[exact_data_bit] ^= 1
                if exact_data_bit in flipped_positions:
                    flipped_positions.remove(exact_data_bit)
                else:
                    flipped_positions.append(exact_data_bit)
                break

            # Мажоритарный поиск информационного бита на пересечении нарушенных паритетов
            best_bit = -1
            best_score = 0
            best_ratio = 0.0

            for b_idx in range(self.k):
                checks = self.bit_to_checks[b_idx]
                deg = len(checks)
                violated = sum(syndrome[c] for c in checks)
                ratio = violated / deg if deg > 0 else 0.0
                if violated >= 2 and ratio > 0.5:
                    if violated > best_score or (violated == best_score and ratio > best_ratio):
                        best_score = violated
                        best_ratio = ratio
                        best_bit = b_idx

            if best_bit != -1:
                y_corr[best_bit] ^= 1
                if best_bit in flipped_positions:
                    flipped_positions.remove(best_bit)
                else:
                    flipped_positions.append(best_bit)
            else:
                if total_violated <= self.num_groups:
                    for chk_idx, s_val in enumerate(syndrome):
                        if s_val == 1:
                            pos = self.k + chk_idx
                            y_corr[pos] ^= 1
                            if pos not in flipped_positions:
                                flipped_positions.append(pos)
                break

        final_syndrome = self.compute_syndrome(y_corr)
        est_multiplicity = len(flipped_positions)
        if any(s == 1 for s in final_syndrome) and est_multiplicity == 0:
            est_multiplicity = max(2, sum(final_syndrome) // max(1, self.num_groups))

        return {
            "error_detected": True,
            "estimated_multiplicity": est_multiplicity,
            "corrected_word": y_corr,
            "flipped_positions": sorted(flipped_positions),
            "initial_syndrome": initial_syndrome,
            "final_syndrome": final_syndrome,
        }

    def format_matrix_view(self, x_k: List[int], x_r: List[int]) -> str:
        """Наглядная визуализация 2D/3D матрицы с горизонтальными и вертикальными паритетами."""
        lines = []
        h_offset = 0
        v_offset = self.z * self.k1

        for p in range(self.z):
            if self.z > 1:
                lines.append(f"  Плоскость Z = {p + 1}:")
            for r in range(self.k1):
                row_bits = [str(x_k[self._coord_to_idx(p, r, c)]) for c in range(self.k2)]
                h_bit = str(x_r[h_offset + p * self.k1 + r])
                lines.append(f"    {' '.join(row_bits)}  | {h_bit}")
            sep_len = self.k2 * 2 - 1
            lines.append(f"    {'-' * sep_len}---+-")
            v_bits = [str(x_r[v_offset + p * self.k2 + c]) for c in range(self.k2)]
            xhv_str = str(x_r[-1]) if (self.include_xhv and p == self.z - 1) else " "
            lines.append(f"    {' '.join(v_bits)}  | {xhv_str}")
        return "\n".join(lines)


def evaluate_iterative_code_stats(
    engine: IterativeCodeEngine,
    x_n: List[int],
    multiplicities: List[int] = [1, 2, 3, 4, 5],
    num_trials: int = 300,
    seed: int = 100
) -> List[Dict[str, float]]:
    """Вычисление оценок N2 / N1 (идентификация кратности) и N3 / N1 (полная коррекция)."""
    rng = random.Random(seed)
    results = []

    for mult in multiplicities:
        if mult > engine.n:
            continue
        n1 = num_trials
        n_detected = 0
        n2_mult_identified = 0
        n3_corrected = 0

        for _ in range(n1):
            y_n, _ = inject_errors(x_n, mult, rng=rng)
            dec = engine.decode(y_n)
            if dec["error_detected"]:
                n_detected += 1
            if dec["corrected_word"] == x_n:
                n3_corrected += 1
                n2_mult_identified += 1
            elif dec["estimated_multiplicity"] == mult:
                n2_mult_identified += 1

        results.append({
            "multiplicity": mult,
            "N1": n1,
            "N_det": n_detected,
            "N2": n2_mult_identified,
            "N3": n3_corrected,
            "det_ratio": n_detected / n1,
            "N2_N1": n2_mult_identified / n1,
            "N3_N1": n3_corrected / n1,
        })
    return results


def run_variant_2_full_demo() -> None:
    """Полный автоматический прогон всех заданий для Варианта 2 (k = 20 бит)."""
    data_file = os.path.join(os.path.dirname(__file__), "..", "assets", "data", "input_message.txt")
    source_desc = "строка 'VAR2'"
    sample_text = "VAR2"
    if os.path.isfile(data_file):
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    sample_text = content[:3]
                    source_desc = f"файл '{os.path.normpath(data_file)}'"
        except Exception:
            pass

    x_k = text_to_bits(sample_text)
    if len(x_k) > 20:
        x_k = x_k[:20]
    elif len(x_k) < 20:
        x_k += [0] * (20 - len(x_k))

    # 1. Часть 1: Код Хемминга (d_min = 3 и d_min = 4)
    print_hamming_report(sample_text, x_k, d_min=3)
    print_hamming_report(sample_text, x_k, d_min=4)

    # 2. Часть 2: Итеративные коды (Вариант 2, k = 20 бит)
    print("=" * 88)
    print("ЧАСТЬ 2. МНОГОМЕРНЫЕ ИТЕРАТИВНЫЕ КОДЫ (ВАРИАНТ 2, k = 20 бит)")
    print("=" * 88)
    print(f"Исходное сообщение ({source_desc}): '{sample_text}' (k = 20 бит)")
    print(f"Информационное слово X_k (k = {len(x_k)} бит): {bits_to_str(x_k)}\n")

    rng = random.Random(2026)

    for cfg in VARIANT_2_CONFIGS:
        dim_label = f"2D матрица ({cfg['k1']}x{cfg['k2']})" if cfg["dim"] == 2 else f"3D матрица ({cfg['k1']}x{cfg['k2']}x{cfg['z']})"
        print("#" * 88)
        print(f"КОНФИГУРАЦИЯ #{cfg['id']} (Вариант 2): {dim_label}, k = {cfg['k']} бит")
        print(f"Доступные количества групп паритетов по Таблице 5.2: {cfg['parity_groups']}")
        print("#" * 88)

        for g_cnt in cfg["parity_groups"]:
            engine = IterativeCodeEngine(
                k1=cfg["k1"],
                k2=cfg["k2"],
                z=cfg["z"],
                num_groups=g_cnt,
                include_xhv=True
            )
            x_r, x_n = engine.encode(x_k)
            code_rate = engine.k / engine.n
            rel_redundancy = engine.r / engine.n

            print("-" * 88)
            print(f"--> Число групп паритетов: {g_cnt} (+ бит X_hv) | k = {engine.k}, r = {engine.r}, n = {engine.n}")
            print(f"    Скорость кода R = k/n = {code_rate:.4f} | Относительная избыточность r/n = {rel_redundancy:.4f}")
            print(f"    Избыточные символы X_r ({engine.r} бит): {bits_to_str(x_r)}")
            print(f"    Кодовое слово X_n ({engine.n} бит)     : {bits_to_str(x_n)}")

            if g_cnt == cfg["parity_groups"][0]:
                print("\n    Матричное представление (инф. биты + горизонтальные/вертикальные паритеты и X_hv):")
                print(engine.format_matrix_view(x_k, x_r))

            for test_mult in (1, 2):
                y_n, err_positions = inject_errors(x_n, test_mult, rng=rng)
                dec = engine.decode(y_n)
                restored_ok = (dec["corrected_word"] == x_n)
                pos_1based = [p + 1 for p in err_positions]
                flip_1based = [p + 1 for p in dec["flipped_positions"]]
                status_text = "УСПЕШНО (Y'_n == X_n)" if restored_ok else "НЕ ИСПРАВЛЕНО"
                print(f"\n    [Тест декодирования: кратность i = {test_mult}] Сгенерированы ошибки в поз.: {pos_1based}")
                print(f"      Принятое слово Y_n     : {bits_to_str(y_n)}")
                print(f"      Синдром S (вес={sum(dec['initial_syndrome']):2d})     : {bits_to_str(dec['initial_syndrome'])}")
                print(f"      Исправленные позиции   : {flip_1based}")
                print(f"      Восстановленное Y'_n   : {bits_to_str(dec['corrected_word'])}")
                print(f"      Результат коррекции    : {status_text}")

            stats = evaluate_iterative_code_stats(engine, x_n, multiplicities=[1, 2, 3, 4, 5], num_trials=300, seed=100 + g_cnt)
            print("\n    Анализ корректирующей способности кода (N1 = 300 испытаний на каждую кратность i):")
            print(f"    {'Кратность i':^12} | {'Обнаружено':^12} | {'N2 (кратность)':^16} | {'N3 (исправлено)':^16} | {'N2 / N1':^10} | {'N3 / N1':^10}")
            print("    " + "-" * 84)
            for st in stats:
                print(
                    f"    {st['multiplicity']:^12d} | "
                    f"{st['N_det']:^12d} | "
                    f"{st['N2']:^16d} | "
                    f"{st['N3']:^16d} | "
                    f"{st['N2_N1']:^10.3f} | "
                    f"{st['N3_N1']:^10.3f}"
                )
            print()


def interactive_menu() -> None:
    """Интерактивное консольное меню для пользовательских экспериментов на защите."""
    while True:
        print("\n" + "=" * 65)
        print("МЕНЮ: ИССЛЕДОВАНИЕ ПОМЕХОУСТОЙЧИВЫХ КОДОВ (ВАРИАНТ 2, k = 20)")
        print("=" * 65)
        print("1. Полный автоматический тест (Часть 1 + Часть 2)")
        print("2. Часть 1: Код Хемминга для произвольного текста / бит")
        print("3. Часть 2: Итеративный код (Вариант 2, k=20) — свой тест")
        print("0. Выход")
        choice = input("Выберите пункт меню: ").strip()

        if choice == "0":
            print("Завершение работы.")
            break
        elif choice == "1":
            run_variant_2_full_demo()
        elif choice == "2":
            text = input("Введите текст или биты (по умолчанию 'VAR2'): ").strip() or "VAR2"
            x_k = text_to_bits(text)
            if len(x_k) > 20:
                x_k = x_k[:20]
            elif len(x_k) < 20:
                x_k += [0] * (20 - len(x_k))
            d_str = input("Выберите минимальное кодовое расстояние d_min (3 или 4, по умолчанию 3): ").strip()
            d_min = 4 if d_str == "4" else 3
            print_hamming_report(text, x_k, d_min=d_min)
        elif choice == "3":
            print("\nДоступные конфигурации Варианта 2 (k = 20 бит):")
            for cfg in VARIANT_2_CONFIGS:
                if cfg["dim"] == 2:
                    print(f"  {cfg['id']}) 2D матрица {cfg['k1']}x{cfg['k2']} (группы паритетов: {cfg['parity_groups']})")
                else:
                    print(f"  {cfg['id']}) 3D матрица {cfg['k1']}x{cfg['k2']}x{cfg['z']} (группы паритетов: {cfg['parity_groups']})")
            c_idx = input("Выберите номер конфигурации (1-4, по умолчанию 1): ").strip()
            cfg_id = int(c_idx) if c_idx in ("1", "2", "3", "4") else 1
            cfg = VARIANT_2_CONFIGS[cfg_id - 1]

            g_str = input(f"Выберите количество групп паритетов {cfg['parity_groups']} (по умолчанию {cfg['parity_groups'][0]}): ").strip()
            g_cnt = int(g_str) if g_str.isdigit() and int(g_str) in cfg["parity_groups"] else cfg["parity_groups"][0]

            bin_in = input("Введите 20 бит (или оставьте пустым для генерации из 'VAR2'): ").strip()
            if bin_in and all(c in "01" for c in bin_in):
                x_k = [int(c) for c in bin_in[:20]]
                if len(x_k) < 20:
                    x_k += [0] * (20 - len(x_k))
            else:
                x_k = text_to_bits("VAR2")[:20]

            mult_str = input("Введите кратность ошибки i (i > 0, по умолчанию 2): ").strip()
            mult = int(mult_str) if mult_str.isdigit() and int(mult_str) > 0 else 2

            engine = IterativeCodeEngine(cfg["k1"], cfg["k2"], cfg["z"], num_groups=g_cnt, include_xhv=True)
            x_r, x_n = engine.encode(x_k)
            y_n, pos = inject_errors(x_n, mult)
            dec = engine.decode(y_n)

            print(f"\nИнформационное слово X_k ({engine.k} бит): {bits_to_str(x_k)}")
            print(f"Проверочные биты X_r ({engine.r} бит)    : {bits_to_str(x_r)}")
            print(f"Кодовое слово X_n ({engine.n} бит)       : {bits_to_str(x_n)}")
            print("\nМатрица:")
            print(engine.format_matrix_view(x_k, x_r))
            print(f"\nВнесено ошибок: {mult} (позиции: {[p + 1 for p in pos]})")
            print(f"Принятое слово Y_n       : {bits_to_str(y_n)}")
            print(f"Синдром S                : {bits_to_str(dec['initial_syndrome'])}")
            print(f"Исправленное слово Y'_n  : {bits_to_str(dec['corrected_word'])}")
            print(f"Совпадение Y'_n == X_n   : {'ДА' if dec['corrected_word'] == x_n else 'НЕТ'}")
        else:
            print("Неверный ввод, попробуйте снова.")


if __name__ == "__main__":
    if "--interactive" in sys.argv or "-i" in sys.argv:
        interactive_menu()
    else:
        run_variant_2_full_demo()

