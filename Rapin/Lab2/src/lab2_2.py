import numpy as np
import random

def binary_string_to_matrix(binary_str, k1, k2):
    """
    Преобразует двоичную строку длины k = k1 * k2
    в матрицу размера k1 x k2 (информационное слово Xk).
    """
    if len(binary_str) != k1 * k2:
        raise ValueError("Длина строки должна быть равна k1 * k2")
    bits = [int(b) for b in binary_str]
    matrix = np.array(bits).reshape(k1, k2)
    return matrix

def compute_row_parities(matrix):
    """
    Вычисление горизонтальных (строковых) паритетов.
    Для каждой строки сумма по модулю 2 (формула четности).
    """
    # Xh_i = sum_j X_ij mod 2
    return np.sum(matrix, axis=1) % 2

def compute_col_parities(matrix):
    """
    Вычисление вертикальных (столбцовых) паритетов.
    Для каждого столбца сумма по модулю 2.
    """
    # Xv_j = sum_i X_ij mod 2
    return np.sum(matrix, axis=0) % 2

def compute_overall_parity(row_parities, col_parities):
    """
    Вычисление паритета паритетов Xhv.
    Xhv = sum row_parities mod 2  (или sum col_parities).
    """
    return np.sum(row_parities) % 2

def encode_2d(info_matrix, num_parity_groups=3):
    """
    Кодирование двумерным итеративным кодом:
      2 - только строки и столбцы
      3 - строки, столбцы и паритет паритетов
    Возвращает кодовое слово Xn в виде плоского массива и расширенную матрицу с паритетами.
    """
    k1, k2 = info_matrix.shape
    row_p = compute_row_parities(info_matrix)
    col_p = compute_col_parities(info_matrix)
    overall = compute_overall_parity(row_p, col_p)

    # Формируем расширенную матрицу (k1+1) x (k2+1)
    # Информационные биты + строковые паритеты + столбцовые + угол
    extended = np.zeros((k1 + 1, k2 + 1), dtype=int)
    extended[:k1, :k2] = info_matrix
    extended[:k1, k2] = row_p          # горизонтальные паритеты справа
    extended[k1, :k2] = col_p          # вертикальные паритеты снизу

    if num_parity_groups >= 3:
        extended[k1, k2] = overall     # паритет паритетов
    else:
        extended[k1, k2] = 0           # не используем

    # Кодовое слово: сначала все информационные, затем паритеты
    # Порядок: строки матрицы слева направо, сверху вниз
    codeword = extended.flatten()
    return codeword, extended

def introduce_errors(codeword, num_errors):
    """
    Генерация ошибки произвольной кратности i.
    Случайным образом выбираются позиции и инвертируются биты.
    Возвращает Yn и список позиций ошибок.
    """
    n = len(codeword)
    if num_errors > n:
        num_errors = n
    positions = random.sample(range(n), num_errors)
    yn = codeword.copy()
    for pos in positions:
        yn[pos] = 1 - yn[pos]
    return yn, positions

