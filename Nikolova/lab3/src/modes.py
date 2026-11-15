from multiprocessing import Pool

from belt import encrypt_block, decrypt_block

BLOCK = 16


def pad(data):
    k = BLOCK - (len(data) % BLOCK)
    return data + bytes([k]) * k


def unpad(data):
    if len(data) == 0 or len(data) % BLOCK != 0:
        raise ValueError("Неверная длина данных")
    k = data[-1]
    if k < 1 or k > BLOCK:
        raise ValueError("Неверный паддинг")
    if data[-k:] != bytes([k]) * k:
        raise ValueError("Неверный паддинг")
    return data[:-k]


def ecb_encrypt(data, key):
    data = pad(data)
    result = b''
    for i in range(0, len(data), BLOCK):
        result += encrypt_block(data[i:i + BLOCK], key)
    return result


def ecb_decrypt(data, key):
    if len(data) % BLOCK != 0:
        raise ValueError("Длина шифротекста не кратна 16")
    result = b''
    for i in range(0, len(data), BLOCK):
        result += decrypt_block(data[i:i + BLOCK], key)
    return unpad(result)


def counter_block(iv, i):
    n = (int.from_bytes(iv, 'big') + i) % (1 << 128)
    return n.to_bytes(16, 'big')


def xor_bytes(a, b):
    return bytes([x ^ y for x, y in zip(a, b)])


def ctr_chunk(args):
    chunk, key, iv, start = args
    result = b''
    for j in range(0, len(chunk), BLOCK):
        gamma = encrypt_block(counter_block(iv, start + j // BLOCK), key)
        result += xor_bytes(chunk[j:j + BLOCK], gamma)
    return result


def ctr_crypt(data, key, iv):
    return ctr_chunk((data, key, iv, 0))


def ctr_crypt_parallel(data, key, iv, processes=4):
    total_blocks = (len(data) + BLOCK - 1) // BLOCK
    blocks_per_chunk = (total_blocks + processes - 1) // processes
    tasks = []
    for p in range(processes):
        start_block = p * blocks_per_chunk
        chunk = data[start_block * BLOCK:(start_block + blocks_per_chunk) * BLOCK]
        if len(chunk) > 0:
            tasks.append((chunk, key, iv, start_block))
    with Pool(processes) as pool:
        parts = pool.map(ctr_chunk, tasks)
    return b''.join(parts)
