# -*- coding: utf-8 -*-
"""
Модуль 2. Режимы шифрования ECB и CFB, дополнение PKCS#7.
Использует только атомарные функции encrypt_block / decrypt_block модуля aes128
и работает с сообщениями произвольной длины.

    ECB:  C_i = E_K(P_i),                P_i = D_K(C_i)
    CFB:  C_i = P_i XOR E_K(C_{i-1}),    P_i = C_i XOR E_K(C_{i-1}),   C_0 = IV
"""
import aes128
from aes128 import BLOCK_SIZE


class PaddingError(ValueError):
    """Некорректное дополнение при расшифровании."""


def xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def split_blocks(data, size=BLOCK_SIZE):
    return [data[i:i + size] for i in range(0, len(data), size)]


# ----------------------------------------------------------------------
#                     ДОПОЛНЕНИЕ PKCS#7
# ----------------------------------------------------------------------
def pkcs7_pad(data, block_size=BLOCK_SIZE):
    """k = B - (L mod B), 1 <= k <= B;  M_pad = M || k || k || ... || k (k раз).
    Если L mod B = 0, добавляется полный блок из B байт 0x10."""
    k = block_size - len(data) % block_size
    return bytes(data) + bytes([k]) * k


def pkcs7_unpad(data, block_size=BLOCK_SIZE):
    """Проверка и снятие дополнения: k = M_pad[|M_pad| - 1], 1 <= k <= B,
    последние k байтов равны k; сообщение усекается на k байт."""
    if not data or len(data) % block_size:
        raise PaddingError("длина данных не кратна размеру блока")
    k = data[-1]
    if not 1 <= k <= block_size:
        raise PaddingError(f"недопустимое значение k = {k}")
    if data[-k:] != bytes([k]) * k:
        raise PaddingError(f"последние {k} байт не равны 0x{k:02x}")
    return bytes(data[:-k])


# ----------------------------------------------------------------------
#                     РЕЖИМ ECB (Electronic Codebook)
# ----------------------------------------------------------------------
def ecb_encrypt(data, key, padding=True):
    """Каждый блок зашифровывается независимо: C_i = E_K(P_i)."""
    if padding:
        data = pkcs7_pad(data)
    elif len(data) % BLOCK_SIZE:
        raise ValueError("без дополнения длина должна быть кратна 16 байтам")
    return b"".join(aes128.encrypt_block(p, key) for p in split_blocks(data))


def ecb_decrypt(data, key, padding=True):
    """P_i = D_K(C_i), затем снятие дополнения PKCS#7."""
    if len(data) % BLOCK_SIZE:
        raise ValueError("длина шифротекста ECB должна быть кратна 16 байтам")
    pt = b"".join(aes128.decrypt_block(c, key) for c in split_blocks(data))
    return pkcs7_unpad(pt) if padding else pt


# ----------------------------------------------------------------------
#                     РЕЖИМ CFB (Cipher Feedback)
# ----------------------------------------------------------------------
def _check_iv(iv):
    if len(iv) != BLOCK_SIZE:
        raise ValueError(f"IV должен быть {BLOCK_SIZE} байт, получено {len(iv)}")


def _cfb(data, key, iv, segment, decrypt):
    """Общая часть CFB. Регистр обратной связи R_0 = IV, гамма = E_K(R_{i-1}),
    R_i = (R_{i-1} без первых s байт) || C_i. При s = 16 (CFB-128) R_i = C_i.
    В обоих направлениях вызывается ТОЛЬКО encrypt_block (E_K)."""
    _check_iv(iv)
    if not 1 <= segment <= BLOCK_SIZE:
        raise ValueError("размер сегмента должен быть от 1 до 16 байт")
    reg = bytes(iv)
    out = bytearray()
    for i in range(0, len(data), segment):
        chunk = data[i:i + segment]
        gamma = aes128.encrypt_block(reg, key)[:len(chunk)]
        res = xor_bytes(chunk, gamma)        # последний неполный сегмент:
        out += res                           # берётся начало гаммы
        ct = chunk if decrypt else res
        if len(chunk) == segment:
            reg = reg[segment:] + ct
    return bytes(out)


def cfb_encrypt(data, key, iv, segment=BLOCK_SIZE):
    """C_i = P_i XOR E_K(C_{i-1}), C_0 = IV. Дополнение не требуется:
    длина шифротекста равна длине открытого текста."""
    return _cfb(data, key, iv, segment, decrypt=False)


def cfb_decrypt(data, key, iv, segment=BLOCK_SIZE):
    """P_i = C_i XOR E_K(C_{i-1}), C_0 = IV (функция D_K не используется)."""
    return _cfb(data, key, iv, segment, decrypt=True)


# ----------------------------------------------------------------------
def encrypt(mode, data, key, iv=None, segment=BLOCK_SIZE):
    if mode == "ECB":
        return ecb_encrypt(data, key)
    if mode == "CFB":
        return cfb_encrypt(data, key, iv, segment)
    raise ValueError(f"неизвестный режим {mode}")


def decrypt(mode, data, key, iv=None, segment=BLOCK_SIZE):
    if mode == "ECB":
        return ecb_decrypt(data, key)
    if mode == "CFB":
        return cfb_decrypt(data, key, iv, segment)
    raise ValueError(f"неизвестный режим {mode}")