def decode_and_correct_2d(yn, k1, k2, num_parity_groups=3):
    """
    Декодирование и исправление ошибок.
    Пересчитываем паритеты полученного слова и сравниваем с принятыми.
    Для одиночной ошибки: пересечение ненулевых синдромов строки и столбца
    указывает позицию ошибки.
    """
    # Восстанавливаем расширенную матрицу из Yn
    extended_recv = yn.reshape(k1 + 1, k2 + 1)
    info_recv = extended_recv[:k1, :k2]
    row_p_recv = extended_recv[:k1, k2]
    col_p_recv = extended_recv[k1, :k2]
    overall_recv = extended_recv[k1, k2]

    # Пересчитываем паритеты по принятым информационным битам
    row_p_calc = compute_row_parities(info_recv)
    col_p_calc = compute_col_parities(info_recv)
    overall_calc = compute_overall_parity(row_p_calc, col_p_calc)

    # Синдромы: разница принятых и вычисленных паритетов
    row_syndrome = (row_p_recv + row_p_calc) % 2
    col_syndrome = (col_p_recv + col_p_calc) % 2
    overall_syndrome = (overall_recv + overall_calc) % 2 if num_parity_groups >= 3 else 0

    # Определение позиций ошибок
    error_rows = np.where(row_syndrome == 1)[0]
    error_cols = np.where(col_syndrome == 1)[0]

    yn_corrected = yn.copy()
    corrected_positions = []

    # Простая коррекция одиночных ошибок в информационной части
    if len(error_rows) == 1 and len(error_cols) == 1:
        # Ошибка в информационном бите
        r, c = error_rows[0], error_cols[0]
        pos = r * (k2 + 1) + c
        yn_corrected[pos] = 1 - yn_corrected[pos]
        corrected_positions.append(pos)
    elif len(error_rows) == 1 and len(error_cols) == 0:
        # Ошибка в строковом паритете
        r = error_rows[0]
        pos = r * (k2 + 1) + k2
        yn_corrected[pos] = 1 - yn_corrected[pos]
        corrected_positions.append(pos)
    elif len(error_rows) == 0 and len(error_cols) == 1:
        # Ошибка в столбцовом паритете
        c = error_cols[0]
        pos = k1 * (k2 + 1) + c
        yn_corrected[pos] = 1 - yn_corrected[pos]
        corrected_positions.append(pos)
    elif num_parity_groups >= 3 and overall_syndrome == 1 and len(error_rows) == 0 and len(error_cols) == 0:
        # Ошибка в паритете паритетов
        pos = (k1 + 1) * (k2 + 1) - 1
        yn_corrected[pos] = 1 - yn_corrected[pos]
        corrected_positions.append(pos)

    # Для кратности >1 код может не исправить (как указано в методичке)

    return yn_corrected, corrected_positions, row_syndrome, col_syndrome, overall_syndrome

# Анализ корректирующей способности
def analyze_correcting_ability(k1, k2, num_parity_groups, num_trials, max_errors):
    results = {}
    k = k1 * k2
    n = (k1 + 1) * (k2 + 1)

    for i in range(1, max_errors + 1):
        N1 = num_trials
        N2 = 0  # правильно обнаружено (синдром ненулевой)
        N3 = 0  # правильно исправлено (Yn* == Xn)

        for _ in range(num_trials):
            # Случайное информационное слово
            info_bits = [random.randint(0, 1) for _ in range(k)]
            info_str = ''.join(map(str, info_bits))
            info_mat = binary_string_to_matrix(info_str, k1, k2)
            xn, _ = encode_2d(info_mat, num_parity_groups)

            yn, true_errors = introduce_errors(xn, i)
            yn_star, corr_pos, row_s, col_s, ov_s = decode_and_correct_2d(
                yn, k1, k2, num_parity_groups
            )

            # Обнаружение: если хотя бы один синдром ненулевой
            detected = np.any(row_s) or np.any(col_s) or (ov_s == 1)
            if detected:
                N2 += 1

            # Исправление: полное совпадение с исходным кодовым словом
            if np.array_equal(yn_star, xn):
                N3 += 1

        results[i] = {
            'N1': N1,
            'N2': N2,
            'N3': N3,
            'N2_N1': N2 / N1 if N1 > 0 else 0,
            'N3_N1': N3 / N1 if N1 > 0 else 0
        }
    return results

def print_matrix(matrix, title):
    """Печать матрицы в удобном виде."""
    print(title)
    for row in matrix:
        print(' '.join(map(str, row)))

