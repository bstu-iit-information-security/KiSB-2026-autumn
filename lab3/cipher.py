from belt import decrypt_block, encrypt_block

BLOCK_SIZE = 16
COUNTER_MASK = (1 << 128) - 1

KEY = bytes.fromhex("E9DEE72C8F0C0FA62DDB49F46F73964706075316ED247A3739CBA38303A98BF6")
NONCE = bytes.fromhex("BE32971343FC9A48A02A885F194B09A1")
BLOCK = bytes.fromhex("B194BAC80A08F53B366D008E584A5DE4")
BLOCK_CIPHER = bytes.fromhex("69CCA1C93557C9E3D66BC3E0FA88FA6E")
CTR_CIPHER = bytes.fromhex("52C9AF96FF50F64435FC43DEF56BD797")


def pad(data):
    size = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + bytes([size]) * size


def unpad(data):
    if not data:
        raise ValueError("invalid padding")
    size = data[-1]
    if not 1 <= size <= BLOCK_SIZE or size > len(data) or data[-size:] != bytes([size]) * size:
        raise ValueError("invalid padding")
    return data[:-size]


def ecb_encrypt(data, key):
    padded = pad(data)
    return b"".join(
        encrypt_block(padded[i:i + BLOCK_SIZE], key)
        for i in range(0, len(padded), BLOCK_SIZE)
    )


def ecb_decrypt(data, key):
    padded = b"".join(
        decrypt_block(data[i:i + BLOCK_SIZE], key)
        for i in range(0, len(data), BLOCK_SIZE)
    )
    return unpad(padded)


def keystream(key, nonce, length):
    if len(nonce) != BLOCK_SIZE:
        raise ValueError("nonce must be 16 bytes")
    counter = encrypt_block(nonce, key)
    result = bytearray()
    while len(result) < length:
        counter = ((int.from_bytes(counter, "little") + 1) & COUNTER_MASK).to_bytes(BLOCK_SIZE, "little")
        result.extend(encrypt_block(counter, key))
    return bytes(result[:length])


def ctr_crypt(data, key, nonce):
    return bytes(a ^ b for a, b in zip(data, keystream(key, nonce, len(data))))


def main():
    block_result = encrypt_block(BLOCK, KEY)
    ctr_result = ctr_crypt(BLOCK, KEY, NONCE)
    print("block vector", block_result.hex().upper(), block_result == BLOCK_CIPHER)
    print("block roundtrip", decrypt_block(block_result, KEY) == BLOCK)
    print("ctr vector", ctr_result.hex().upper(), ctr_result == CTR_CIPHER)
    print("ctr roundtrip", ctr_crypt(ctr_result, KEY, NONCE) == BLOCK)

    for message in (b"A", b"0123456789abcdef", b"0123456789abcdefABCD"):
        padded = pad(message)
        ecb = ecb_encrypt(message, KEY)
        ctr = ctr_crypt(message, KEY, NONCE)
        print(
            "len", len(message),
            "pad", padded[len(message):].hex().upper(),
            "ecb", ecb_decrypt(ecb, KEY) == message,
            "ctr", ctr_crypt(ctr, KEY, NONCE) == message,
            "ctr_len", len(ctr),
        )

    pattern = b"KiSBKiSBKiSBKiSB" * 4
    ecb = ecb_encrypt(pattern, KEY)
    ctr = ctr_crypt(pattern, KEY, NONCE)
    ecb_blocks = [ecb[i:i + BLOCK_SIZE] for i in range(0, len(ecb), BLOCK_SIZE)]
    ctr_blocks = [ctr[i:i + BLOCK_SIZE] for i in range(0, len(ctr), BLOCK_SIZE)]
    print("pattern", "plain", len(set(blocks(pattern))), "ecb", len(set(ecb_blocks)), "ctr", len(set(ctr_blocks)))


def blocks(data):
    return [data[i:i + BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]


if __name__ == "__main__":
    main()
