import struct

BLOCK_SIZE = 16
MASK = 0xFFFFFFFF

H = bytes.fromhex("""
B1 94 BA C8 0A 08 F5 3B 36 6D 00 8E 58 4A 5D E4
85 04 FA 9D 1B B6 C7 AC 25 2E 72 C2 02 FD CE 0D
5B E3 D6 12 17 B9 61 81 FE 67 86 AD 71 6B 89 0B
5C B0 C0 FF 33 C3 56 B8 35 C4 05 AE D8 E0 7F 99
E1 2B DC 1A E2 82 57 EC 70 3F CC F0 95 EE 8D F1
C1 AB 76 38 9F E6 78 CA F7 C6 F8 60 D5 BB 9C 4F
F3 3C 65 7B 63 7C 30 6A DD 4E A7 79 9E B2 3D 31
3E 98 B5 6E 27 D3 BC CF 59 1E 18 1F 4C 5A B7 93
E9 DE E7 2C 8F 0C 0F A6 2D DB 49 F4 6F 73 96 47
06 07 53 16 ED 24 7A 37 39 CB A3 83 03 A9 8B F6
92 BD 9B 1C E5 D1 41 01 54 45 FB C9 5E 4D 0E F2
68 20 80 AA 22 7D 64 2F 26 87 F9 34 90 40 55 11
BE 32 97 13 43 FC 9A 48 A0 2A 88 5F 19 4B 09 A1
7E CD A4 D0 15 44 AF 8C A5 84 50 BF 66 D2 E8 8A
A2 D7 46 52 42 A8 DF B3 69 74 C5 51 EB 23 29 21
D4 EF D9 B4 3A 62 28 75 91 14 10 EA 77 6C DA 1D
""")


def g(value: int, shift: int) -> int:
    """Подстановка четырёх байтов и циклический сдвиг влево."""
    value &= MASK
    substituted = (
        H[value & 0xFF]
        | H[(value >> 8) & 0xFF] << 8
        | H[(value >> 16) & 0xFF] << 16
        | H[(value >> 24) & 0xFF] << 24
    )
    return ((substituted << shift) | (substituted >> (32 - shift))) & MASK


class Belt:
    """Хранит 56 подключей, полученных циклическим повторением ключа."""

    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("Ключ БелТ должен содержать ровно 32 байта.")
        words = struct.unpack("<8I", key)
        self.round_keys = tuple(words[index % 8] for index in range(56))

    def encrypt_block(self, block: bytes) -> bytes:
        if len(block) != BLOCK_SIZE:
            raise ValueError("Блок должен содержать ровно 16 байт.")
        a, b, c, d = struct.unpack("<4I", block)

        for round_number in range(1, 9):
            k = self.round_keys[7 * (round_number - 1):7 * round_number]
            b ^= g(a + k[0], 5)
            c ^= g(d + k[1], 21)
            a = (a - g(b + k[2], 13)) & MASK
            e = g(b + c + k[3], 21) ^ round_number
            b = (b + e) & MASK
            c = (c - e) & MASK
            d = (d + g(c + k[4], 13)) & MASK
            b ^= g(a + k[5], 21)
            c ^= g(d + k[6], 5)

            a, b, c, d = b, d, a, c

        return struct.pack("<4I", b, d, a, c)

    def decrypt_block(self, block: bytes) -> bytes:
        if len(block) != BLOCK_SIZE:
            raise ValueError("Блок должен содержать ровно 16 байт.")
        b, d, a, c = struct.unpack("<4I", block)

        for round_number in range(8, 0, -1):
            k = self.round_keys[7 * (round_number - 1):7 * round_number]
            a, b, c, d = c, a, d, b
            c ^= g(d + k[6], 5)
            b ^= g(a + k[5], 21)
            d = (d - g(c + k[4], 13)) & MASK
            e = g(b + c + k[3], 21) ^ round_number
            c = (c + e) & MASK
            b = (b - e) & MASK
            a = (a + g(b + k[2], 13)) & MASK
            c ^= g(d + k[1], 21)
            b ^= g(a + k[0], 5)

        return struct.pack("<4I", a, b, c, d)


def encrypt_block(pt_block: bytes, key: bytes) -> bytes:
    return Belt(key).encrypt_block(pt_block)


def decrypt_block(ct_block: bytes, key: bytes) -> bytes:
    return Belt(key).decrypt_block(ct_block)
