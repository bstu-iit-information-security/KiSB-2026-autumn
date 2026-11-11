"""
Модуль cipher_modes.py
Реализация паддинга PKCS#7 и режимов шифрования ECB и CBC
на базе функций encrypt_block / decrypt_block.
"""

from aes128 import encrypt_block, decrypt_block

BLOCK_SIZE = 16


def pkcs7_pad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    """Дополнение сообщения до кратности block_size по стандарту PKCS#7."""
    remainder = len(data) % block_size
    pad_len = block_size - remainder  # от 1 до block_size байт
    padding = bytes([pad_len] * pad_len)
    return data + padding


def pkcs7_unpad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    """Безопасная валидация и удаление паддинга PKCS#7."""
    if not data or len(data) % block_size != 0:
        raise ValueError("Некорректный размер блока данных для удаления паддинга.")

    pad_len = data[-1]
    if pad_len < 1 or pad_len > block_size:
        raise ValueError(f"Недопустимое значение байта паддинга: {pad_len}")

    expected_pad = bytes([pad_len] * pad_len)
    if data[-pad_len:] != expected_pad:
        raise ValueError("Нарушена структура паддинга PKCS#7 (Padding Error).")

    return data[:-pad_len]


def xor_bytes(a: bytes, b: bytes) -> bytes:
    """Побитовый XOR двух байтовых строк одинаковой длины."""
    return bytes(x ^ y for x, y in zip(a, b))


# --- Режим ECB ---

def encrypt_ecb(plaintext: bytes, key: bytes) -> bytes:
    """Зашифрование произвольного сообщения в режиме ECB с паддингом."""
    padded = pkcs7_pad(plaintext, BLOCK_SIZE)
    ciphertext = bytearray()
    for i in range(0, len(padded), BLOCK_SIZE):
        block = padded[i : i + BLOCK_SIZE]
        ciphertext.extend(encrypt_block(block, key))
    return bytes(ciphertext)


def decrypt_ecb(ciphertext: bytes, key: bytes) -> bytes:
    """Расшифрование сообщения в режиме ECB со снятием паддинга."""
    if len(ciphertext) % BLOCK_SIZE != 0:
        raise ValueError("Длина шифротекста в ECB должна быть кратна размеру блока.")

    padded_plaintext = bytearray()
    for i in range(0, len(ciphertext), BLOCK_SIZE):
        block = ciphertext[i : i + BLOCK_SIZE]
        padded_plaintext.extend(decrypt_block(block, key))
    return pkcs7_unpad(bytes(padded_plaintext), BLOCK_SIZE)


# --- Режим CBC ---

def encrypt_cbc(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    """Зашифрование в режиме CBC: Ci = E_k(Pi ^ Ci-1), C0 = IV."""
    if len(iv) != BLOCK_SIZE:
        raise ValueError("Размер IV должен быть строго равен размеру блока (16 байт).")

    padded = pkcs7_pad(plaintext, BLOCK_SIZE)
    ciphertext = bytearray()
    prev_block = iv

    for i in range(0, len(padded), BLOCK_SIZE):
        block = padded[i : i + BLOCK_SIZE]
        block_xored = xor_bytes(block, prev_block)
        encrypted_block = encrypt_block(block_xored, key)
        ciphertext.extend(encrypted_block)
        prev_block = encrypted_block

    return bytes(ciphertext)


def decrypt_cbc(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """Расшифрование в режиме CBC: Pi = D_k(Ci) ^ Ci-1, C0 = IV."""
    if len(ciphertext) % BLOCK_SIZE != 0:
        raise ValueError("Длина шифротекста в CBC должна быть кратна размеру блока.")
    if len(iv) != BLOCK_SIZE:
        raise ValueError("Размер IV должен быть строго равен размеру блока (16 байт).")

    padded_plaintext = bytearray()
    prev_block = iv

    for i in range(0, len(ciphertext), BLOCK_SIZE):
        block = ciphertext[i : i + BLOCK_SIZE]
        decrypted_block = decrypt_block(block, key)
        plaintext_block = xor_bytes(decrypted_block, prev_block)
        padded_plaintext.extend(plaintext_block)
        prev_block = block  # Сохраняем исходный блок шифротекста для следующего шага

    return pkcs7_unpad(bytes(padded_plaintext), BLOCK_SIZE)