H = [
    0xB1, 0x94, 0xBA, 0xC8, 0x0A, 0x08, 0xF5, 0x3B, 0x36, 0x6D, 0x00, 0x8E, 0x58, 0x4A, 0x5D, 0xE4,
    0x85, 0x04, 0xFA, 0x9D, 0x1B, 0xB6, 0xC7, 0xAC, 0x25, 0x2E, 0x72, 0xC2, 0x02, 0xFD, 0xCE, 0x0D,
    0x5B, 0xE3, 0xD6, 0x12, 0x17, 0xB9, 0x61, 0x81, 0xFE, 0x67, 0x86, 0xAD, 0x71, 0x6B, 0x89, 0x0B,
    0x5C, 0xB0, 0xC0, 0xFF, 0x33, 0xC3, 0x56, 0xB8, 0x35, 0xC4, 0x05, 0xAE, 0xD8, 0xE0, 0x7F, 0x99,
    0xE1, 0x2B, 0xDC, 0x1A, 0xE2, 0x82, 0x57, 0xEC, 0x70, 0x3F, 0xCC, 0xF0, 0x95, 0xEE, 0x8D, 0xF1,
    0xC1, 0xAB, 0x76, 0x38, 0x9F, 0xE6, 0x78, 0xCA, 0xF7, 0xC6, 0xF8, 0x60, 0xD5, 0xBB, 0x9C, 0x4F,
    0xF3, 0x3C, 0x65, 0x7B, 0x63, 0x7C, 0x30, 0x6A, 0xDD, 0x4E, 0xA7, 0x79, 0x9E, 0xB2, 0x3D, 0x31,
    0x3E, 0x98, 0xB5, 0x6E, 0x27, 0xD3, 0xBC, 0xCF, 0x59, 0x1E, 0x18, 0x1F, 0x4C, 0x5A, 0xB7, 0x93,
    0xE9, 0xDE, 0xE7, 0x2C, 0x8F, 0x0C, 0x0F, 0xA6, 0x2D, 0xDB, 0x49, 0xF4, 0x6F, 0x73, 0x96, 0x47,
    0x06, 0x07, 0x53, 0x16, 0xED, 0x24, 0x7A, 0x37, 0x39, 0xCB, 0xA3, 0x83, 0x03, 0xA9, 0x8B, 0xF6,
    0x92, 0xBD, 0x9B, 0x1C, 0xE5, 0xD1, 0x41, 0x01, 0x54, 0x45, 0xFB, 0xC9, 0x5E, 0x4D, 0x0E, 0xF2,
    0x68, 0x20, 0x80, 0xAA, 0x22, 0x7D, 0x64, 0x2F, 0x26, 0x87, 0xF9, 0x34, 0x90, 0x40, 0x55, 0x11,
    0xBE, 0x32, 0x97, 0x13, 0x43, 0xFC, 0x9A, 0x48, 0xA0, 0x2A, 0x88, 0x5F, 0x19, 0x4B, 0x09, 0xA1,
    0x7E, 0xCD, 0xA4, 0xD0, 0x15, 0x44, 0xAF, 0x8C, 0xA5, 0x84, 0x50, 0xBF, 0x66, 0xD2, 0xE8, 0x8A,
    0xA2, 0xD7, 0x46, 0x52, 0x42, 0xA8, 0xDF, 0xB3, 0x69, 0x74, 0xC5, 0x51, 0xEB, 0x23, 0x29, 0x21,
    0xD4, 0xEF, 0xD9, 0xB4, 0x3A, 0x62, 0x28, 0x75, 0x91, 0x14, 0x10, 0xEA, 0x77, 0x6C, 0xDA, 0x1D
]

KEY_INDEX = [
    [0, 1, 2, 3, 4, 5, 6],
    [7, 0, 1, 2, 3, 4, 5],
    [6, 7, 0, 1, 2, 3, 4],
    [5, 6, 7, 0, 1, 2, 3],
    [4, 5, 6, 7, 0, 1, 2],
    [3, 4, 5, 6, 7, 0, 1],
    [2, 3, 4, 5, 6, 7, 0],
    [1, 2, 3, 4, 5, 6, 7]
]

MASK32 = 0xFFFFFFFF


def rotl32(x, r):
    return ((x << r) | (x >> (32 - r))) & MASK32


def g(x, r):
    val = (H[(x >> 24) & 0xFF] << 24) | (H[(x >> 16) & 0xFF] << 16) | (H[(x >> 8) & 0xFF] << 8) | H[x & 0xFF]
    return rotl32(val, r)


