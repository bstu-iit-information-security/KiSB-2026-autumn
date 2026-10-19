
import random

ROWS = 4
COLS = 6
K = 24


# Создание матрицы 4 x 6
def make_matrix(bits):
    matrix = []

    for i in range(ROWS):
        row = []

        for j in range(COLS):
            row.append(bits[i * COLS + j])

        matrix.append(row)

    return matrix


# Вывод матрицы
def print_matrix(matrix):
    for row in matrix:
        print(" ".join(str(bit) for bit in row))

# Формирование групп паритетов
def make_groups(mode):
    data_groups = []
    names = []

    # Проверки по строкам
    for r in range(ROWS):
        group = []

        for c in range(COLS):
            group.append(r * COLS + c)

        data_groups.append(group)
        names.append("Строка " + str(r + 1))

    # Проверки по столбцам
    for c in range(COLS):
        group = []

        for r in range(ROWS):
            group.append(r * COLS + c)

        data_groups.append(group)
        names.append("Столбец " + str(c + 1))

    # Третье направление — диагонали
    if mode == 3:
        number = 1

        for difference in range(-(ROWS - 1), COLS):
            group = []

            for r in range(ROWS):
                for c in range(COLS):
                    if c - r == difference:
                        group.append(r * COLS + c)

            data_groups.append(group)
            names.append("Диагональ " + str(number))
            number += 1

    return data_groups, names


def encode(info, mode):
    data_groups, names = make_groups(mode)

    code = info.copy()
    groups = []
    parity_positions = []

    for group in data_groups:
        total = 0

        for position in group:
            total += code[position]

        parity = total % 2

        parity_position = len(code)
        code.append(parity)
        full_group = group.copy()
        full_group.append(parity_position)
        groups.append(full_group)
        parity_positions.append(parity_position)
    total = 0

    for bit in code:
        total += bit

    overall_parity = total % 2
    overall_position = len(code)
    code.append(overall_parity)
    overall_group = []

    for i in range(len(code)):
        overall_group.append(i)

    groups.append(overall_group)
    names.append("Общий паритет")

    return code, groups, names, parity_positions, overall_position

def print_code_table(code, mode, parity_positions,
                     overall_position):
    matrix = make_matrix(code[:K])

    print("\nТАБЛИЦА КОДОВОГО СЛОВА")
    print("-" * 53)
    print("       Информационные биты       | Pстр")

    for r in range(ROWS):
        print(
            " ".join(str(bit) for bit in matrix[r]),
            "|", code[parity_positions[r]]
        )

    print("-" * 53)

    print("Pстолб:", end=" ")

    for c in range(COLS):
        position = parity_positions[ROWS + c]
        print(code[position], end=" ")

    print()

    if mode == 3:
        print("\nПроверочные биты диагоналей:")

        for i in range(ROWS + COLS, len(parity_positions)):
            position = parity_positions[i]

            print(
                "P" + str(i - ROWS - COLS + 1)
                + " = " + str(code[position]),
                end="   "
            )

        print()

    print(
        "\nОбщий бит паритета Pобщ =",
        code[overall_position]
    )

    print("\nПолное кодовое слово:")
    print(" ".join(str(bit) for bit in code))
    print("Длина кодового слова:", len(code))

def get_syndrome(code, groups):
    syndrome = []
    for i in range(len(groups)):
        total = 0

        for position in groups[i]:
            total += code[position]

        if total % 2 != 0:
            syndrome.append(i)

    return syndrome


def make_errors(code, count=None, positions=None):
    result = code.copy()

    if positions is not None:
        # Пользователь вводит позиции начиная с 1
        selected = []
        for position in positions:
            if position < 1 or position > len(result):
                raise ValueError(
                    "Позиция вне диапазона кодового слова."
                )
            index = position - 1
            if index in selected:
                raise ValueError(
                    "Одна позиция указана несколько раз."
                )
            selected.append(index)
    else:
        if count is None:
            raise ValueError(
                "Укажите количество ошибок или позиции."
            )

        if count < 1 or count > len(result):
            raise ValueError(
                "Недопустимое количество ошибок."
            )

        selected = random.sample(range(len(result)), count)

    for position in selected:
        result[position] = 1 - result[position]
    positions_used = []

    for position in selected:
        positions_used.append(position + 1)

    return result, positions_used

def correct(code, groups):
    result = code.copy()

    for step in range(len(result)):
        syndrome = get_syndrome(result, groups)

        if len(syndrome) == 0:
            break

        found = False

        # Ищем бит, входящий во все нарушенные группы
        for position in range(len(result)):
            signature = []

            for i in range(len(groups)):
                if position in groups[i]:
                    signature.append(i)

            if signature == syndrome:
                result[position] = 1 - result[position]
                found = True
                break

        if not found:
            break

    return result

def count_errors(first, second):
    count = 0

    for i in range(len(first)):
        if first[i] != second[i]:
            count += 1

    return count


def task2():
    word = "101100011010110010011001"
    info = [int(bit) for bit in word]
    mode = 3
    code, groups, names, parity_positions, overall_position = (
        encode(info, mode)
    )
    print("\nИсходное кодовое слово X:")
    print_code_table(
        code, mode, parity_positions, overall_position
    )
    error_positions = [8]

    received, positions = make_errors(
        code, positions=error_positions
    )
    print("Полученное слово Y с ошибкой:")
    print("".join(str(bit) for bit in received))

    restored = correct(received, groups)

    print("\nИсправленное кодовое слово Y':")
    print("".join(str(bit) for bit in restored))

    print("\nТаблица исправленного слова:")
    print_code_table(
        restored, mode, parity_positions, overall_position
    )
    differences = count_errors(code, restored)
    print("\nРезультат проверки:")
    if restored == code:
        print("Кодовое слово восстановлено правильно.")
    else:
        print("Кодовое слово восстановлено не полностью.")
    print("Количество отличающихся битов:", differences)
    restored_info = restored[:K]
    print("\nВосстановленная информационная часть:")
    print("".join(str(bit) for bit in restored_info))
    if restored_info == info:
        print("Информационное слово восстановлено правильно.")
    else:
        print("В информационном слове остались ошибки.")

if __name__ == "__main__":
    task2()
