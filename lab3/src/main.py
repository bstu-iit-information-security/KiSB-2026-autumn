import os
import time

from belt import encrypt_block
from modes import ecb_decrypt, ecb_encrypt, ofb_crypt, ofb_gamma, pad, unpad


key = bytes(range(32))
iv = bytes(range(100, 116))


def blocks(c):
    return [c[i:i + 16] for i in range(0, len(c), 16)]


# шифр расшиф строки
msg = "Привет, БелТ!".encode()
c = ecb_encrypt(msg, key)
assert ecb_decrypt(c, key) == msg

c = ofb_crypt(msg, key, iv)
assert ofb_crypt(c, key, iv) == msg

print("ECB/OFB round-trip: OK\n")


# padding   <16 16 >16
for n in (5, 16, 21):
    m = os.urandom(n)
    c = ecb_encrypt(m, key)
    assert ecb_decrypt(c, key) == m and unpad(pad(m)) == m

    print(f"len={n:2d} -> padded={len(pad(m))}, ECB ct={len(c)}, OFB ct={len(ofb_crypt(m, key, iv))}")


# ECB OFB    данные с повтор блоками
p = b"QWERTYU ZXCVBNM!" * 8
for name, c in (("ECB", ecb_encrypt(p, key)), ("OFB", ofb_crypt(p, key, iv))):
    print(f"{name}: уникальных блоков {len(set(blocks(c)))} из {len(blocks(c))}")


# оптимизация OFB
data = os.urandom(256 * 1024)


def ofb_naive(data):
    out, blk = bytearray(), iv

    for i in range(0, len(data), 16):
        blk = encrypt_block(blk, key)
        out += bytes(x ^ y for x, y in zip(data[i:i + 16], blk))

    return bytes(out)


t = time.perf_counter(); c1 = ofb_naive(data); t_naive = time.perf_counter() - t
t = time.perf_counter(); g = ofb_gamma(key, iv, len(data)); t_gen = time.perf_counter() - t
t = time.perf_counter(); c2 = ofb_crypt(data, key, iv, g); t_xor = time.perf_counter() - t

assert c1 == c2

print(f"naive: {t_naive:.3f}s | гамма заранее: {t_gen:.3f}s | XOR с готовой гаммой: {t_xor:.5f}s")
