"""Базовый блочный шифр СТБ 34.101.31 (БелТ): блок 128 бит, ключ 256 бит.
Модуль не знает о режимах работы: он шифрует/расшифровывает ровно один блок."""

BLOCK_SIZE = 16
KEY_SIZE = 32
MASK = 0xFFFFFFFF

_H_HEX = """
B194BAC80A08F53B366D008E584A5DE4
8504FA9D1BB6C7AC252E72C202FDCE0D
5BE3D61217B96181FE6786AD716B890B
5CB0C0FF33C356B835C405AED8E07F99
E12BDC1AE28257EC703FCCF095EE8DF1
C1AB76389FE678CAF7C6F860D5BB9C4F
F33C657B637C306ADD4EA7799EB23D31
3E98B56E27D3BCCF591E181F4C5AB793
E9DEE72C8F0C0FA62DDB49F46F739647
0607 5316ED247A3739CBA38303A98BF6
92BD9B1CE5D1410154 45FBC95E4D0EF2
682080AA227D642F2687F934904055 11
BE32971343FC9A48A02A885F194B09A1
7ECDA4D01544AF8CA58450BF66D2E88A
A2D74652 42A8DFB36974C551EB232921
D4EFD9B43A622875911410EA776CDA1D
"""
H = bytes.fromhex("".join(_H_HEX.split()))
assert len(H) == 256 and len(set(H)) == 256, "H должна быть перестановкой"


def _rotl(x: int, r: int) -> int:
    return ((x << r) | (x >> (32 - r))) & MASK


def _G(r: int, u: int) -> int:
    """G_r(u): подстановка H к каждому байту слова и циклический сдвиг влево на r бит."""
    w = (H[u & 0xFF]
         | H[(u >> 8) & 0xFF] << 8
         | H[(u >> 16) & 0xFF] << 16
         | H[(u >> 24) & 0xFF] << 24)
    return _rotl(w, r)


def _words(b: bytes):
    """Байты -> 32-битные слова (little-endian, как требует стандарт)."""
    return [int.from_bytes(b[i:i + 4], "little") for i in range(0, len(b), 4)]


def _bytes(ws):
    return b"".join(w.to_bytes(4, "little") for w in ws)


class Belt:
    def __init__(self, key: bytes):
        if len(key) != KEY_SIZE:
            raise ValueError("Ключ БелТ должен быть 32 байта")
        theta = _words(key)
        # K_i = theta_{((i-1) mod 8)+1}, i = 1..56 (K[0] не используется)
        self.K = [0] + [theta[(i - 1) % 8] for i in range(1, 57)]

    def encrypt_block(self, block: bytes) -> bytes:
        if len(block) != BLOCK_SIZE:
            raise ValueError("Блок должен быть 16 байт")
        a, b, c, d = _words(block)
        K = self.K
        for i in range(1, 9):
            b ^= _G(5, (a + K[7 * i - 6]) & MASK)
            c ^= _G(21, (d + K[7 * i - 5]) & MASK)
            a = (a - _G(13, (b + K[7 * i - 4]) & MASK)) & MASK
            e = _G(21, (b + c + K[7 * i - 3]) & MASK) ^ i
            b = (b + e) & MASK
            c = (c - e) & MASK
            d = (d + _G(13, (c + K[7 * i - 2]) & MASK)) & MASK
            b ^= _G(21, (a + K[7 * i - 1]) & MASK)
            c ^= _G(5, (d + K[7 * i]) & MASK)
            a, b = b, a
            c, d = d, c
            b, c = c, b
        return _bytes([b, d, a, c])

    def decrypt_block(self, block: bytes) -> bytes:
        if len(block) != BLOCK_SIZE:
            raise ValueError("Блок должен быть 16 байт")
        a, b, c, d = _words(block)
        K = self.K
        for i in range(8, 0, -1):
            b ^= _G(5, (a + K[7 * i]) & MASK)
            c ^= _G(21, (d + K[7 * i - 1]) & MASK)
            a = (a - _G(13, (b + K[7 * i - 2]) & MASK)) & MASK
            e = _G(21, (b + c + K[7 * i - 3]) & MASK) ^ i
            b = (b + e) & MASK
            c = (c - e) & MASK
            d = (d + _G(13, (c + K[7 * i - 4]) & MASK)) & MASK
            b ^= _G(21, (a + K[7 * i - 5]) & MASK)
            c ^= _G(5, (d + K[7 * i - 6]) & MASK)
            a, b = b, a
            c, d = d, c
            a, d = d, a
        return _bytes([c, a, d, b])
