"""Модуль 2. PKCS#7 и режимы ECB / CBC поверх encrypt_block / decrypt_block."""
from aes import encrypt_block, decrypt_block

B = 16


def pad(data: bytes) -> bytes:
    k = B - len(data) % B          # 1..16, при кратности добавляется целый блок
    return data + bytes([k]) * k


def unpad(data: bytes) -> bytes:
    if not data or len(data) % B:
        raise ValueError("Некорректный паддинг")
    k = data[-1]
    if not 1 <= k <= B or data[-k:] != bytes([k]) * k:
        raise ValueError("Некорректный паддинг")
    return data[:-k]


def _blocks(data: bytes):
    return [data[i:i + B] for i in range(0, len(data), B)]


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def ecb_encrypt(data: bytes, key: bytes) -> bytes:
    return b"".join(encrypt_block(p, key) for p in _blocks(pad(data)))


def ecb_decrypt(data: bytes, key: bytes) -> bytes:
    if len(data) % B:
        raise ValueError("Длина шифротекста не кратна 16")
    return unpad(b"".join(decrypt_block(c, key) for c in _blocks(data)))


def cbc_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    if len(iv) != B:
        raise ValueError("IV должен быть 16 байт")
    prev, out = iv, []
    for p in _blocks(pad(data)):
        prev = encrypt_block(_xor(p, prev), key)   # C_i = E(P_i xor C_{i-1})
        out.append(prev)
    return b"".join(out)


def cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    if len(iv) != B or len(data) % B:
        raise ValueError("Некорректные IV или длина шифротекста")
    prev, out = iv, []
    for c in _blocks(data):
        out.append(_xor(decrypt_block(c, key), prev))  # P_i = D(C_i) xor C_{i-1}
        prev = c
    return unpad(b"".join(out))
