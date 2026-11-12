import numpy as np

n=4
k=7
G=np.array([[1, 0, 0, 0, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 1],
    [0, 0, 1, 0, 0, 1, 1],
    [0, 0, 0, 1, 1, 1, 1]])

H=np.array([[1, 1, 0],
            [1, 0, 1],
            [0, 1, 1],
            [1, 1, 1],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]])
H4 = np.column_stack((
    H,
    np.ones(7, dtype=int)
))

H4 = np.vstack((
    H4,
    [0, 0, 0, 1]
)) % 2

import random

def pomeha(file_name, n, p):
    data = bytearray(read_file(file_name))
    if not 0 <= p <= 1:
        raise ValueError("p должна находиться в диапазоне от 0 до 1")
    if not 0 <= n <= 8:
        raise ValueError("n должно быть от 0 до 8")
    errors = 0
    for i in range(len(data)):
        positions = random.sample(range(8), n)
        for pos in positions:
            if random.random() < p:
                data[i] ^= 1 << pos
                errors += 1
    write_file(file_name, data)
    print(f"Количество байтов: {len(data)}")
    print(f"Максимальное количество ошибок: {len(data) * n}")
    print(f"Фактически внесено ошибок: {errors}")

def part1():
    coder("text.txt")
    pomeha("encoded.txt",2,1)
    decoder()

def part2():
    coder4("text.txt")
    pomeha("encoded4.txt",1,1)
    decoder4()

def coder(file_name):
    data = read_file(file_name)
    encoded = bytearray()
    buffer = []
    for byte in data:
        bits = [(byte >> i) & 1 for i in range(7, -1, -1)]
        groups = [
            bits[:4],
            bits[4:]
        ]
        for group in groups:
            encoded_bits = np.array(group) @ G
            encoded_bits = encoded_bits % 2
            buffer.extend(encoded_bits.tolist())
            while len(buffer) >= 8:
                byte_bits = buffer[:8]
                buffer = buffer[8:]
                value = 0
                for bit in byte_bits:
                    value = (value << 1) | bit
                encoded.append(value)
    if len(buffer) > 0:
        buffer.extend([0] * (8 - len(buffer)))
        value = 0
        for bit in buffer:
            value = (value << 1) | bit
        encoded.append(value)
    write_file("encoded.txt", encoded)

def syndrome(code):
    code = np.array(code)

    # Считаем синдром
    s = code @ H
    s = s % 2

    print("7 бит:       ", code)
    print("Синдром:     ", s)

    # Если синдром не равен [0, 0, 0],
    # значит есть ошибка
    if np.any(s):
        # Ищем столбец H, совпадающий с синдромом
        for i in range(7):
            if np.array_equal(H[i], s):
                print("Ошибка в бите:", i + 1)

                # Исправляем ошибочный бит
                code[i] ^= 1

                break

    # После исправления первые 4 бита -
    # информационные, потому что G имеет вид [I | P]
    information_bits = code[:4]

    print("Исправленные: ", code)
    print("4 инф. бита:  ", information_bits)
    print()

    return information_bits.tolist()

def decoder():
    data = read_file("encoded.txt")

    decoded = bytearray()
    buffer = []

    for byte in data:

        # Превращаем байт в 8 бит
        bits = [(byte >> i) & 1 for i in range(7, -1, -1)]

        # Добавляем биты в буфер
        buffer.extend(bits)

        # Из буфера берём по 14 бит
        while len(buffer) >= 14:

            block = buffer[:14]
            buffer = buffer[14:]

            # Первые 7 бит
            group1 = block[:7]

            # Вторые 7 бит
            group2 = block[7:]

            # Декодируем обе группы
            info1 = syndrome(group1)
            info2 = syndrome(group2)

            # Получили 4 + 4 = 8 информационных бит
            decoded_bits = info1 + info2

            print("Декодированные 8 бит:", decoded_bits)
            print()

            # Превращаем 8 бит обратно в байт
            value = 0

            for bit in decoded_bits:
                value = (value << 1) | bit

            decoded.append(value)

    write_file("decoded.txt", decoded)

def coder4(file_name):
    data = read_file(file_name)

    encoded = bytearray()
    buffer = []

    for byte in data:
        bits = [(byte >> i) & 1 for i in range(7, -1, -1)]

        groups = [
            bits[:4],
            bits[4:]
        ]

        for group in groups:
            # Кодируем 4 информационных бита
            encoded_bits = (np.array(group) @ G) % 2

            # Общий бит чётности: сумма всех 7 бит по модулю 2
            parity = int(np.sum(encoded_bits) % 2)

            # Получаем кодовое слово из 8 бит
            codeword = encoded_bits.tolist() + [parity]

            buffer.extend(codeword)

            # Записываем полные байты
            while len(buffer) >= 8:
                byte_bits = buffer[:8]
                buffer = buffer[8:]

                value = 0
                for bit in byte_bits:
                    value = (value << 1) | int(bit)

                encoded.append(value)

    # Для Hamming(8,4) каждый блок занимает ровно 8 бит,
    # поэтому при корректной работе остатка быть не должно.
    if buffer:
        raise RuntimeError("Неожиданный остаток битового буфера")

    write_file("encoded4.txt", encoded)

def syndrome4(code):
    code = np.array(code, dtype=int)

    # Вычисляем расширенный синдром
    s = (code @ H4) % 2

    print("8 бит:          ", code.tolist())
    print("Синдром H4:     ", s.tolist())

    hamming_syndrome = s[:3]
    overall_parity = s[3]

    if np.any(hamming_syndrome):
        if overall_parity == 1:
            # Одиночная ошибка в первых семи битах
            for i in range(7):
                if np.array_equal(H[i], hamming_syndrome):
                    code[i] ^= 1
                    print("Исправлена ошибка в бите:", i + 1)
                    break
            else:
                raise ValueError("Не удалось определить ошибочный бит")

        else:
            # Ненулевой синдром при чётной общей чётности
            # указывает на обнаруженную двойную ошибку
            raise ValueError(
                "Обнаружена двойная ошибка. "
                "Кодовое слово нельзя надёжно декодировать."
            )

    elif overall_parity == 1:
        # Первые семь бит правильны, ошибка в восьмом
        code[7] ^= 1
        print("Исправлена ошибка в бите: 8")

    information_bits = code[:4].tolist()

    print("Исправленные:   ", code.tolist())
    print("4 инф. бита:    ", information_bits)
    print()

    return information_bits

def decoder4():
    data = read_file("encoded4.txt")

    decoded = bytearray()
    buffer = []
    half = None

    for byte in data:
        bits = [(byte >> i) & 1 for i in range(7, -1, -1)]
        buffer.extend(bits)

        while len(buffer) >= 8:
            block = buffer[:8]
            buffer = buffer[8:]

            info = syndrome4(block)

            if half is None:
                half = info
            else:
                decoded_bits = half + info
                half = None

                print("Декодированные 8 бит:", decoded_bits)
                print()

                value = 0
                for bit in decoded_bits:
                    value = (value << 1) | int(bit)

                decoded.append(value)

    if buffer or half is not None:
        raise ValueError("Закодированный файл имеет неполный блок")

    write_file("decoded4.txt", decoded)

def write_file(name:str, data):
    with open(name,'wb') as file:
      file.write(data)

def read_file(name:str):
    with open(name,'rb') as file:
        binary_content = file.read()
        return(binary_content)

if __name__=="__main__":
    #part1()
    part2()


