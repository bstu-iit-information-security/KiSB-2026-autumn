from AES_128 import encrypt_block, decrypt_block

B = 16

# PKCS#7
def pad(data):
    k = B - len(data) % B
    return data + bytes([k]) * k

def unpad(data):
    if not data or len(data) % B:
        raise ValueError("неверная длина данных")
    k = data[-1]
    if not 1 <= k <= B or data[-k:] != bytes([k]) * k:
        raise ValueError("неверный padding")
    return data[:-k]

# ECB
def ecb_encrypt(data, key):
    data = pad(data)
    return b"".join(encrypt_block(data[i:i + B], key) for i in range(0, len(data), B))

def ecb_decrypt(data, key):
    if len(data) % B:
        raise ValueError("длина шифротекста не кратна 16")
    pt = b"".join(decrypt_block(data[i:i + B], key) for i in range(0, len(data), B))
    return unpad(pt)

# CFB
def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))

def cfb_encrypt(data, key, iv):
    if len(iv) != B:
        raise ValueError("IV должен быть 16 байт")
    out, prev = b"", iv
    for i in range(0, len(data), B):
        c = _xor(data[i:i + B], encrypt_block(prev, key))
        out += c
        prev = c
    return out

def cfb_decrypt(data, key, iv):
    if len(iv) != B:
        raise ValueError("IV должен быть 16 байт")
    out, prev = b"", iv
    for i in range(0, len(data), B):
        c = data[i:i + B]
        out += _xor(c, encrypt_block(prev, key))
        prev = c
    return out
