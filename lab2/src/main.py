import random
import sys
from itertools import product


def to_str(data):
    return ''.join(str(x) for x in data)


def convert_text(text):
    result = []
    for byte in text.encode('utf-8'):
        result.extend(int(bit) for bit in f'{byte:08b}')
    return result


def create_hamming_matrix(k):
    r = 0
    while 2 ** r < k + r + 1:
        r += 1

    n = k + r
    matrix = []

    for i in range(r):
        matrix.append([(j >> i) & 1 for j in range(1, n + 1)])

    return r, n, matrix


def get_parity(matrix, data):
    values = []
    for row in matrix:
        values.append(sum(a * b for a, b in zip(row, data)) % 2)
    return values


def part1(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        bits = convert_text(file.read().strip('\n'))

    k = len(bits)
    if k < 16:
        sys.exit('Сообщение в бинарном виде должно быть не менее 16 бит')

    r, n, matrix = create_hamming_matrix(k)
    positions = {2 ** i - 1 for i in range(r)}

    xn = []
    source = iter(bits)

    for i in range(n):
        xn.append(0 if i in positions else next(source))

    xr = get_parity(matrix, xn)

    for i, pos in enumerate(sorted(positions)):
        xn[pos] = xr[i]

    print('\n' + '=' * 65)
    print('          ЧАСТЬ 1. КОД ХЕММИНГА')
    print('=' * 65)

    print(f'\nИсходные данные:')
    print(f'  Информационное слово : {to_str(bits)}')
    print(f'  Количество бит k     : {k}')
    print(f'  Проверочных бит r    : {r}')
    print(f'  Длина кодового слова : {n}')

    print('\nПроверочная матрица:')
    for i, row in enumerate(matrix, 1):
        print(f'  H[{i}] = {to_str(row)}')

    print('\nФормирование кодового слова:')
    print(f'  Информационные биты : {to_str(bits)}')
    print(f'  Проверочные биты    : {to_str(xr)}')
    print(f'  Кодовое слово Xn    : {to_str(xn)}')

    for errors in range(3):
        en = [0] * n

        for pos in random.sample(range(n), errors):
            en[pos] = 1

        yn = [x ^ e for x, e in zip(xn, en)]
        yr = [yn[pos] for pos in sorted(positions)]

        temp = yn.copy()
        for pos in positions:
            temp[pos] = 0

        yr_new = get_parity(matrix, temp)
        syndrome = [a ^ b for a, b in zip(yr, yr_new)]

        error_pos = sum(bit << i for i, bit in enumerate(syndrome))

        corrected = yn.copy()
        error_vector = [0] * n

        if 0 < error_pos <= n:
            corrected[error_pos - 1] ^= 1
            error_vector[error_pos - 1] = 1

        print('\n' + '-' * 65)
        print(f'          ПРОВЕРКА ПРИ {errors} ОШИБКАХ')
        print('-' * 65)

        print(f'  Полученное слово Yn  : {to_str(yn)}')
        print(f'  Проверочные биты Yr  : {to_str(yr)}')
        print(f'  Повторный расчёт Yr  : {to_str(yr_new)}')
        print(f'  Синдром              : {to_str(syndrome)}')
        print(f'  Позиция по синдрому  : {error_pos}')
        print(f'  Вектор ошибок En     : {to_str(error_vector)}')

        print('\nРезультат декодирования:')
        print(f'  Исправленное слово   : {to_str(corrected)}')
        print(f'  Исходное слово       : {to_str(xn)}')

        if corrected == xn:
            print('  Результат            : слово восстановлено правильно')
        else:
            print('  Результат            : слово отличается от исходного')

    print('\n' + '=' * 65)
    print('             ЗАВЕРШЕНИЕ ПЕРВОЙ ЧАСТИ')
    print('=' * 65)


DIRECTIONS_2D = [
    (0, 1),
    (1, 0),
    (1, 1),
    (1, -1)
]

DIRECTIONS_3D = [
    (0, 1, 0),
    (1, 0, 0),
    (0, 0, 1),
    (1, 1, 1),
    (1, -1, 1)
]


def generate_lines(dimensions, directions):
    coordinates = list(product(*(range(size) for size in dimensions)))
    indexes = {point: i for i, point in enumerate(coordinates)}
    result = []

    for direction in directions:
        for point in coordinates:
            previous = tuple(x - d for x, d in zip(point, direction))

            if previous in indexes:
                continue

            current = point
            line = []

            while current in indexes:
                line.append(indexes[current])
                current = tuple(x + d for x, d in zip(current, direction))

            result.append(line)

    return result


def make_codeword(data, lines):
    checks = []

    for line in lines:
        checks.append(sum(data[i] for i in line) % 2)

    return data + checks


def correct_errors(word, k, lines, cell_lines):
    result = word.copy()
    detected = False

    for _ in range(len(result)):
        invalid = set()

        for j, line in enumerate(lines):
            if (result[k + j] + sum(result[i] for i in line)) % 2:
                invalid.add(j)

        if not invalid:
            break

        detected = True

        if len(invalid) == 1:
            index = k + next(iter(invalid))
            result[index] ^= 1
            continue

        candidates = [
            i for i in range(k)
            if cell_lines[i].issubset(invalid)
        ]

        if len(candidates) != 1:
            break

        result[candidates[0]] ^= 1

    return result, detected


def part2(k=20, trials=10000, max_errors=6):
    configurations = [
        ((4, 5), (2, 3)),
        ((2, 10), (2, 3)),
        ((2, 5, 2), (2, 3, 4, 5)),
        ((2, 2, 5), (2, 3, 4, 5))
    ]

    print('\n' + '=' * 65)
    print('       ЧАСТЬ 2. ИТЕРАТИВНОЕ КОДИРОВАНИЕ')
    print('=' * 65)
    print(f'\nДлина информационного слова: {k} бит')
    print(f'Количество испытаний       : {trials}')
    print(f'Максимальное число ошибок  : {max_errors}')

    for dimensions, groups in configurations:
        print('\n' + '#' * 65)
        print(f'РАЗМЕРНОСТЬ МАТРИЦЫ: {" x ".join(map(str, dimensions))}')
        print('#' * 65)

        for group_count in groups:
            directions = DIRECTIONS_2D if len(dimensions) == 2 else DIRECTIONS_3D
            lines = generate_lines(dimensions, directions[:group_count])

            cell_lines = []
            for i in range(k):
                related = {
                    j for j, line in enumerate(lines)
                    if i in line
                }
                cell_lines.append(related)

            xk = [random.randrange(2) for _ in range(k)]
            xn = make_codeword(xk, lines)
            n = len(xn)

            print(f'\nГрупп паритетов: {group_count}')
            print(f'  Информационное слово : {to_str(xk)}')
            print(f'  Кодовое слово Xn     : {to_str(xn)}')
            print(f'  Размер кодового слова: {n} бит')

            print('\n  Результаты моделирования:')
            print('  ' + '-' * 59)
            print(f'  {"Ошибок":<10} {"Обнаружено":<17} {"Исправлено":<17}')
            print('  ' + '-' * 59)

            for error_count in range(1, min(max_errors, n) + 1):
                detected_count = 0
                corrected_count = 0

                for _ in range(trials):
                    yn = xn.copy()

                    for pos in random.sample(range(n), error_count):
                        yn[pos] ^= 1

                    result, detected = correct_errors(
                        yn, k, lines, cell_lines
                    )

                    detected_count += detected
                    corrected_count += result == xn

                detected_percent = detected_count / trials * 100
                corrected_percent = corrected_count / trials * 100

                print(
                    f'  {error_count:<10} '
                    f'{detected_percent:>6.2f}% ({detected_count:<5}) '
                    f'{corrected_percent:>6.2f}% ({corrected_count:<5})'
                )

            print('  ' + '-' * 59)

    print('\n' + '=' * 65)
    print('             ЗАВЕРШЕНИЕ ВТОРОЙ ЧАСТИ')
    print('=' * 65)


if __name__ == '__main__':
    print('============================================================ p1')
    part1(sys.argv[1] if len(sys.argv) > 1 else 'input.txt')

    print('\n============================================================ p2')
    part2()
