def xtime(a):
    a <<= 1
    if a & 0x100:
        a ^= 0x11B
    return a


def mul(a, b):
    result = 0
    while b:
        if b & 1:
            result ^= a
        a = xtime(a)
        b >>= 1
    return result


def rotl8(value, count):
    return ((value << count) | (value >> (8 - count))) & 0xFF


def build_sbox():
    inverse = [0] * 256
    for x in range(1, 256):
        for y in range(1, 256):
            if mul(x, y) == 1:
                inverse[x] = y
                break
    box = [0] * 256
    for x in range(256):
        b = inverse[x]
        box[x] = (b ^ rotl8(b, 1) ^ rotl8(b, 2) ^ rotl8(b, 3) ^ rotl8(b, 4) ^ 0x63) & 0xFF
    return box


S = build_sbox()
INV_S = [0] * 256
for i in range(256):
    INV_S[S[i]] = i

RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def expand_key(key):
    words = [list(key[i * 4:i * 4 + 4]) for i in range(4)]
    for i in range(4, 44):
        temp = list(words[i - 1])
        if i % 4 == 0:
            temp = temp[1:] + temp[:1]
            temp = [S[b] for b in temp]
            temp[0] ^= RCON[i // 4 - 1]
        words.append([words[i - 4][j] ^ temp[j] for j in range(4)])
    round_keys = []
    for r in range(11):
        round_key = []
        for w in range(4):
            round_key += words[4 * r + w]
        round_keys.append(round_key)
    return round_keys


def add_round_key(state, round_key):
    for i in range(16):
        state[i] ^= round_key[i]


def sub_bytes(state, inverse):
    table = INV_S if inverse else S
    for i in range(16):
        state[i] = table[state[i]]


def shift_rows(state, inverse):
    copy = list(state)
    for row in range(4):
        for col in range(4):
            from_col = (col - row + 4) % 4 if inverse else (col + row) % 4
            state[4 * col + row] = copy[4 * from_col + row]


def mix_columns(state, inverse):
    for col in range(4):
        a = state[4 * col]
        b = state[4 * col + 1]
        c = state[4 * col + 2]
        d = state[4 * col + 3]
        if inverse:
            state[4 * col] = mul(a, 14) ^ mul(b, 11) ^ mul(c, 13) ^ mul(d, 9)
            state[4 * col + 1] = mul(a, 9) ^ mul(b, 14) ^ mul(c, 11) ^ mul(d, 13)
            state[4 * col + 2] = mul(a, 13) ^ mul(b, 9) ^ mul(c, 14) ^ mul(d, 11)
            state[4 * col + 3] = mul(a, 11) ^ mul(b, 13) ^ mul(c, 9) ^ mul(d, 14)
        else:
            state[4 * col] = mul(a, 2) ^ mul(b, 3) ^ c ^ d
            state[4 * col + 1] = a ^ mul(b, 2) ^ mul(c, 3) ^ d
            state[4 * col + 2] = a ^ b ^ mul(c, 2) ^ mul(d, 3)
            state[4 * col + 3] = mul(a, 3) ^ b ^ c ^ mul(d, 2)


def pad(data):
    size = 16 - len(data) % 16
    return data + bytes([size]) * size


def unpad(data):
    size = data[-1]
    if size < 1 or size > 16:
        raise ValueError("invalid padding")
    if data[-size:] != bytes([size]) * size:
        raise ValueError("invalid padding")
    return data[:-size]


def xor_bytes(left, right):
    return bytes(a ^ b for a, b in zip(left, right))


def ecb_encrypt(data, encrypt_block, round_keys):
    padded = pad(data)
    result = b""
    for i in range(0, len(padded), 16):
        result += encrypt_block(padded[i:i + 16], round_keys)
    return result


def ecb_decrypt(data, decrypt_block, round_keys):
    padded = b""
    for i in range(0, len(data), 16):
        padded += decrypt_block(data[i:i + 16], round_keys)
    return unpad(padded)


def encrypt_block(block, round_keys):
    state = list(block)
    add_round_key(state, round_keys[0])
    for round_number in range(1, 10):
        sub_bytes(state, False)
        shift_rows(state, False)
        mix_columns(state, False)
        add_round_key(state, round_keys[round_number])
    sub_bytes(state, False)
    shift_rows(state, False)
    add_round_key(state, round_keys[10])
    return bytes(state)


def decrypt_block(block, round_keys):
    state = list(block)
    add_round_key(state, round_keys[10])
    for round_number in range(9, 0, -1):
        shift_rows(state, True)
        sub_bytes(state, True)
        add_round_key(state, round_keys[round_number])
        mix_columns(state, True)
    shift_rows(state, True)
    sub_bytes(state, True)
    add_round_key(state, round_keys[0])
    return bytes(state)
