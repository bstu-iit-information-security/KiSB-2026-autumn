from belt import encrypt_block, decrypt_block


B = 16  # размер блока (128)



# ================================================== PKCS#7 ====
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



# ================================================== ECB ====
def ecb_encrypt(data, key):
    data = pad(data)

    return b"".join(encrypt_block(data[i:i + B], key) for i in range(0, len(data), B))


def ecb_decrypt(data, key):
    if len(data) % B:
        raise ValueError("длина шифротекста не кратна 16")

    pt = b"".join(decrypt_block(data[i:i + B], key) for i in range(0, len(data), B))

    return unpad(pt)



# ================================================== OFB ====
def ofb_gamma(key, iv, length):
    out = bytearray()
    blk = iv

    for _ in range(-(-length // B)):
        blk = encrypt_block(blk, key)
        out += blk

    return bytes(out[:length])


def ofb_crypt(data, key, iv, gamma=None):
    n = len(data)

    if gamma is None:
        gamma = ofb_gamma(key, iv, n)

    if len(gamma) < n:
        raise ValueError("гаммы меньше чем данных")

    x = int.from_bytes(data, "big") ^ int.from_bytes(gamma[:n], "big")

    return x.to_bytes(n, "big")
