import numpy as np
import random
from typing import List, Tuple, Optional

def binary_string_to_matrix(binary_str: str, k1: int, k2: int) -> np.ndarray:
    if len(binary_str) != k1 * k2:
        raise ValueError(f"Длина строки должна быть равна {k1 * k2}")
    bits = [int(b) for b in binary_str]
    return np.array(bits).reshape(k1, k2)

def compute_row_parities(matrix: np.ndarray) -> np.ndarray:
    return np.sum(matrix, axis=1) % 2

def compute_col_parities(matrix: np.ndarray) -> np.ndarray:
    return np.sum(matrix, axis=0) % 2

def compute_main_diag_parities(matrix: np.ndarray) -> np.ndarray:
    """Паритеты по всем параллелям главной диагонали (i - j = const)."""
    k1, k2 = matrix.shape
    num_diags = k1 + k2 - 1
    diags = np.zeros(num_diags, dtype=int)
    for i in range(k1):
        for j in range(k2):
            d = i - j + (k2 - 1)          # сдвиг, чтобы индекс был >= 0
            diags[d] ^= matrix[i, j]
    return diags

def compute_anti_diag_parities(matrix: np.ndarray) -> np.ndarray:
    """Паритеты по всем параллелям побочной диагонали (i + j = const)."""
    k1, k2 = matrix.shape
    num_diags = k1 + k2 - 1
    diags = np.zeros(num_diags, dtype=int)
    for i in range(k1):
        for j in range(k2):
            d = i + j
            diags[d] ^= matrix[i, j]
    return diags

def compute_overall_parity(*parity_vectors) -> int:
    total = 0
    for vec in parity_vectors:
        total ^= np.sum(vec) % 2
    return total

def encode(info_matrix: np.ndarray, num_parity_groups: int = 3):
    """
    Кодирование.
    Возвращает:
      - codeword (плоский массив)
      - словарь со всеми паритетами (для отладки и декодирования)
    """
    k1, k2 = info_matrix.shape
    row_p = compute_row_parities(info_matrix)
    col_p = compute_col_parities(info_matrix)

    main_d = None
    anti_d = None
    overall = 0

    if num_parity_groups >= 4:
        main_d = compute_main_diag_parities(info_matrix)
        anti_d = compute_anti_diag_parities(info_matrix)

    if num_parity_groups == 3 or num_parity_groups == 5:
        vectors = [row_p, col_p]
        if main_d is not None:
            vectors.extend([main_d, anti_d])
        overall = compute_overall_parity(*vectors)

    # Формируем кодовое слово: info + row + col + [main] + [anti] + [overall]
    parts = [info_matrix.flatten(), row_p, col_p]
    if main_d is not None:
        parts.append(main_d)
        parts.append(anti_d)
    if num_parity_groups in (3, 5):
        parts.append(np.array([overall]))

    codeword = np.concatenate(parts)
    parities = {
        'row': row_p,
        'col': col_p,
        'main_diag': main_d,
        'anti_diag': anti_d,
        'overall': overall if num_parity_groups in (3, 5) else None
    }
    return codeword, parities

def introduce_errors(codeword: np.ndarray, num_errors: int) -> Tuple[np.ndarray, List[int]]:
    n = len(codeword)
    num_errors = min(num_errors, n)
    positions = random.sample(range(n), num_errors) if num_errors > 0 else []
    yn = codeword.copy()
    for pos in positions:
        yn[pos] = 1 - yn[pos]
    return yn, sorted(positions)

