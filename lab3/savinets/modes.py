"""AES-128 ECB/PKCS#7 and CFB-128 (SP 800-38A).

These modes do not provide authentication; ECB also reveals repeated blocks.
"""

import aes128

BLOCK_SIZE = 16


def _validate_block(value, name):
    if not isinstance(value, bytes):
        raise TypeError("{} must be bytes".format(name))
    if len(value) != BLOCK_SIZE:
        raise ValueError("{} must be exactly 16 bytes".format(name))


def pkcs7_pad(data):
    """Pad bytes to a multiple of the AES block size, including empty input."""
    padding_length = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return bytes(data) + bytes([padding_length]) * padding_length


def pkcs7_unpad(data):
    """Remove PKCS#7 padding, rejecting malformed or incomplete blocks."""
    if not data or len(data) % BLOCK_SIZE:
        raise ValueError("padded data must contain complete blocks")
    padding_length = data[-1]
    if (padding_length < 1 or padding_length > BLOCK_SIZE
            or data[-padding_length:] != bytes([padding_length]) * padding_length):
        raise ValueError("invalid PKCS#7 padding")
    return bytes(data[:-padding_length])


def encrypt_ecb(data, key):
    """Encrypt data using AES-128 ECB with PKCS#7 padding."""
    _validate_block(key, "key")
    padded = pkcs7_pad(data)
    return b"".join(aes128.encrypt_block(padded[i:i + BLOCK_SIZE], key)
                    for i in range(0, len(padded), BLOCK_SIZE))


def decrypt_ecb(data, key):
    """Decrypt AES-128 ECB and validate/remove its PKCS#7 padding."""
    _validate_block(key, "key")
    if not data or len(data) % BLOCK_SIZE:
        raise ValueError("ECB ciphertext must contain complete blocks")
    padded = b"".join(aes128.decrypt_block(data[i:i + BLOCK_SIZE], key)
                      for i in range(0, len(data), BLOCK_SIZE))
    return pkcs7_unpad(padded)


def _crypt_cfb(data, key, iv, decrypt):
    _validate_block(key, "key")
    _validate_block(iv, "iv")
    feedback = iv
    result = bytearray()
    for i in range(0, len(data), BLOCK_SIZE):
        chunk = data[i:i + BLOCK_SIZE]
        keystream = aes128.encrypt_block(feedback, key)
        output = bytes(a ^ b for a, b in zip(chunk, keystream))
        result.extend(output)
        # On decryption the input is ciphertext; on encryption it is output.
        feedback = chunk if decrypt else output
    return bytes(result)


def encrypt_cfb(data, key, iv):
    """Encrypt arbitrary-length data using full-block CFB without padding."""
    return _crypt_cfb(data, key, iv, decrypt=False)


def decrypt_cfb(data, key, iv):
    """Decrypt CFB-128 using only the AES block encryption primitive."""
    return _crypt_cfb(data, key, iv, decrypt=True)