def main():
    print("Итеративное кодирование")
    print("Доступные конфигурации матрицы:")
    print("1. k1=4, k2=4 (2D)")
    print("2. k1=8, k2=2 (2D)")
    print("3. k1=4, k2=2, z=2 (3D - упрощенная реализация через 2D слои)")
    print("4. k1=2, k2=4, z=2 (3D - упрощенная реализация через 2D слои)")
    print()

    # Выбор конфигурации
    choice = input("Выберите конфигурацию: ").strip()
    if choice == '2':
        k1, k2 = 8, 2
    elif choice == '3':
        k1, k2 = 4, 2
        print("Примечание: 3D реализовано как два слоя 4x2 с отдельными паритетами.")
    elif choice == '4':
        k1, k2 = 2, 4
        print("Примечание: 3D реализовано как два слоя 2x4 с отдельными паритетами.")
    else:
        k1, k2 = 4, 4

    k = k1 * k2
    print(f"\nВыбрано: k1={k1}, k2={k2}, k={k}")

    # Количество групп паритетов
    num_groups_str = input("Количество групп паритетов (2 или 3): ").strip()
    num_parity_groups = 3 if num_groups_str == '' else int(num_groups_str)
    if num_parity_groups not in (2, 3):
        num_parity_groups = 3
    print(f"Используется {num_parity_groups} групп паритетов")

    # Ввод информационного слова
    print(f"\nВведите информационное слово Xk ({k} бит, только 0 и 1)")
    print("или нажмите Enter для случайного слова:")
    info_input = input().strip()
    if info_input == '':
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

    # 1. Формирование матрицы
    info_matrix = binary_string_to_matrix(info_str, k1, k2)
    print_matrix(info_matrix, "\nИнформационная матрица Xk:")

    # 2-3. Вычисление паритетов и формирование кодового слова Xn
    xn, extended = encode_2d(info_matrix, num_parity_groups)
    print_matrix(extended, "\nРасширенная матрица (с паритетами):")
    print(f"\nКодовое слово Xn (длина n={len(xn)}):")
    print(''.join(map(str, xn)))

    # 4. Генерация ошибки
    err_str = input("\nВведите кратность ошибки i (целое >0) [1]: ").strip()
    num_errors = 1 if err_str == '' else int(err_str)
    yn, error_positions = introduce_errors(xn, num_errors)
    print(f"\nВнесены ошибки в позиции: {error_positions}")
    print(f"Слово с ошибками Yn:")
    print(''.join(map(str, yn)))

    # 5. Определение местоположения и исправление
    yn_star, corr_pos, row_s, col_s, ov_s = decode_and_correct_2d(
        yn, k1, k2, num_parity_groups
    )
    print(f"\nСиндром строк: {row_s}")
    print(f"Синдром столбцов: {col_s}")
    if num_parity_groups >= 3:
        print(f"Синдром паритета паритетов: {ov_s}")
    print(f"Исправленные позиции: {corr_pos}")
    print(f"Исправленное слово Yn*:")
    print(''.join(map(str, yn_star)))

    # Проверка совпадения
    if np.array_equal(yn_star, xn):
        print("\nОшибки успешно исправлены. Yn* совпадает с Xn.")
    else:
        print("\nПолное исправление не удалось (характерно для кратности >1).")

    # 6. Анализ корректирующей способности
    print("\nАнализ корректирующей способности")
    run_analysis = input("Запустить анализ? (y/n): ").strip().lower()
    if run_analysis != 'n':
        trials = input("Число испытаний на каждую кратность [100]: ").strip()
        num_trials = 100 if trials == '' else int(trials)
        max_err = input("Максимальная кратность ошибки для анализа [3]: ").strip()
        max_errors = 3 if max_err == '' else int(max_err)

        results = analyze_correcting_ability(
            k1, k2, num_parity_groups, num_trials, max_errors
        )
        print(f"\nРезультаты (N1={num_trials}):")
        print(f"{'Кратность i':<12} {'N2 (обнаружено)':<18} {'N3 (исправлено)':<18} {'N2/N1':<10} {'N3/N1':<10}")
        for i, res in results.items():
            print(f"{i:<12} {res['N2']:<18} {res['N3']:<18} {res['N2_N1']:<10.3f} {res['N3_N1']:<10.3f}")

    print("\nПрограмма завершена.")

if __name__ == "__main__":
    main()