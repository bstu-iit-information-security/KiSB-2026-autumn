import os

from aes128 import BLOCK_SIZE, decrypt_block, encrypt_block

ERROR_TEXT = "ошибка расшифрования"


class DecryptionError(Exception):
    def __init__(self):
        super().__init__(ERROR_TEXT)


def xor_bytes(left, right):
    return bytes(a ^ b for a, b in zip(left, right))


def split_blocks(data):
    return [data[i:i + BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]


def pad(data):
    count = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return bytes(data) + bytes([count]) * count


def unpad(data):
    length = len(data)
    if length == 0 or length % BLOCK_SIZE:
        raise DecryptionError()
    count = data[-1]
    invalid = (((count - 1) | (BLOCK_SIZE - count)) >> 8) & 1
    for index in range(BLOCK_SIZE):
        covered = ((index - count) >> 8) & 1
        difference = data[-1 - index] ^ count
        invalid |= covered & (((difference | -difference) >> 8) & 1)
    if invalid:
        raise DecryptionError()
    return bytes(data[:length - count])


def check_iv(iv):
    if len(iv) != BLOCK_SIZE:
        raise ValueError("Вектор инициализации должен содержать 16 байт")


def ecb_encrypt(plaintext, key):
    return b"".join(encrypt_block(block, key) for block in split_blocks(pad(plaintext)))


def ecb_decrypt(ciphertext, key):
    if len(ciphertext) == 0 or len(ciphertext) % BLOCK_SIZE:
        raise DecryptionError()
    return unpad(b"".join(decrypt_block(block, key) for block in split_blocks(ciphertext)))


def cbc_encrypt(plaintext, key, iv):
    check_iv(iv)
    previous = bytes(iv)
    result = []
    for block in split_blocks(pad(plaintext)):
        previous = encrypt_block(xor_bytes(block, previous), key)
        result.append(previous)
    return b"".join(result)


def cbc_decrypt(ciphertext, key, iv):
    check_iv(iv)
    if len(ciphertext) == 0 or len(ciphertext) % BLOCK_SIZE:
        raise DecryptionError()
    previous = bytes(iv)
    result = []
    for block in split_blocks(ciphertext):
        result.append(xor_bytes(decrypt_block(block, key), previous))
        previous = block
    return unpad(b"".join(result))


def double_block(block):
    value = int.from_bytes(block, "big")
    shifted = (value << 1) & ((1 << 128) - 1)
    if value >> 127:
        shifted ^= 0x87
    return shifted.to_bytes(BLOCK_SIZE, "big")


def cmac(key, message):
    first = double_block(encrypt_block(bytes(BLOCK_SIZE), key))
    second = double_block(first)
    blocks = split_blocks(message) or [b""]
    last = blocks[-1]
    if len(last) == BLOCK_SIZE:
        last = xor_bytes(last, first)
    else:
        last = xor_bytes(last + b"\x80" + bytes(BLOCK_SIZE - 1 - len(last)), second)
    state = bytes(BLOCK_SIZE)
    for block in blocks[:-1]:
        state = encrypt_block(xor_bytes(state, block), key)
    return encrypt_block(xor_bytes(state, last), key)


def equal_constant_time(left, right):
    if len(left) != len(right):
        return False
    difference = 0
    for a, b in zip(left, right):
        difference |= a ^ b
    return difference == 0


def cbc_seal(plaintext, enc_key, mac_key, iv=None):
    iv = os.urandom(BLOCK_SIZE) if iv is None else bytes(iv)
    body = iv + cbc_encrypt(plaintext, enc_key, iv)
    return body + cmac(mac_key, body)


def cbc_open(message, enc_key, mac_key):
    if len(message) < 3 * BLOCK_SIZE or len(message) % BLOCK_SIZE:
        raise DecryptionError()
    body, tag = message[:-BLOCK_SIZE], message[-BLOCK_SIZE:]
    if not equal_constant_time(cmac(mac_key, body), tag):
        raise DecryptionError()
    return cbc_decrypt(body[BLOCK_SIZE:], enc_key, body[:BLOCK_SIZE])
