"""Модуль 1. Блочный шифр AES-128 (FIPS-197). Только один 16-байтный блок."""
from functools import lru_cache


def _xtime(b: int) -> int:
    return ((b << 1) ^ 0x1B) & 0xFF if b & 0x80 else b << 1


def _mul(a: int, b: int) -> int:
    """Умножение в GF(2^8) (сдвиги + xtime)."""
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r


def _make_sbox() -> list[int]:
    """Строит таблицу S-box (мультипликативная инверсия + аффинное преобразование)."""
    rotl = lambda x, n: ((x << n) | (x >> (8 - n))) & 0xFF
    sbox = [0] * 256
    p = q = 1
    while True:
        p = p ^ _xtime(p)                      # p *= 3
        q ^= q << 1; q ^= q << 2; q ^= q << 4  # q /= 3
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        sbox[p] = q ^ rotl(q, 1) ^ rotl(q, 2) ^ rotl(q, 3) ^ rotl(q, 4) ^ 0x63
        if p == 1:
            break
    sbox[0] = 0x63
    return sbox


SBOX = _make_sbox()
INV_SBOX = [0] * 256
for _i, _v in enumerate(SBOX):
    INV_SBOX[_v] = _i


@lru_cache(maxsize=16)
def expand_key(key: bytes) -> tuple:
    """Key Expansion: 16 байт -> 11 раундовых ключей по 16 байт."""
    if len(key) != 16:
        raise ValueError("Ключ AES-128 должен быть 16 байт")
    w = [list(key[4 * i:4 * i + 4]) for i in range(4)]
    rc = 1
    for i in range(4, 44):
        t = w[i - 1][:]
        if i % 4 == 0:
            t = t[1:] + t[:1]                  # RotWord
            t = [SBOX[b] for b in t]           # SubWord
            t[0] ^= rc                         # Rcon
            rc = _xtime(rc)
        w.append([a ^ b for a, b in zip(w[i - 4], t)])
    return tuple(tuple(sum(w[4 * r:4 * r + 4], [])) for r in range(11))


# Состояние: плоский список из 16 байт, элемент [row + 4*col] (как в стандарте).
def _add_round_key(s, rk):
    return [a ^ b for a, b in zip(s, rk)]


def _shift_rows(s):
    return [s[r + 4 * ((c + r) % 4)] for c in range(4) for r in range(4)]


def _inv_shift_rows(s):
    out = [0] * 16
    for c in range(4):
        for r in range(4):
            out[r + 4 * ((c + r) % 4)] = s[r + 4 * c]
    return out


def _mix_columns(s):
    out = []
    for c in range(4):
        a = s[4 * c:4 * c + 4]
        out += [
            _xtime(a[0]) ^ (_xtime(a[1]) ^ a[1]) ^ a[2] ^ a[3],
            a[0] ^ _xtime(a[1]) ^ (_xtime(a[2]) ^ a[2]) ^ a[3],
            a[0] ^ a[1] ^ _xtime(a[2]) ^ (_xtime(a[3]) ^ a[3]),
            (_xtime(a[0]) ^ a[0]) ^ a[1] ^ a[2] ^ _xtime(a[3]),
        ]
    return out


def _inv_mix_columns(s):
    out = []
    for c in range(4):
        a = s[4 * c:4 * c + 4]
        out += [
            _mul(a[0], 14) ^ _mul(a[1], 11) ^ _mul(a[2], 13) ^ _mul(a[3], 9),
            _mul(a[0], 9) ^ _mul(a[1], 14) ^ _mul(a[2], 11) ^ _mul(a[3], 13),
            _mul(a[0], 13) ^ _mul(a[1], 9) ^ _mul(a[2], 14) ^ _mul(a[3], 11),
            _mul(a[0], 11) ^ _mul(a[1], 13) ^ _mul(a[2], 9) ^ _mul(a[3], 14),
        ]
    return out


def encrypt_block(pt_block: bytes, key: bytes) -> bytes:
    if len(pt_block) != 16:
        raise ValueError("Блок должен быть 16 байт")
    rk = expand_key(key)
    s = _add_round_key(list(pt_block), rk[0])
    for r in range(1, 10):
        s = [SBOX[b] for b in s]
        s = _shift_rows(s)
        s = _mix_columns(s)
        s = _add_round_key(s, rk[r])
    s = [SBOX[b] for b in s]
    s = _shift_rows(s)
    return bytes(_add_round_key(s, rk[10]))


def decrypt_block(ct_block: bytes, key: bytes) -> bytes:
    if len(ct_block) != 16:
        raise ValueError("Блок должен быть 16 байт")
    rk = expand_key(key)
    s = _add_round_key(list(ct_block), rk[10])
    for r in range(9, 0, -1):
        s = _inv_shift_rows(s)
        s = [INV_SBOX[b] for b in s]
        s = _add_round_key(s, rk[r])
        s = _inv_mix_columns(s)
    s = _inv_shift_rows(s)
    s = [INV_SBOX[b] for b in s]
    return bytes(_add_round_key(s, rk[0]))
