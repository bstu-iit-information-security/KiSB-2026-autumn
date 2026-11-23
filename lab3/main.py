"""Демонстрация ЛР №3, вариант 1: AES-128, ECB + CBC, PKCS#7.
Запуск:  uv run python main.py   (результаты -> папка out/)"""
import os
import struct
from aes import encrypt_block, decrypt_block
from modes import pad, unpad, ecb_encrypt, ecb_decrypt, cbc_encrypt, cbc_decrypt

KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f")


def demo_padding():
    print("== 1. Паддинг PKCS#7 и round-trip ==")
    iv = os.urandom(16)
    for n in (5, 15, 16, 17, 32):
        m = (b"A" * n)
        ecb_ct, cbc_ct = ecb_encrypt(m, KEY), cbc_encrypt(m, KEY, iv)
        ok = ecb_decrypt(ecb_ct, KEY) == m and cbc_decrypt(cbc_ct, KEY, iv) == m
        print(f"  len={n:>2} -> padded={len(pad(m)):>2} (+{len(pad(m)) - n:>2} байт, "
              f"последний байт=0x{pad(m)[-1]:02x}), ct={len(ecb_ct)} Б, расшифровка верна: {ok}")
    text = "Привет, AES-128!".encode()
    print("  Строка:", text, "->", cbc_encrypt(text, KEY, iv).hex()[:32] + "...")


def make_bmp(path, w=256, h=256):
    """24-бит BMP: белый фон, чёрный круг, красный квадрат (большие однотонные области)."""
    px = bytearray()
    for y in range(h):
        for x in range(w):
            if (x - 128) ** 2 + (y - 128) ** 2 < 80 ** 2:
                bgr = (0, 0, 0)
            elif 10 < x < 60 and 10 < y < 60:
                bgr = (0, 0, 255)
            else:
                bgr = (255, 255, 255)
            px += bytes(bgr)
    header = b"BM" + struct.pack("<IHHI", 54 + len(px), 0, 0, 54) + \
        struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(px), 2835, 2835, 0, 0)
    return header, bytes(px)


def unique_blocks(data):
    bl = [data[i:i + 16] for i in range(0, len(data) - 15, 16)]
    return len(set(bl)), len(bl)


def demo_ecb_vs_cbc():
    print("\n== 2. ECB vs CBC на изображении ==")
    os.makedirs("out", exist_ok=True)
    header, pixels = make_bmp("out/original.bmp")
    iv = os.urandom(16)
    # шифротекст длиннее на паддинг -> обрезаем до размера оригинала, чтобы BMP открывался
    results = {"original": pixels,
               "ecb": ecb_encrypt(pixels, KEY)[:len(pixels)],
               "cbc": cbc_encrypt(pixels, KEY, iv)[:len(pixels)]}
    for name, data in results.items():
        with open(f"out/{name}.bmp", "wb") as f:
            f.write(header + data)
        u, t = unique_blocks(data)
        print(f"  {name:<8} уникальных 16-байтных блоков: {u:>6} из {t}")
    assert ecb_decrypt(ecb_encrypt(pixels, KEY), KEY) == pixels
    assert cbc_decrypt(cbc_encrypt(pixels, KEY, iv), KEY, iv) == pixels
    print("  Файлы: out/original.bmp, out/ecb.bmp, out/cbc.bmp (расшифровка проверена)")


if __name__ == "__main__":
    demo_padding()
    demo_ecb_vs_cbc()