def decode_and_correct(yn: np.ndarray, k1: int, k2: int, num_parity_groups: int = 3):
    """
    Декодирование и попытка исправления.
    Возвращает исправленное слово, список исправленных позиций и синдромы.
    """
    k = k1 * k2
    pos = 0

    # Разбираем принятое слово
    info_recv = yn[pos:pos + k].reshape(k1, k2)
    pos += k
    row_recv = yn[pos:pos + k1]
    pos += k1
    col_recv = yn[pos:pos + k2]
    pos += k2

    main_recv = anti_recv = None
    overall_recv = None

    if num_parity_groups >= 4:
        num_d = k1 + k2 - 1
        main_recv = yn[pos:pos + num_d]
        pos += num_d
        anti_recv = yn[pos:pos + num_d]
        pos += num_d

    if num_parity_groups in (3, 5):
        overall_recv = yn[pos]

    # Пересчитываем паритеты по принятым информационным битам
    row_calc = compute_row_parities(info_recv)
    col_calc = compute_col_parities(info_recv)
    main_calc = compute_main_diag_parities(info_recv) if num_parity_groups >= 4 else None
    anti_calc = compute_anti_diag_parities(info_recv) if num_parity_groups >= 4 else None

    # Синдромы
    row_s = (row_recv + row_calc) % 2
    col_s = (col_recv + col_calc) % 2
    main_s = (main_recv + main_calc) % 2 if main_calc is not None else None
    anti_s = (anti_recv + anti_calc) % 2 if anti_calc is not None else None

    overall_s = 0
    if num_parity_groups in (3, 5):
        vectors = [row_calc, col_calc]
        if main_calc is not None:
            vectors.extend([main_calc, anti_calc])
        overall_calc = compute_overall_parity(*vectors)
        overall_s = (overall_recv + overall_calc) % 2

    # Поиск и исправление одиночной ошибки
    yn_corr = yn.copy()
    corrected_positions = []

    error_rows = np.where(row_s == 1)[0]
    error_cols = np.where(col_s == 1)[0]

    # Случай 1: ошибка в информационном бите
    if len(error_rows) == 1 and len(error_cols) == 1:
        r, c = error_rows[0], error_cols[0]
        # Дополнительная проверка по диагоналям (если они есть)
        consistent = True
        if main_s is not None:
            d_main = r - c + (k2 - 1)
            if main_s[d_main] != 1:
                consistent = False
        if anti_s is not None:
            d_anti = r + c
            if anti_s[d_anti] != 1:
                consistent = False

        if consistent:
            bit_pos = r * k2 + c
            yn_corr[bit_pos] = 1 - yn_corr[bit_pos]
            corrected_positions.append(bit_pos)

    # Случай 2: ошибка только в строковом паритете
    elif len(error_rows) == 1 and len(error_cols) == 0:
        r = error_rows[0]
        bit_pos = k + r
        yn_corr[bit_pos] = 1 - yn_corr[bit_pos]
        corrected_positions.append(bit_pos)

    # Случай 3: ошибка только в столбцовом паритете
    elif len(error_rows) == 0 and len(error_cols) == 1:
        c = error_cols[0]
        bit_pos = k + k1 + c
        yn_corr[bit_pos] = 1 - yn_corr[bit_pos]
        corrected_positions.append(bit_pos)

    # Случай 4: ошибка в общем паритете
    elif num_parity_groups in (3, 5) and overall_s == 1 and \
         len(error_rows) == 0 and len(error_cols) == 0 and \
         (main_s is None or np.all(main_s == 0)) and \
         (anti_s is None or np.all(anti_s == 0)):
        bit_pos = len(yn) - 1
        yn_corr[bit_pos] = 1 - yn_corr[bit_pos]
        corrected_positions.append(bit_pos)

    syndromes = {
        'row': row_s,
        'col': col_s,
        'main_diag': main_s,
        'anti_diag': anti_s,
        'overall': overall_s if num_parity_groups in (3, 5) else None
    }
    return yn_corr, corrected_positions, syndromes

def analyze_correcting_ability(k1, k2, num_parity_groups, num_trials=50, max_errors=2):
    results = {}
    k = k1 * k2
    for i in range(1, max_errors + 1):
        N2 = N3 = 0
        for _ in range(num_trials):
            info_bits = [random.randint(0, 1) for _ in range(k)]
            info_str = ''.join(map(str, info_bits))
            info_mat = binary_string_to_matrix(info_str, k1, k2)
            xn, _ = encode(info_mat, num_parity_groups)
            yn, _ = introduce_errors(xn, i)
            yn_star, _, syndromes = decode_and_correct(yn, k1, k2, num_parity_groups)

            # Обнаружение: хотя бы один синдром ненулевой
            detected = (np.any(syndromes['row']) or np.any(syndromes['col']) or
                        (syndromes['main_diag'] is not None and np.any(syndromes['main_diag'])) or
                        (syndromes['anti_diag'] is not None and np.any(syndromes['anti_diag'])) or
                        (syndromes['overall'] is not None and syndromes['overall'] == 1))
            if detected:
                N2 += 1
            if np.array_equal(yn_star, xn):
                N3 += 1
        results[i] = {
            'N1': num_trials,
            'N2': N2,
            'N3': N3,
            'N2_N1': N2 / num_trials,
            'N3_N1': N3 / num_trials
        }
    return results

def print_matrix(matrix, title):
    print(title)
    for row in matrix:
        print(' '.join(map(str, row)))

