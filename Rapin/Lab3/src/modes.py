from typing import Optional
import os

from aes import encrypt_block, decrypt_block

BLOCK_SIZE = 16  # 128 бит

# PKCS#7 Padding / Unpadding 

def pad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    k = block_size - (len(data) % block_size)
    if k == 0:
        k = block_size
    padding = bytes([k] * k)
    return data + padding


def unpad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    if not data or len(data) % block_size != 0:
        raise ValueError("Некорректная длина данных для снятия паддинга")

    k = data[-1]
    if not (1 <= k <= block_size):
        raise ValueError(f"Некорректное значение паддинга: {k}")

    if data[-k:] != bytes([k] * k):
        raise ValueError("Паддинг не прошёл проверку")

    return data[:-k]


# Режим ECB

def encrypt_ecb(plaintext: bytes, key: bytes) -> bytes:
    if len(key) != 16:
        raise ValueError("Ключ должен быть 16 байт")

    padded = pad(plaintext)
    ciphertext = bytearray()

    for i in range(0, len(padded), BLOCK_SIZE):
        block = padded[i:i + BLOCK_SIZE]
        ciphertext.extend(encrypt_block(block, key))

    return bytes(ciphertext)


def decrypt_ecb(ciphertext: bytes, key: bytes) -> bytes:
    if len(key) != 16:
        raise ValueError("Ключ должен быть 16 байт")
    if len(ciphertext) == 0 or len(ciphertext) % BLOCK_SIZE != 0:
        raise ValueError("Длина шифротекста должна быть кратна размеру блока")

    plaintext = bytearray()
    for i in range(0, len(ciphertext), BLOCK_SIZE):
        block = ciphertext[i:i + BLOCK_SIZE]
        plaintext.extend(decrypt_block(block, key))

    return unpad(bytes(plaintext))


# Режим CFB

def encrypt_cfb(plaintext: bytes, key: bytes, iv: Optional[bytes] = None) -> bytes:
    if len(key) != 16:
        raise ValueError("Ключ должен быть 16 байт")

    if iv is None:
        iv = os.urandom(BLOCK_SIZE)
    if len(iv) != BLOCK_SIZE:
        raise ValueError("IV должен быть 16 байт")

    if not plaintext:
        return iv + b""   # возвращаем IV + пустой шифротекст

    ciphertext = bytearray()
    prev = iv  # C_0 = IV

    # Обрабатываем полные блоки
    full_blocks = len(plaintext) // BLOCK_SIZE
    for i in range(full_blocks):
        p_block = plaintext[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE]
        # E_K(C_{i-1})
        keystream = encrypt_block(prev, key)
        # C_i = P_i ⊕ E_K(C_{i-1})
        c_block = bytes(a ^ b for a, b in zip(p_block, keystream))
        ciphertext.extend(c_block)
        prev = c_block  # обратная связь по шифротексту

    # Последний неполный блок
    remainder = len(plaintext) % BLOCK_SIZE
    if remainder > 0:
        p_block = plaintext[full_blocks * BLOCK_SIZE:]
        keystream = encrypt_block(prev, key)
        # XOR только нужного количества байт
        c_block = bytes(a ^ b for a, b in zip(p_block, keystream[:remainder]))
        ciphertext.extend(c_block)
        # для неполного блока prev обновлять не нужно (конец сообщения)

    # Возвращаем IV || ciphertext (IV нужен для расшифрования)
    return iv + bytes(ciphertext)


def decrypt_cfb(ciphertext_with_iv: bytes, key: bytes) -> bytes:
    if len(key) != 16:
        raise ValueError("Ключ должен быть 16 байт")
    if len(ciphertext_with_iv) < BLOCK_SIZE:
        raise ValueError("Слишком короткий шифротекст (нет места даже для IV)")

    iv = ciphertext_with_iv[:BLOCK_SIZE]
    ciphertext = ciphertext_with_iv[BLOCK_SIZE:]

    if not ciphertext:
        return b""

    plaintext = bytearray()
    prev = iv  # C_0 = IV

    full_blocks = len(ciphertext) // BLOCK_SIZE
    for i in range(full_blocks):
        c_block = ciphertext[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE]
        keystream = encrypt_block(prev, key)
        # P_i = C_i ⊕ E_K(C_{i-1})
        p_block = bytes(a ^ b for a, b in zip(c_block, keystream))
        plaintext.extend(p_block)
        prev = c_block  # обратная связь

    # Последний неполный блок
    remainder = len(ciphertext) % BLOCK_SIZE
    if remainder > 0:
        c_block = ciphertext[full_blocks * BLOCK_SIZE:]
        keystream = encrypt_block(prev, key)
        p_block = bytes(a ^ b for a, b in zip(c_block, keystream[:remainder]))
        plaintext.extend(p_block)

    return bytes(plaintext)


# Удобные обёртки с явным IV (для тестов)

def encrypt_cfb_with_iv(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    """То же, что encrypt_cfb, но IV передаётся явно (не генерируется)."""
    return encrypt_cfb(plaintext, key, iv=iv)


# Самопроверка модуля
if __name__ == "__main__":
    key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
    iv  = bytes.fromhex("000102030405060708090a0b0c0d0e0f")

    # Тест PKCS#7
    for length in [0, 1, 15, 16, 17, 31, 32, 33, 48]:
        data = bytes(range(length))
        padded = pad(data)
        assert len(padded) % 16 == 0
        assert unpad(padded) == data
    print("PKCS#7 pad/unpad OK")

    # Тест ECB
    messages = [
        b"",
        b"A",
        b"Hello, AES-ECB!",
        b"1234567890123456",                     # ровно 16 байт
        b"12345678901234567",                    # 17 байт
        b"The quick brown fox jumps over the lazy dog",
        bytes(range(64)),
    ]

    for msg in messages:
        ct = encrypt_ecb(msg, key)
        pt = decrypt_ecb(ct, key)
        assert pt == msg, f"ECB failed for len={len(msg)}"
    print("ECB encrypt/decrypt OK")

    # Тест CFB (произвольные длины)
    for msg in messages:
        ct = encrypt_cfb_with_iv(msg, key, iv)
        pt = decrypt_cfb(ct, key)
        assert pt == msg, f"CFB failed for len={len(msg)}"
    print("CFB encrypt/decrypt (arbitrary lengths) OK")


    # Сравнение: одинаковые блоки в ECB дают одинаковый шифротекст
    pattern = b"AAAAAAAA" * 4   # 32 байта одинаковых
    ct_ecb = encrypt_ecb(pattern, key)
    # первые два блока шифротекста должны совпасть
    assert ct_ecb[:16] == ct_ecb[16:32], "ECB не показал уязвимость паттернов"
    print("ECB pattern vulnerability demonstrated")

    ct_cfb = encrypt_cfb_with_iv(pattern, key, iv)
    assert ct_cfb[16:32] != ct_cfb[32:48], "CFB не должен давать одинаковые блоки"
    print("CFB hides patterns OK")

    print("\nAll modes self-tests passed.")
