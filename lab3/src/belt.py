import struct
from functools import lru_cache

M32 = 0xFFFFFFFF

H = bytes.fromhex(
    "B194BAC80A08F53B366D008E584A5DE4"
    "8504FA9D1BB6C7AC252E72C202FDCE0D"
    "5BE3D61217B96181FE6786AD716B890B"
    "5CB0C0FF33C356B835C405AED8E07F99"
    "E12BDC1AE28257EC703FCCF095EE8DF1"
    "C1AB76389FE678CAF7C6F860D5BB9C4F"
    "F33C657B637C306ADD4EA7799EB23D31"
    "3E98B56E27D3BCCF591E181F4C5AB793"
    "E9DEE72C8F0C0FA62DDB49F46F739647"
    "06075316ED247A3739CBA38303A98BF6"
    "92BD9B1CE5D141015445FBC95E4D0EF2"
    "682080AA227D642F2687F93490405511"
    "BE32971343FC9A48A02A885F194B09A1"
    "7ECDA4D01544AF8CA58450BF66D2E88A"
    "A2D7465242A8DFB36974C551EB232921"
    "D4EFD9B43A622875911410EA776CDA1D"
)


def _G(u, r):
    t = (H[u & 255] | H[(u >> 8) & 255] << 8 | H[(u >> 16) & 255] << 16 | H[(u >> 24) & 255] << 24)

    return ((t << r) | (t >> (32 - r))) & M32


@lru_cache(maxsize=16)
def _expand(key):
    if len(key) != 32:
        raise ValueError("ключ БелТ должен быть 32 байта")

    w = struct.unpack("<8I", key)

    return tuple(w[i % 8] for i in range(56))


def encrypt_block(pt_block, key):
    if len(pt_block) != 16:
        raise ValueError("блок должен быть 16 байт")

    ks = _expand(bytes(key))
    a, b, c, d = struct.unpack("<4I", pt_block)

    for i in range(1, 9):
        k1, k2, k3, k4, k5, k6, k7 = ks[7 * i - 7:7 * i]

        b ^= _G((a + k1) & M32, 5)                  # 1
        c ^= _G((d + k2) & M32, 21)                 # 2
        a = (a - _G((b + k3) & M32, 13)) & M32      # 3
        e = _G((b + c + k4) & M32, 21) ^ i          # 4
        b = (b + e) & M32                           # 5
        c = (c - e) & M32                           # 6
        d = (d + _G((c + k5) & M32, 13)) & M32      # 7
        b ^= _G((a + k6) & M32, 21)                 # 8
        c ^= _G((d + k7) & M32, 5)                  # 9

        a, b = b, a                                 #  a ↔ b
        c, d = d, c                                 #  c ↔ d
        b, c = c, b                                 #  b ↔ c

    return struct.pack("<4I", b, d, a, c)


def decrypt_block(ct_block, key):
    if len(ct_block) != 16:
        raise ValueError("блок должен быть 16 байт")

    ks = _expand(bytes(key))
    a, b, c, d = struct.unpack("<4I", ct_block)

    for i in range(1, 9):
        j = 9 - i
        k1, k2, k3, k4, k5, k6, k7 = ks[7 * j - 7:7 * j]

        b ^= _G((a + k7) & M32, 5)
        c ^= _G((d + k6) & M32, 21)
        a = (a - _G((b + k5) & M32, 13)) & M32
        e = _G((b + c + k4) & M32, 21) ^ j
        b = (b + e) & M32
        c = (c - e) & M32
        d = (d + _G((c + k3) & M32, 13)) & M32
        b ^= _G((a + k2) & M32, 21)
        c ^= _G((d + k1) & M32, 5)

        a, b = b, a
        c, d = d, c
        a, d = d, a

    return struct.pack("<4I", c, a, d, b)
