"""Режимы работы и дополнение (padding). Не содержит логики самого шифра БелТ."""
import os
from belt import Belt, BLOCK_SIZE


# ---------- паддинг PKCS#7 ----------
def pad(data: bytes, bs: int = BLOCK_SIZE) -> bytes:
    n = bs - len(data) % bs          # 1..bs, всегда добавляется хотя бы 1 байт
    return data + bytes([n]) * n


def unpad(data: bytes, bs: int = BLOCK_SIZE) -> bytes:
    if not data or len(data) % bs:
        raise ValueError("Некорректная длина данных")
    n = data[-1]
    if not 1 <= n <= bs or data[-n:] != bytes([n]) * n:
        raise ValueError("Некорректный паддинг")
    return data[:-n]


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


# ---------- ECB ----------
def ecb_encrypt(cipher: Belt, data: bytes, use_padding: bool = True) -> bytes:
    if use_padding:
        data = pad(data)
    if len(data) % BLOCK_SIZE:
        raise ValueError("Без паддинга длина должна быть кратна 16")
    return b"".join(cipher.encrypt_block(data[i:i + BLOCK_SIZE])
                    for i in range(0, len(data), BLOCK_SIZE))


def ecb_decrypt(cipher: Belt, data: bytes, use_padding: bool = True) -> bytes:
    if len(data) % BLOCK_SIZE:
        raise ValueError("Длина шифртекста должна быть кратна 16")
    out = b"".join(cipher.decrypt_block(data[i:i + BLOCK_SIZE])
                   for i in range(0, len(data), BLOCK_SIZE))
    return unpad(out) if use_padding else out


# ---------- CTR (belt-ctr, СТБ 34.101.31, п. 6.3) ----------
def _inc_counter(s: bytes) -> bytes:
    """s <- (s + 1) mod 2^128. Блок трактуется как число в порядке байт
    little-endian (младший байт первым) - так же, как 32-битные слова БелТ."""
    v = (int.from_bytes(s, "little") + 1) % (1 << 128)
    return v.to_bytes(BLOCK_SIZE, "little")


def ctr_crypt(cipher: Belt, data: bytes, synchro: bytes) -> bytes:
    """Зашифрование и расшифрование совпадают. Паддинг не нужен: последний
    неполный блок гаммы просто усекается."""
    if len(synchro) != BLOCK_SIZE:
        raise ValueError("Синхропосылка - 16 байт")
    s = cipher.encrypt_block(synchro)             # s = E_K(S)
    out = bytearray()
    for i in range(0, len(data), BLOCK_SIZE):
        s = _inc_counter(s)                       # s = s + 1
        out += _xor(data[i:i + BLOCK_SIZE], cipher.encrypt_block(s))
    return bytes(out)


def new_synchro() -> bytes:
    return os.urandom(BLOCK_SIZE)
