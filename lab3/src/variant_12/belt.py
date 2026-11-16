"""Блочный шифр СТБ 34.101.31-2011 («БелТ»).

Модуль 1: базовый алгоритм. Блок 128 бит, ключ 256 бит, 8 раундов.
Модуль инкапсулирует генерацию раундовых ключей и содержит функции
зашифрования/расшифрования строго одного 128-битного блока:

    encrypt_block(pt_block, key) -> ct_block
    decrypt_block(ct_block, key) -> pt_block

Класс BeltCipher хранит уже развёрнутые раундовые ключи и таблицы
G-функций, поэтому при обработке длинных сообщений ключ не
разворачивается заново на каждом блоке.

Сторонние криптографические библиотеки не используются.
"""

BLOCK_SIZE = 16  # байт (128 бит)
KEY_SIZE = 32    # байт (256 бит)
ROUNDS = 8
MASK32 = 0xFFFFFFFF

# H-блок из СТБ 34.101.31: H[0x00] = 0xB1, H[0x01] = 0x94, ..., H[0xFF] = 0x1D.
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
assert len(H) == 256 and len(set(H)) == 256, "H-блок должен быть перестановкой"


# --------------------------------------------------------------------------
# Базовые операции над 32-битными словами
# --------------------------------------------------------------------------

def rot_hi(u: int, r: int) -> int:
    """RotHi^r: циклический сдвиг 32-битного слова влево на r бит."""
    return ((u << r) | (u >> (32 - r))) & MASK32


def g_ref(u: int, r: int) -> int:
    """G_r(u) строго по определению: H к каждому байту, затем RotHi^r."""
    v = (H[u & 0xFF]
         | H[(u >> 8) & 0xFF] << 8
         | H[(u >> 16) & 0xFF] << 16
         | H[(u >> 24) & 0xFF] << 24)
    return rot_hi(v, r)


def _make_g_tables(r: int):
    """Таблицы T0..T3 такие, что G_r(u) = T0[u0] ^ T1[u1] ^ T2[u2] ^ T3[u3].

    Сдвиг RotHi линеен относительно XOR, а байты слова не пересекаются,
    поэтому подстановку и сдвиг можно заранее «склеить» в 4 таблицы по
    256 слов — одна G-функция превращается в 4 обращения к памяти.
    """
    return tuple(
        tuple(rot_hi(H[x] << (8 * j), r) for x in range(256))
        for j in range(4)
    )


G5_T = _make_g_tables(5)
G13_T = _make_g_tables(13)
G21_T = _make_g_tables(21)


def bytes_to_words(block: bytes):
    """16 байт -> 4 слова (порядок байт little-endian, как в СТБ)."""
    return tuple(int.from_bytes(block[i:i + 4], "little") for i in range(0, len(block), 4))


def words_to_bytes(*words: int) -> bytes:
    return b"".join(w.to_bytes(4, "little") for w in words)


# --------------------------------------------------------------------------
# Генерация раундовых ключей
# --------------------------------------------------------------------------

def key_schedule(key: bytes):
    """k[i] = K_{(i-1) mod 8 + 1}, i = 1..56 (в коде индексы с нуля)."""
    if len(key) != KEY_SIZE:
        raise ValueError(f"ключ БелТ должен быть {KEY_SIZE} байт, получено {len(key)}")
    K = bytes_to_words(key)
    return tuple(K[i % 8] for i in range(7 * ROUNDS))


# --------------------------------------------------------------------------
# Эталонная реализация (прямо по формулам стандарта)
# --------------------------------------------------------------------------

def _encrypt_words_ref(a, b, c, d, k):
    G = g_ref
    for i in range(1, ROUNDS + 1):
        o = 7 * (i - 1)                       # k[7i-6] -> k[o]
        b ^= G((a + k[o]) & MASK32, 5)
        c ^= G((d + k[o + 1]) & MASK32, 21)
        a = (a - G((b + k[o + 2]) & MASK32, 13)) & MASK32
        e = G((b + c + k[o + 3]) & MASK32, 21) ^ i
        b = (b + e) & MASK32
        c = (c - e) & MASK32
        d = (d + G((c + k[o + 4]) & MASK32, 13)) & MASK32
        b ^= G((a + k[o + 5]) & MASK32, 21)
        c ^= G((d + k[o + 6]) & MASK32, 5)
        a, b = b, a                           # a <-> b
        c, d = d, c                           # c <-> d
        b, c = c, b                           # b <-> c
    return b, d, a, c                         # Y = b || d || a || c


def _decrypt_words_ref(a, b, c, d, k):
    G = g_ref
    for i in range(ROUNDS, 0, -1):
        o = 7 * (i - 1)
        b ^= G((a + k[o + 6]) & MASK32, 5)
        c ^= G((d + k[o + 5]) & MASK32, 21)
        a = (a - G((b + k[o + 4]) & MASK32, 13)) & MASK32
        e = G((b + c + k[o + 3]) & MASK32, 21) ^ i
        b = (b + e) & MASK32
        c = (c - e) & MASK32
        d = (d + G((c + k[o + 2]) & MASK32, 13)) & MASK32
        b ^= G((a + k[o + 1]) & MASK32, 21)
        c ^= G((d + k[o]) & MASK32, 5)
        a, b = b, a                           # a <-> b
        c, d = d, c                           # c <-> d
        a, d = d, a                           # a <-> d
    return c, a, d, b                         # X = c || a || d || b


