"""ECB с PKCS#7 и классический CTR по формулам методички."""

from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

from belt import BLOCK_SIZE, Belt


def pad(data: bytes) -> bytes:
    count = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + bytes([count]) * count


def unpad(data: bytes) -> bytes:
    if not data or len(data) % BLOCK_SIZE:
        raise ValueError("Некорректная длина дополненного сообщения.")
    count = data[-1]
    if not 1 <= count <= BLOCK_SIZE or data[-count:] != bytes([count]) * count:
        raise ValueError("Некорректное дополнение PKCS#7.")
    return data[:-count]


def ecb_encrypt(data: bytes, key: bytes) -> bytes:
    cipher = Belt(key)
    padded = pad(data)
    return b"".join(
        cipher.encrypt_block(padded[offset:offset + BLOCK_SIZE])
        for offset in range(0, len(padded), BLOCK_SIZE)
    )


def ecb_decrypt(data: bytes, key: bytes) -> bytes:
    cipher = Belt(key)
    if not data or len(data) % BLOCK_SIZE:
        raise ValueError("Шифротекст ECB должен состоять из целых блоков.")
    padded = b"".join(
        cipher.decrypt_block(data[offset:offset + BLOCK_SIZE])
        for offset in range(0, len(data), BLOCK_SIZE)
    )
    return unpad(padded)


def _validate_ctr(data: bytes, key: bytes, iv: bytes, start: int) -> None:
    Belt(key)
    if len(iv) != 8:
        raise ValueError("IV для выбранного формата CTR должен иметь 8 байт.")
    blocks = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
    if not 0 <= start < 2**64 or start + blocks > 2**64:
        raise ValueError("Переполнение 64-битной части счётчика.")


def ctr_crypt(data: bytes, key: bytes, iv: bytes, start: int = 0) -> bytes:
    """T_i = IV (8 байт) || counter (8 байт, big-endian), без паддинга."""
    _validate_ctr(data, key, iv, start)
    cipher = Belt(key)
    result = bytearray()

    for block_index, offset in enumerate(range(0, len(data), BLOCK_SIZE)):
        counter = (start + block_index).to_bytes(8, "big")
        gamma = cipher.encrypt_block(iv + counter)
        block = data[offset:offset + BLOCK_SIZE]
        result.extend(value ^ mask for value, mask in zip(block, gamma))

    return bytes(result)


def _ctr_worker(task: tuple) -> bytes:
    return ctr_crypt(*task)


def ctr_parallel(data: bytes, key: bytes, iv: bytes, workers: int = 2,
                 start: int = 0) -> bytes:
    """Каждый процесс получает свою часть и начальный номер блока."""
    _validate_ctr(data, key, iv, start)
    if workers < 1:
        raise ValueError("Количество процессов должно быть положительным.")
    if not data:
        return b""

    blocks = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
    chunk_blocks = (blocks + workers - 1) // workers
    chunk_size = chunk_blocks * BLOCK_SIZE
    tasks = [
        (data[offset:offset + chunk_size], key, iv, start + offset // BLOCK_SIZE)
        for offset in range(0, len(data), chunk_size)
    ]
    with ProcessPoolExecutor(max_workers=workers,
                             mp_context=get_context("spawn")) as pool:
        return b"".join(pool.map(_ctr_worker, tasks))
