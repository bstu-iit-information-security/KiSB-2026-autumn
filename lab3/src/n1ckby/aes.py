BLOCK_SIZE = 16

S_BOX = bytes.fromhex(
    "63 7c 77 7b f2 6b 6f c5 30 01 67 2b fe d7 ab 76 "
    "ca 82 c9 7d fa 59 47 f0 ad d4 a2 af 9c a4 72 c0 "
    "b7 fd 93 26 36 3f f7 cc 34 a5 e5 f1 71 d8 31 15 "
    "04 c7 23 c3 18 96 05 9a 07 12 80 e2 eb 27 b2 75 "
    "09 83 2c 1a 1b 6e 5a a0 52 3b d6 b3 29 e3 2f 84 "
    "53 d1 00 ed 20 fc b1 5b 6a cb be 39 4a 4c 58 cf "
    "d0 ef aa fb 43 4d 33 85 45 f9 02 7f 50 3c 9f a8 "
    "51 a3 40 8f 92 9d 38 f5 bc b6 da 21 10 ff f3 d2 "
    "cd 0c 13 ec 5f 97 44 17 c4 a7 7e 3d 64 5d 19 73 "
    "60 81 4f dc 22 2a 90 88 46 ee b8 14 de 5e 0b db "
    "e0 32 3a 0a 49 06 24 5c c2 d3 ac 62 91 95 e4 79 "
    "e7 c8 37 6d 8d d5 4e a9 6c 56 f4 ea 65 7a ae 08 "
    "ba 78 25 2e 1c a6 b4 c6 e8 dd 74 1f 4b bd 8b 8a "
    "70 3e b5 66 48 03 f6 0e 61 35 57 b9 86 c1 1d 9e "
    "e1 f8 98 11 69 d9 8e 94 9b 1e 87 e9 ce 55 28 df "
    "8c a1 89 0d bf e6 42 68 41 99 2d 0f b0 54 bb 16"
)

_inverse = [0] * 256
for _index, _value in enumerate(S_BOX):
    _inverse[_value] = _index
INV_S_BOX = bytes(_inverse)


def xtime(value: int) -> int:
    """Умножение байта на 2 в поле GF(2^8)."""
    if value & 0x80:
        return ((value << 1) ^ 0x1B) & 0xFF
    return (value << 1) & 0xFF


def multiply(value: int, factor: int) -> int:
    """Умножение в GF(2^8) через xtime и XOR."""
    result = 0
    while factor:
        if factor & 1:
            result ^= value
        value = xtime(value)
        factor >>= 1
    return result


def expand_key(key: bytes) -> list:
    """Получить 11 раундовых ключей из 44 четырёхбайтовых слов."""
    if len(key) != BLOCK_SIZE:
        raise ValueError("Ключ AES-128 должен содержать ровно 16 байт.")

    words = [list(key[i:i + 4]) for i in range(0, BLOCK_SIZE, 4)]
    round_constant = 1

    for index in range(4, 44):
        temporary = words[index - 1].copy()
        if index % 4 == 0:
            temporary = temporary[1:] + temporary[:1]  # RotWord
            temporary = [S_BOX[value] for value in temporary]  # SubWord
            temporary[0] ^= round_constant
            round_constant = xtime(round_constant)
        words.append([
            words[index - 4][j] ^ temporary[j] for j in range(4)
        ])

    return [
        sum(words[start:start + 4], []) for start in range(0, 44, 4)
    ]


def add_round_key(state: list, round_key: list) -> list:
    return [value ^ key_byte for value, key_byte in zip(state, round_key)]


def sub_bytes(state: list, inverse: bool = False) -> list:
    table = INV_S_BOX if inverse else S_BOX
    return [table[value] for value in state]


def shift_rows(state: list, inverse: bool = False) -> list:
    result = [0] * BLOCK_SIZE
    direction = -1 if inverse else 1
    for row in range(4):
        for column in range(4):
            source_column = (column + direction * row) % 4
            result[4 * column + row] = state[4 * source_column + row]
    return result


def mix_columns(state: list, inverse: bool = False) -> list:
    matrix = (
        ((14, 11, 13, 9), (9, 14, 11, 13),
         (13, 9, 14, 11), (11, 13, 9, 14))
        if inverse else
        ((2, 3, 1, 1), (1, 2, 3, 1),
         (1, 1, 2, 3), (3, 1, 1, 2))
    )
    result = [0] * BLOCK_SIZE
    for column in range(4):
        for row in range(4):
            for index in range(4):
                result[4 * column + row] ^= multiply(
                    state[4 * column + index], matrix[row][index]
                )
    return result


def encrypt_block(pt_block: bytes, key: bytes) -> bytes:
    """Зашифровать строго один блок, без паддинга."""
    if len(pt_block) != BLOCK_SIZE:
        raise ValueError("Блок AES должен содержать ровно 16 байт.")
    round_keys = expand_key(key)
    state = add_round_key(list(pt_block), round_keys[0])

    for round_number in range(1, 10):
        state = sub_bytes(state)
        state = shift_rows(state)
        state = mix_columns(state)
        state = add_round_key(state, round_keys[round_number])

    state = sub_bytes(state)
    state = shift_rows(state)
    state = add_round_key(state, round_keys[10])
    return bytes(state)


def decrypt_block(ct_block: bytes, key: bytes) -> bytes:
    """Расшифровать строго один блок, без снятия паддинга."""
    if len(ct_block) != BLOCK_SIZE:
        raise ValueError("Блок AES должен содержать ровно 16 байт.")
    round_keys = expand_key(key)
    state = add_round_key(list(ct_block), round_keys[10])

    for round_number in range(9, 0, -1):
        state = shift_rows(state, inverse=True)
        state = sub_bytes(state, inverse=True)
        state = add_round_key(state, round_keys[round_number])
        state = mix_columns(state, inverse=True)

    state = shift_rows(state, inverse=True)
    state = sub_bytes(state, inverse=True)
    state = add_round_key(state, round_keys[0])
    return bytes(state)
