from aes128 import BLOCK_SIZE, encrypt_block, decrypt_block


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def pkcs7_pad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)


def pkcs7_unpad(padded_data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    if not padded_data or len(padded_data) % block_size != 0:
        raise ValueError("Некорректная длина данных для снятия PKCS#7 паддинга.")

    pad_len = padded_data[-1]
    if pad_len < 1 or pad_len > block_size:
        raise ValueError("Некорректное значение байта паддинга PKCS#7.")

    if padded_data[-pad_len:] != bytes([pad_len] * pad_len):
        raise ValueError("Нарушена целостность байтов паддинга PKCS#7.")

    return padded_data[:-pad_len]

def encrypt_ecb(plaintext: bytes, key: bytes) -> bytes:
    padded = pkcs7_pad(plaintext, BLOCK_SIZE)
    ciphertext = bytearray()

    for i in range(0, len(padded), BLOCK_SIZE):
        block = padded[i : i + BLOCK_SIZE]
        ciphertext.extend(encrypt_block(block, key))

    return bytes(ciphertext)


def decrypt_ecb(ciphertext: bytes, key: bytes) -> bytes:
    if not ciphertext or len(ciphertext) % BLOCK_SIZE != 0:
        raise ValueError(f"Длина шифротекста должна быть кратна {BLOCK_SIZE} байтам.")

    padded_plaintext = bytearray()
    for i in range(0, len(ciphertext), BLOCK_SIZE):
        block = ciphertext[i : i + BLOCK_SIZE]
        padded_plaintext.extend(decrypt_block(block, key))

    return pkcs7_unpad(bytes(padded_plaintext), BLOCK_SIZE)

def encrypt_cbc(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    if len(iv) != BLOCK_SIZE:
        raise ValueError(f"Вектор инициализации (IV) должен быть длиной {BLOCK_SIZE} байт.")

    padded = pkcs7_pad(plaintext, BLOCK_SIZE)
    ciphertext = bytearray()
    prev_block = iv

    for i in range(0, len(padded), BLOCK_SIZE):
        pt_block = padded[i : i + BLOCK_SIZE]
        xored = _xor_bytes(pt_block, prev_block)
        ct_block = encrypt_block(xored, key)
        ciphertext.extend(ct_block)
        prev_block = ct_block

    return bytes(ciphertext)


def decrypt_cbc(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    if len(iv) != BLOCK_SIZE:
        raise ValueError(f"Вектор инициализации (IV) должен быть длиной {BLOCK_SIZE} байт.")
    if not ciphertext or len(ciphertext) % BLOCK_SIZE != 0:
        raise ValueError(f"Длина шифротекста должна быть кратна {BLOCK_SIZE} байтам.")

    padded_plaintext = bytearray()
    prev_block = iv

    for i in range(0, len(ciphertext), BLOCK_SIZE):
        ct_block = ciphertext[i : i + BLOCK_SIZE]
        decrypted = decrypt_block(ct_block, key)
        pt_block = _xor_bytes(decrypted, prev_block)
        padded_plaintext.extend(pt_block)
        prev_block = ct_block

    return pkcs7_unpad(bytes(padded_plaintext), BLOCK_SIZE)