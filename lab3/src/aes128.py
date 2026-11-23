# -*- coding: utf-8 -*-
"""
Модуль 1. Блочный шифр AES-128 (FIPS-197).
Блок 128 бит (матрица 4 x 4 байта), ключ 128 бит, 10 раундов.
Реализация без сторонних криптографических библиотек.

Внешний интерфейс модуля (строго один 128-битный блок):
    encrypt_block(pt_block, key) -> ct_block
    decrypt_block(ct_block, key) -> pt_block
Генерация раундовых ключей инкапсулирована внутри модуля (расширенный
ключ кэшируется, чтобы не вычислять его заново для каждого блока).

Состояние хранится как список из 16 байт по столбцам: s[r + 4c] = state[r][c].
"""
from functools import lru_cache

BLOCK_SIZE = 16          # байт (128 бит)
KEY_SIZE = 16            # байт (128 бит)
ROUNDS = 10

# S-box: одномерная таблица подстановки (lookup table) из 256 байт
SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76" "ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d83115" "04c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f84" "53d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa8" "51a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d1973" "60814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479" "e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a" "703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df" "8ca1890dbfe6426841992d0fb054bb16")

# Обратная таблица подстановки: INV_SBOX[SBOX[x]] = x
_inv = bytearray(256)
for _x, _y in enumerate(SBOX):
    _inv[_y] = _x
INV_SBOX = bytes(_inv)


def xtime(b):
    """Умножение байта на x (т.е. на 2) в GF(2^8) по модулю x^8 + x^4 + x^3 + x + 1:
    (b << 1) mod 256, если b7 = 0;  ((b << 1) XOR 0x1B) mod 256, если b7 = 1."""
    b <<= 1
    return (b ^ 0x1B) & 0xFF if b & 0x100 else b


def mul2(b):
    return xtime(b)


def mul3(b):
    """b x 3 = xtime(b) XOR b."""
    return xtime(b) ^ b


def gmul(a, b):
    """Произвольное умножение в GF(2^8) (нужно для InvMixColumns: 9, 11, 13, 14)."""
    res = 0
    while b:
        if b & 1:
            res ^= a
        a = xtime(a)
        b >>= 1
    return res


# Константы раундов: rc_1 = 0x01, rc_j = xtime(rc_{j-1})
RCON = [0x01]
while len(RCON) < ROUNDS:
    RCON.append(xtime(RCON[-1]))


# ----------------------------------------------------------------------
#                     РАСШИРЕНИЕ КЛЮЧА (KEY EXPANSION)
# ----------------------------------------------------------------------
def rot_word(w):
    """Циклический сдвиг 32-битного слова на один байт влево."""
    return w[1:] + w[:1]


def sub_word(w):
    """Подстановка каждого байта слова через S-box."""
    return [SBOX[b] for b in w]