def _check_block(block: bytes):
    if len(block) != BLOCK_SIZE:
        raise ValueError(f"блок должен быть {BLOCK_SIZE} байт, получено {len(block)}")


def encrypt_block(pt_block: bytes, key: bytes) -> bytes:
    """Зашифрование одного 128-битного блока (эталонная реализация)."""
    _check_block(pt_block)
    return words_to_bytes(*_encrypt_words_ref(*bytes_to_words(pt_block), key_schedule(key)))


def decrypt_block(ct_block: bytes, key: bytes) -> bytes:
    """Расшифрование одного 128-битного блока (эталонная реализация)."""
    _check_block(ct_block)
    return words_to_bytes(*_decrypt_words_ref(*bytes_to_words(ct_block), key_schedule(key)))


# --------------------------------------------------------------------------
# Оптимизированная реализация: ключ разворачивается один раз, G — по таблицам
# --------------------------------------------------------------------------

class BeltCipher:
    """БелТ с заранее развёрнутым ключом и табличными G-функциями."""

    def __init__(self, key: bytes):
        self.k = key_schedule(key)

    def encrypt_words(self, a, b, c, d):
        k = self.k
        A0, A1, A2, A3 = G5_T
        B0, B1, B2, B3 = G13_T
        C0, C1, C2, C3 = G21_T
        M = MASK32
        for i in range(1, ROUNDS + 1):
            o = 7 * i - 7
            u = (a + k[o]) & M
            b ^= A0[u & 255] ^ A1[(u >> 8) & 255] ^ A2[(u >> 16) & 255] ^ A3[u >> 24]
            u = (d + k[o + 1]) & M
            c ^= C0[u & 255] ^ C1[(u >> 8) & 255] ^ C2[(u >> 16) & 255] ^ C3[u >> 24]
            u = (b + k[o + 2]) & M
            a = (a - (B0[u & 255] ^ B1[(u >> 8) & 255] ^ B2[(u >> 16) & 255] ^ B3[u >> 24])) & M
            u = (b + c + k[o + 3]) & M
            e = C0[u & 255] ^ C1[(u >> 8) & 255] ^ C2[(u >> 16) & 255] ^ C3[u >> 24] ^ i
            b = (b + e) & M
            c = (c - e) & M
            u = (c + k[o + 4]) & M
            d = (d + (B0[u & 255] ^ B1[(u >> 8) & 255] ^ B2[(u >> 16) & 255] ^ B3[u >> 24])) & M
            u = (a + k[o + 5]) & M
            b ^= C0[u & 255] ^ C1[(u >> 8) & 255] ^ C2[(u >> 16) & 255] ^ C3[u >> 24]
            u = (d + k[o + 6]) & M
            c ^= A0[u & 255] ^ A1[(u >> 8) & 255] ^ A2[(u >> 16) & 255] ^ A3[u >> 24]
            a, b, c, d = b, d, a, c           # a<->b, c<->d, b<->c разом
        return b, d, a, c

    def decrypt_words(self, a, b, c, d):
        k = self.k
        A0, A1, A2, A3 = G5_T
        B0, B1, B2, B3 = G13_T
        C0, C1, C2, C3 = G21_T
        M = MASK32
        for i in range(ROUNDS, 0, -1):
            o = 7 * i - 7
            u = (a + k[o + 6]) & M
            b ^= A0[u & 255] ^ A1[(u >> 8) & 255] ^ A2[(u >> 16) & 255] ^ A3[u >> 24]
            u = (d + k[o + 5]) & M
            c ^= C0[u & 255] ^ C1[(u >> 8) & 255] ^ C2[(u >> 16) & 255] ^ C3[u >> 24]
            u = (b + k[o + 4]) & M
            a = (a - (B0[u & 255] ^ B1[(u >> 8) & 255] ^ B2[(u >> 16) & 255] ^ B3[u >> 24])) & M
            u = (b + c + k[o + 3]) & M
            e = C0[u & 255] ^ C1[(u >> 8) & 255] ^ C2[(u >> 16) & 255] ^ C3[u >> 24] ^ i
            b = (b + e) & M
            c = (c - e) & M
            u = (c + k[o + 2]) & M
            d = (d + (B0[u & 255] ^ B1[(u >> 8) & 255] ^ B2[(u >> 16) & 255] ^ B3[u >> 24])) & M
            u = (a + k[o + 1]) & M
            b ^= C0[u & 255] ^ C1[(u >> 8) & 255] ^ C2[(u >> 16) & 255] ^ C3[u >> 24]
            u = (d + k[o]) & M
            c ^= A0[u & 255] ^ A1[(u >> 8) & 255] ^ A2[(u >> 16) & 255] ^ A3[u >> 24]
            a, b, c, d = c, a, d, b           # a<->b, c<->d, a<->d разом
        return c, a, d, b

    def encrypt_block(self, pt_block: bytes) -> bytes:
        _check_block(pt_block)
        return words_to_bytes(*self.encrypt_words(*bytes_to_words(pt_block)))

    def decrypt_block(self, ct_block: bytes) -> bytes:
        _check_block(ct_block)
        return words_to_bytes(*self.decrypt_words(*bytes_to_words(ct_block)))
