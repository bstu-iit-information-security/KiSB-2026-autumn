"""Функция хэширования belt-hash (СТБ 34.101.31, п. 6.9).

Строится на блочном шифре БелТ из ЛР №3 (модуль belt.py) через функцию
сжатия belt-compress. Длина хэш-значения — 256 бит. Именно эта
хэш-функция используется в СТБ 34.101.45 для вычисления H(M).
"""

from belt import BeltCipher, H

_ONES = b"\xff" * 16
_H0 = bytes(H[:32])  # начальное значение h: первые 32 байта H-блока


def _xor(a: bytes, b: bytes) -> bytes:
    return (int.from_bytes(a, "little") ^ int.from_bytes(b, "little")).to_bytes(len(a), "little")


def _block(x: bytes, key: bytes) -> bytes:
    return BeltCipher(key).encrypt_block(x)


def belt_compress(X: bytes):
    """belt-compress: 512 бит -> (S: 128 бит, Y: 256 бит).

    S  = belt-block(X3 ^ X4, X1 || X2) ^ X3 ^ X4
    Y1 = belt-block(X1, S || X4) ^ X1
    Y2 = belt-block(X2, (S ^ 1^128) || X3) ^ X2
    """
    X1, X2, X3, X4 = X[0:16], X[16:32], X[32:48], X[48:64]
    x34 = _xor(X3, X4)
    S = _xor(_block(x34, X1 + X2), x34)
    Y1 = _xor(_block(X1, S + X4), X1)
    Y2 = _xor(_block(X2, _xor(S, _ONES) + X3), X2)
    return S, Y1 + Y2


def belt_hash(data: bytes) -> bytes:
    """belt-hash(X): r = <|X|>_128, s = 0, h = H0;
    для каждого 256-битного блока X_i: (t, h) = compress(X_i || h), s ^= t;
    результат = compress(r || s || h).Y"""
    r = (len(data) * 8).to_bytes(16, "little")
    s = bytes(16)
    h = _H0
    padded = data + bytes((-len(data)) % 32)
    for i in range(0, len(padded), 32):
        t, h = belt_compress(padded[i:i + 32] + h)
        s = _xor(s, t)
    return belt_compress(r + s + h)[1]