def key_expansion(key):
    """Генерация 44 слов W0..W43:
    W_i = W_{i-4} XOR SubWord(RotWord(W_{i-1})) XOR Rcon[i/4], если i mod 4 = 0,
    W_i = W_{i-4} XOR W_{i-1}                                   иначе."""
    key = bytes(key)
    if len(key) != KEY_SIZE:
        raise ValueError(f"ключ AES-128 должен быть {KEY_SIZE} байт, получено {len(key)}")
    w = [list(key[4 * i:4 * i + 4]) for i in range(4)]
    for i in range(4, 4 * (ROUNDS + 1)):
        t = w[i - 1]
        if i % 4 == 0:
            t = sub_word(rot_word(t))
            t[0] ^= RCON[i // 4 - 1]
        w.append([a ^ b for a, b in zip(w[i - 4], t)])
    return w


@lru_cache(maxsize=64)
def _round_keys_cached(key):
    w = key_expansion(key)
    return tuple(bytes(w[4 * r] + w[4 * r + 1] + w[4 * r + 2] + w[4 * r + 3])
                 for r in range(ROUNDS + 1))


def round_keys(key):
    """11 раундовых ключей K(0)..K(10) по 16 байт."""
    return _round_keys_cached(bytes(key))


# ----------------------------------------------------------------------
#                     РАУНДОВЫЕ ПРЕОБРАЗОВАНИЯ
# ----------------------------------------------------------------------
def add_round_key(s, k):
    return [a ^ b for a, b in zip(s, k)]


def sub_bytes(s):
    return [SBOX[b] for b in s]


def inv_sub_bytes(s):
    return [INV_SBOX[b] for b in s]


def shift_rows(s):
    """Строка r циклически сдвигается влево на r байт (0, 1, 2, 3)."""
    return [s[r + 4 * ((c + r) % 4)] for c in range(4) for r in range(4)]


def inv_shift_rows(s):
    return [s[r + 4 * ((c - r) % 4)] for c in range(4) for r in range(4)]


def mix_columns(s):
    """Каждый столбец умножается на матрицу [[2 3 1 1] [1 2 3 1] [1 1 2 3] [3 1 1 2]]."""
    out = []
    for c in range(4):
        a0, a1, a2, a3 = s[4 * c:4 * c + 4]
        out += [mul2(a0) ^ mul3(a1) ^ a2 ^ a3,
                a0 ^ mul2(a1) ^ mul3(a2) ^ a3,
                a0 ^ a1 ^ mul2(a2) ^ mul3(a3),
                mul3(a0) ^ a1 ^ a2 ^ mul2(a3)]
    return out


def inv_mix_columns(s):
    """Обратная матрица [[14 11 13 9] [9 14 11 13] [13 9 14 11] [11 13 9 14]]."""
    out = []
    for c in range(4):
        a0, a1, a2, a3 = s[4 * c:4 * c + 4]
        out += [gmul(a0, 14) ^ gmul(a1, 11) ^ gmul(a2, 13) ^ gmul(a3, 9),
                gmul(a0, 9) ^ gmul(a1, 14) ^ gmul(a2, 11) ^ gmul(a3, 13),
                gmul(a0, 13) ^ gmul(a1, 9) ^ gmul(a2, 14) ^ gmul(a3, 11),
                gmul(a0, 11) ^ gmul(a1, 13) ^ gmul(a2, 9) ^ gmul(a3, 14)]
    return out


def _check_block(block):
    if len(block) != BLOCK_SIZE:
        raise ValueError(f"блок должен быть ровно {BLOCK_SIZE} байт, получено {len(block)}")


# ----------------------------------------------------------------------
#                     ЗАШИФРОВАНИЕ / РАСШИФРОВАНИЕ БЛОКА
# ----------------------------------------------------------------------
def encrypt_block(pt_block, key, trace=None):
    """E_K: зашифрование одного 128-битного блока.
    trace — необязательный список, в который записываются состояния
    после каждого раунда (для демонстрации)."""
    _check_block(pt_block)
    rk = round_keys(key)
    s = add_round_key(list(pt_block), rk[0])                 # раунд 0
    if trace is not None:
        trace.append((0, bytes(s)))
    for r in range(1, ROUNDS):                               # раунды 1..9
        s = add_round_key(mix_columns(shift_rows(sub_bytes(s))), rk[r])
        if trace is not None:
            trace.append((r, bytes(s)))
    s = add_round_key(shift_rows(sub_bytes(s)), rk[ROUNDS])  # раунд 10
    if trace is not None:
        trace.append((ROUNDS, bytes(s)))
    return bytes(s)


def decrypt_block(ct_block, key):
    """D_K: расшифрование одного 128-битного блока (обратные преобразования
    в обратном порядке с раундовыми ключами K(10)..K(0))."""
    _check_block(ct_block)
    rk = round_keys(key)
    s = add_round_key(list(ct_block), rk[ROUNDS])
    for r in range(ROUNDS - 1, 0, -1):
        s = inv_mix_columns(add_round_key(inv_sub_bytes(inv_shift_rows(s)), rk[r]))
    s = add_round_key(inv_sub_bytes(inv_shift_rows(s)), rk[0])
    return bytes(s)
