import os

from aes import BLOCK_SIZE, encrypt_block, decrypt_block


class PaddingError(ValueError):


class IVError(ValueError):


class CiphertextError(ValueError):


def pad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    k = block_size - (len(data) % block_size)
    return bytes(data) + bytes([k]) * k


def unpad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    if len(data) == 0 or len(data) % block_size != 0:
        raise PaddingError("длина данных не кратна размеру блока")
    k = data[-1]
    if not 1 <= k <= block_size:
        raise PaddingError(f"недопустимое значение байта паддинга: {k}")
    tail = data[-block_size:]
    bad = 0
    for i in range(block_size):
        in_pad = i >= block_size - k            
        if in_pad and tail[i] != k:
            bad |= 1
    if bad:
        raise PaddingError("байты паддинга не совпадают со значением k")
    return bytes(data[:-k])


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def _blocks(data: bytes):
    for i in range(0, len(data), BLOCK_SIZE):
        yield data[i:i + BLOCK_SIZE]


def check_iv(iv) -> bytes:
    if iv is None:
        raise IVError("IV не задан")
    if not isinstance(iv, (bytes, bytearray)):
        raise IVError(f"IV должен быть bytes, получено {type(iv).__name__}")
    if len(iv) != BLOCK_SIZE:
        raise IVError(f"IV должен быть длиной {BLOCK_SIZE} байт, получено {len(iv)}")
    return bytes(iv)


def generate_iv() -> bytes:
    return os.urandom(BLOCK_SIZE)


def _check_ct_len(ct: bytes):
    if len(ct) == 0 or len(ct) % BLOCK_SIZE != 0:
        raise CiphertextError(
            f"длина шифротекста ({len(ct)}) должна быть ненулевой и кратной {BLOCK_SIZE}")


def ecb_encrypt(data: bytes, key: bytes, padding: bool = True) -> bytes:
    if padding:
        data = pad(data)
    elif len(data) % BLOCK_SIZE:
        raise ValueError("без паддинга длина данных должна быть кратна 16")
    return b"".join(encrypt_block(b, key) for b in _blocks(data))


def ecb_decrypt(ct: bytes, key: bytes, padding: bool = True) -> bytes:
    _check_ct_len(ct)
    pt = b"".join(decrypt_block(b, key) for b in _blocks(ct))
    return unpad(pt) if padding else pt


def cbc_encrypt(data: bytes, key: bytes, iv: bytes, padding: bool = True) -> bytes:
    prev = check_iv(iv)
    if padding:
        data = pad(data)
    elif len(data) % BLOCK_SIZE:
        raise ValueError("без паддинга длина данных должна быть кратна 16")
    out = []
    for p in _blocks(data):
        prev = encrypt_block(_xor(p, prev), key)
        out.append(prev)
    return b"".join(out)


def cbc_decrypt(ct: bytes, key: bytes, iv: bytes, padding: bool = True) -> bytes:
    prev = check_iv(iv)
    _check_ct_len(ct)
    out = []
    for c in _blocks(ct):
        out.append(_xor(decrypt_block(c, key), prev))
        prev = c                                   
    pt = b"".join(out)
    return unpad(pt) if padding else pt


def cbc_encrypt_packed(data: bytes, key: bytes, iv: bytes = None) -> bytes:
    iv = generate_iv() if iv is None else check_iv(iv)
    return iv + cbc_encrypt(data, key, iv)


def cbc_decrypt_packed(blob: bytes, key: bytes) -> bytes:
    if len(blob) < 2 * BLOCK_SIZE:
        raise CiphertextError("шифротекст короче IV + одного блока")
    iv, ct = blob[:BLOCK_SIZE], blob[BLOCK_SIZE:]
    return cbc_decrypt(ct, key, iv)


def cbc_verify_chain(ct: bytes, key: bytes, iv: bytes, plaintext_padded: bytes) -> bool:
    prev = check_iv(iv)
    pblocks = list(_blocks(plaintext_padded))
    cblocks = list(_blocks(ct))
    if len(pblocks) != len(cblocks):
        return False
    for p, c in zip(pblocks, cblocks):
        expected = encrypt_block(_xor(p, prev), key)
        if expected != c:
            return False
        prev = c
    return True