def main():
    print("Итеративное кодирование с поддержкой диагональных паритетов")
    print("Доступные конфигурации матрицы:")
    print("1. k1=4, k2=4 (2D)")
    print("2. k1=8, k2=2 (2D)")
    print("3. k1=4, k2=2 (упрощённый 3D-слой)")
    print("4. k1=2, k2=4 (упрощённый 3D-слой)")
    print()

    choice = input("Выберите конфигурацию [1]: ").strip() or '1'
    if choice == '2':
        k1, k2 = 8, 2
    elif choice == '3':
        k1, k2 = 4, 2
    elif choice == '4':
        k1, k2 = 2, 4
    else:
        k1, k2 = 4, 4

    k = k1 * k2
    print(f"\nВыбрано: k1={k1}, k2={k2}, k={k}")

    print("\nКоличество групп паритетов:")
    print("  2 — строки + столбцы")
    print("  3 — строки + столбцы + общий")
    print("  4 — строки + столбцы + главные диагонали + побочные диагонали")
    print("  5 — всё выше + общий паритет")
    num_str = input("Введите число групп (2–5) [3]: ").strip() or '3'
    num_parity_groups = int(num_str)
    if num_parity_groups not in (2, 3, 4, 5):
        num_parity_groups = 3
    print(f"Используется {num_parity_groups} групп паритетов")

    # Ввод информационного слова
    print(f"\nВведите информационное слово Xk ({k} бит, только 0 и 1)")
    print("или нажмите Enter для случайного слова:")
    info_input = input().strip()
    if not info_input:
        info_bits = [random.randint(0, 1) for _ in range(k)]
        info_str = ''.join(map(str, info_bits))
        print(f"Сгенерировано: {info_str}")
    else:
        info_str = info_input
        if len(info_str) != k or any(c not in '01' for c in info_str):
            print("Ошибка ввода. Используется случайное слово.")
            info_bits = [random.randint(0, 1) for _ in range(k)]
            info_str = ''.join(map(str, info_bits))
            print(f"Сгенерировано: {info_str}")

    info_matrix = binary_string_to_matrix(info_str, k1, k2)
    print_matrix(info_matrix, "\nИнформационная матрица Xk:")

    # Кодирование
    xn, parities = encode(info_matrix, num_parity_groups)
    print(f"\nКодовое слово Xn (длина n={len(xn)}):")
    print(''.join(map(str, xn)))

    print("\nПаритеты:")
    print(f"  Строковые:     {parities['row']}")
    print(f"  Столбцовые:    {parities['col']}")
    if parities['main_diag'] is not None:
        print(f"  Главные диаг.: {parities['main_diag']}")
        print(f"  Побочные диаг.:{parities['anti_diag']}")
    if parities['overall'] is not None:
        print(f"  Общий:         {parities['overall']}")

    # Внесение ошибок
    err_str = input("\nВведите кратность ошибки i (целое >0) [1]: ").strip() or '1'
    num_errors = int(err_str)
    yn, error_positions = introduce_errors(xn, num_errors)
    print(f"\nВнесены ошибки в позиции: {error_positions}")
    print(f"Слово с ошибками Yn:\n{''.join(map(str, yn))}")

    # Декодирование
    yn_star, corr_pos, syndromes = decode_and_correct(yn, k1, k2, num_parity_groups)

    print("\nСиндромы:")
    print(f"  Строк:         {syndromes['row']}")
    print(f"  Столбцов:      {syndromes['col']}")
    if syndromes['main_diag'] is not None:
        print(f"  Главных диаг.: {syndromes['main_diag']}")
        print(f"  Побочных диаг.:{syndromes['anti_diag']}")
    if syndromes['overall'] is not None:
        print(f"  Общего:        {syndromes['overall']}")

    print(f"\nИсправленные позиции: {corr_pos}")
    print(f"Исправленное слово Yn*:\n{''.join(map(str, yn_star))}")

    if np.array_equal(yn_star, xn):
        print("\n>>> Ошибки успешно исправлены. Yn* совпадает с Xn.")
    else:
        print("\n>>> Полное исправление не удалось (характерно для кратности > 1).")

    # Анализ
    run = input("Запустить количественный анализ? (y/n) [y]: ").strip().lower() or 'y'
    if run != 'n':
        trials = input("Число испытаний на каждую кратность [50]: ").strip() or '50'
        max_err = input("Максимальная кратность ошибки [2]: ").strip() or '2'
        results = analyze_correcting_ability(k1, k2, num_parity_groups,
                                            int(trials), int(max_err))
        print(f"\nРезультаты (N1={trials}):")
        print(f"{'i':<4} {'N2 (обнар.)':<12} {'N3 (испр.)':<12} {'N2/N1':<8} {'N3/N1':<8}")
        for i, res in results.items():
            print(f"{i:<4} {res['N2']:<12} {res['N3']:<12} "
                  f"{res['N2_N1']:<8.3f} {res['N3_N1']:<8.3f}")

    print("\nПрограмма завершена.")

if __name__ == "__main__":
    main()