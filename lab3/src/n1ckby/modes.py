from aes import BLOCK_SIZE, decrypt_block, encrypt_block


def pad(data: bytes) -> bytes:
    padding_length = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + bytes([padding_length]) * padding_length


def unpad(data: bytes) -> bytes:
    if not data or len(data) % BLOCK_SIZE != 0:
        raise ValueError("Некорректное дополнение PKCS#7.")
    padding_length = data[-1]
    if not 1 <= padding_length <= BLOCK_SIZE:
        raise ValueError("Некорректное дополнение PKCS#7.")
    expected = bytes([padding_length]) * padding_length
    if data[-padding_length:] != expected:
        raise ValueError("Некорректное дополнение PKCS#7.")
    return data[:-padding_length]


def xor_blocks(first: bytes, second: bytes) -> bytes:
    if len(first) != BLOCK_SIZE or len(second) != BLOCK_SIZE:
        raise ValueError("Для XOR нужны два блока по 16 байт.")
    return bytes(a ^ b for a, b in zip(first, second))


def validate_ciphertext(data: bytes) -> None:
    if not data or len(data) % BLOCK_SIZE != 0:
        raise ValueError("Шифротекст должен содержать целое число блоков.")


def validate_iv(iv: bytes) -> None:
    if len(iv) != BLOCK_SIZE:
        raise ValueError("IV должен содержать ровно 16 байт.")


def encrypt_ecb(data: bytes, key: bytes) -> bytes:
    padded = pad(data)
    result = bytearray()
    for offset in range(0, len(padded), BLOCK_SIZE):
        result.extend(encrypt_block(padded[offset:offset + BLOCK_SIZE], key))
    return bytes(result)


def decrypt_ecb(data: bytes, key: bytes) -> bytes:
    validate_ciphertext(data)
    result = bytearray()
    for offset in range(0, len(data), BLOCK_SIZE):
        result.extend(decrypt_block(data[offset:offset + BLOCK_SIZE], key))
    return unpad(bytes(result))


def encrypt_cbc(data: bytes, key: bytes, iv: bytes) -> bytes:
    validate_iv(iv)
    padded = pad(data)
    previous = iv
    result = bytearray()
    for offset in range(0, len(padded), BLOCK_SIZE):
        block = padded[offset:offset + BLOCK_SIZE]
        encrypted = encrypt_block(xor_blocks(block, previous), key)
        result.extend(encrypted)
        previous = encrypted
    return bytes(result)


def decrypt_cbc(data: bytes, key: bytes, iv: bytes) -> bytes:
    validate_iv(iv)
    validate_ciphertext(data)
    previous = iv
    result = bytearray()
    for offset in range(0, len(data), BLOCK_SIZE):
        block = data[offset:offset + BLOCK_SIZE]
        decrypted = xor_blocks(decrypt_block(block, key), previous)
        result.extend(decrypted)
        previous = block
    return unpad(bytes(result))