def load32(block, i):
    return block[i] | (block[i + 1] << 8) | (block[i + 2] << 16) | (block[i + 3] << 24)


def store32(v):
    return bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF])


def expand_key(key):
    return [load32(key, 4 * i) for i in range(8)]


def encrypt_block(block, key):
    a = load32(block, 0)
    b = load32(block, 4)
    c = load32(block, 8)
    d = load32(block, 12)
    e = 0
    for i in range(8):
        b ^= g((a + key[KEY_INDEX[i][0]]) & MASK32, 5)
        c ^= g((d + key[KEY_INDEX[i][1]]) & MASK32, 21)
        a = (a - g((b + key[KEY_INDEX[i][2]]) & MASK32, 13)) & MASK32
        e = (g((b + c + key[KEY_INDEX[i][3]]) & MASK32, 21) ^ (i + 1)) & MASK32
        b = (b + e) & MASK32
        c = (c - e) & MASK32
        d = (d + g((c + key[KEY_INDEX[i][4]]) & MASK32, 13)) & MASK32
        b ^= g((a + key[KEY_INDEX[i][5]]) & MASK32, 21)
        c ^= g((d + key[KEY_INDEX[i][6]]) & MASK32, 5)
        a, b = b, a
        c, d = d, c
        b, c = c, b
    out = b""
    for w in (b, d, a, c):
        out += store32(w)
    return out


def decrypt_block(block, key):
    a = load32(block, 0)
    b = load32(block, 4)
    c = load32(block, 8)
    d = load32(block, 12)
    e = 0
    for i in range(8):
        b ^= g((a + key[KEY_INDEX[7 - i][6]]) & MASK32, 5)
        c ^= g((d + key[KEY_INDEX[7 - i][5]]) & MASK32, 21)
        a = (a - g((b + key[KEY_INDEX[7 - i][4]]) & MASK32, 13)) & MASK32
        e = (g((b + c + key[KEY_INDEX[7 - i][3]]) & MASK32, 21) ^ (8 - i)) & MASK32
        b = (b + e) & MASK32
        c = (c - e) & MASK32
        d = (d + g((c + key[KEY_INDEX[7 - i][2]]) & MASK32, 13)) & MASK32
        b ^= g((a + key[KEY_INDEX[7 - i][1]]) & MASK32, 21)
        c ^= g((d + key[KEY_INDEX[7 - i][0]]) & MASK32, 5)
        a, b = b, a
        c, d = d, c
        a, d = d, a
    out = b""
    for w in (c, a, d, b):
        out += store32(w)
    return out


def xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


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


def keystream(encrypt_block, key, nonce, length):
    s = encrypt_block(nonce, key)
    result = b""
    for i in range(0, length, 16):
        block_len = min(16, length - i)
        s_int = int.from_bytes(s, "little") + 1
        s = s_int.to_bytes(16, "little")
        t = encrypt_block(s, key)
        result += t[:block_len]
    return result


def ctr_crypt(data, encrypt_block, key, nonce):
    return xor_bytes(data, keystream(encrypt_block, key, nonce, len(data)))


def ecb_encrypt(data, encrypt_block, key):
    padded = pad(data)
    result = b""
    for i in range(0, len(padded), 16):
        result += encrypt_block(padded[i:i + 16], key)
    return result


def ecb_decrypt(data, decrypt_block, key):
    padded = b""
    for i in range(0, len(data), 16):
        padded += decrypt_block(data[i:i + 16], key)
    return unpad(padded)


if __name__ == "__main__":
    key = bytes.fromhex("E9DEE72C8F0C0FA62DDB49F46F73964706075316ED247A3739CBA38303A98BF6")
    nonce = bytes.fromhex("BE32971343FC9A48A02A885F194B09A1")
    round_key = expand_key(key)
    block = bytes.fromhex("B194BAC80A08F53B366D008E584A5DE4")
    cipher = ctr_crypt(block, encrypt_block, round_key, nonce)
    print(cipher == bytes.fromhex("52C9AF96FF50F64435FC43DEF56BD797"))
    plain = ctr_crypt(cipher, encrypt_block, round_key, nonce)
    print(plain == block)
    cipher = ecb_encrypt(block, encrypt_block, round_key)
    plain = ecb_decrypt(cipher, decrypt_block, round_key)
    print(plain == block)