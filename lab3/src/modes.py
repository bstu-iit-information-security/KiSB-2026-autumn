# Логика режимов поверх атомарных функций блочного шифра.
from aes_block import encrypt_block, decrypt_block

BLOCK = 16


# ---------- PKCS#7 ----------
def pkcs7_pad(data: bytes, block: int = BLOCK) -> bytes:
    k = block - (len(data) % block)
    return data + bytes([k]) * k


def pkcs7_unpad(data: bytes, block: int = BLOCK) -> bytes:
    if not data or len(data) % block != 0:
        raise ValueError("Некорректная длина дополненного сообщения")
    k = data[-1]
    if not (1 <= k <= block):
        raise ValueError("Некорректное значение паддинга")
    if data[-k:] != bytes([k]) * k:
        raise ValueError("Проверка паддинга не пройдена (Padding Oracle guard)")
    return data[:-k]


# ---------- ECB ----------
def ecb_encrypt(pt: bytes, key: bytes) -> bytes:
    pt = pkcs7_pad(pt)
    return b"".join(encrypt_block(pt[i:i + BLOCK], key)
                    for i in range(0, len(pt), BLOCK))


def ecb_decrypt(ct: bytes, key: bytes) -> bytes:
    if len(ct) % BLOCK != 0:
        raise ValueError("Длина шифротекста не кратна блоку")
    pt = b"".join(decrypt_block(ct[i:i + BLOCK], key)
                  for i in range(0, len(ct), BLOCK))
    return pkcs7_unpad(pt)


# ---------- CFB (полноблочный CFB-128) ----------
# Dемонстрация того, что и для шифрования, и для расшифрования
# используется ТОЛЬКО функция E_K. Паддинг НЕ нужен — CFB потоковый.
def cfb_encrypt(pt: bytes, key: bytes, iv: bytes) -> bytes:
    assert len(iv) == BLOCK
    out = bytearray()
    prev = iv
    # обрабатываем целыми блоками + последний неполный
    for i in range(0, len(pt), BLOCK):
        chunk = pt[i:i + BLOCK]
        keystream = encrypt_block(prev, key)
        ct_chunk = bytes(a ^ b for a, b in zip(chunk, keystream))
        out += ct_chunk
        prev = ct_chunk if len(ct_chunk) == BLOCK else ct_chunk.ljust(BLOCK, b"\x00")
    return bytes(out)


def cfb_decrypt(ct: bytes, key: bytes, iv: bytes) -> bytes:
    assert len(iv) == BLOCK
    out = bytearray()
    prev = iv
    for i in range(0, len(ct), BLOCK):
        chunk = ct[i:i + BLOCK]
        keystream = encrypt_block(prev, key)          # только E_K, НЕ D_K!
        pt_chunk = bytes(a ^ b for a, b in zip(chunk, keystream))
        out += pt_chunk
        prev = chunk if len(chunk) == BLOCK else chunk.ljust(BLOCK, b"\x00")
    return bytes(out)