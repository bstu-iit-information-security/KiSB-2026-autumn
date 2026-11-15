import os
import sys

from aes import encrypt_block, decrypt_block
from modes import (ecb_encrypt, ecb_decrypt, cbc_encrypt, cbc_decrypt,
                   cbc_encrypt_packed, cbc_decrypt_packed, cbc_verify_chain,
                   pad, unpad, generate_iv, check_iv, IVError, PaddingError,
                   CiphertextError)
import struct

IMAGE_DIR = r"D:\politex\ЛАБЫ\7 семестр\КиСБ\lab_3"
IMAGE_NAME = "Ducky.bmp"

KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
IV = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def title(s):
    print("\n" + "=" * 70 + f"\n{s}\n" + "=" * 70)


def demo_block():
    title("1. Один блок AES-128 (тестовый вектор FIPS-197, Приложение C.1)")
    pt = bytes.fromhex("00112233445566778899aabbccddeeff")
    ct = encrypt_block(pt, KEY)
    print("PT :", pt.hex())
    print("KEY:", KEY.hex())
    print("CT :", ct.hex(), "(ожидается 69c4e0d86a7b0430d8cdb78070b4c55a)")
    print("D(E(PT)) == PT:", decrypt_block(ct, KEY) == pt)


def demo_strings():
    title("2. Шифрование/расшифрование тестовых строк (ECB и CBC)")
    for text in ["Hello, AES!", "Лабораторная работа №3", "A" * 40]:
        data = text.encode("utf-8")
        e = ecb_encrypt(data, KEY)
        c = cbc_encrypt(data, KEY, IV)
        print(f"\nТекст: {text!r} ({len(data)} байт)")
        print("  ECB:", e.hex())
        print("  CBC:", c.hex())
        print("  ECB расшифр.:", ecb_decrypt(e, KEY).decode(), "| CBC расшифр.:",
              cbc_decrypt(c, KEY, IV).decode())


def demo_padding():
    title("3. Паддинг PKCS#7: длины <16, =16, >16 байт")
    for n in (5, 15, 16, 17, 32):
        m = bytes(range(65, 65 + n % 26)) if n < 26 else b"B" * n
        m = (m * 2)[:n]
        p = pad(m)
        k = p[-1]
        print(f"L={n:2d}: k={k:2d}, длина после паддинга={len(p):2d}, "
              f"хвост={p[-k:].hex()}, unpad ok={unpad(p) == m}")
    print("\nПроверка отказов unpad():")
    bad = [("k=0", bytes(15) + b"\x00"), ("k=17", bytes(15) + b"\x11"),
           ("k=4, но байты не равны", bytes(12) + b"\x01\x02\x03\x04")]
    for name, blk in bad:
        try:
            unpad(blk)
            print(f"  {name}: НЕ обнаружено (ошибка!)")
        except PaddingError as e:
            print(f"  {name}: PaddingError - {e}")


def demo_iv_and_chain():
    title("4. Строгая проверка IV и цепочки блоков CBC")
    for name, iv in [("None", None), ("15 байт", bytes(15)), ("17 байт", bytes(17)),
                     ("str вместо bytes", "0123456789abcdef"), ("корректный", IV)]:
        try:
            check_iv(iv)
            print(f"  IV {name}: принят")
        except IVError as e:
            print(f"  IV {name}: IVError - {e}")

    msg = b"Chain of blocks: C_i depends on C_{i-1}"
    padded = pad(msg)
    ct = cbc_encrypt(msg, KEY, IV)
    print("\nРучная проверка цепочки C_i = E(P_i xor C_{i-1}):",
          cbc_verify_chain(ct, KEY, IV, padded))

    iv2 = generate_iv()
    print("Тот же текст, другой IV -> шифротекст другой:",
          cbc_encrypt(msg, KEY, iv2) != ct)

    wrong = bytearray(IV); wrong[0] ^= 1
    bad_iv_pt = cbc_decrypt(ct, KEY, bytes(wrong), padding=False)
    good_pt = cbc_decrypt(ct, KEY, IV, padding=False)
    diff = [i for i in range(len(good_pt)) if good_pt[i] != bad_iv_pt[i]]
    print(f"Неверный IV (1 бит): изменились байты открытого текста {diff} "
          "(только блок P_1, причём ровно тот же бит)")

    t = bytearray(ct); t[16] ^= 0x01        
    pt_t = cbc_decrypt(bytes(t), KEY, IV, padding=False)
    blocks_bad = sorted({i // 16 + 1 for i in range(len(good_pt)) if good_pt[i] != pt_t[i]})
    print(f"Порча 1 бита в C_2 -> затронуты блоки открытого текста: P_{blocks_bad}")
    print("  (P_2 разрушен полностью, в P_3 меняется один бит; остальные не затронуты)")

    packed = cbc_encrypt_packed(msg, KEY)
    print("\nУпакованный формат IV||C: длина", len(packed),
          "| расшифрование ok:", cbc_decrypt_packed(packed, KEY) == msg)
    try:
        cbc_decrypt(ct[:-3], KEY, IV)
    except CiphertextError as e:
        print("Обрезанный шифротекст -> CiphertextError:", e)


def split_bmp(data: bytes):
    if data[:2] != b"BM":
        raise ValueError("это не BMP-файл")
    offset = struct.unpack_from("<I", data, 10)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    if bpp != 24 or compression != 0:
        raise ValueError(f"нужен 24-битный BMP без сжатия (получено: {bpp} бит, сжатие {compression})")
    return data[:offset], data[offset:]


def find_image():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = [IMAGE_DIR, here]
    for dr in dirs:
        p = os.path.join(dr, IMAGE_NAME)
        if os.path.isfile(p):
            return p
    for dr in dirs:
        if os.path.isdir(dr):
            for f in sorted(os.listdir(dr)):
                if f.lower().endswith(".bmp") and not f.lower().startswith("encrypted"):
                    return os.path.join(dr, f)
    raise SystemExit(f"BMP-картинка не найдена ни в {IMAGE_DIR}, ни в {here}. "
                     f"Поправьте IMAGE_DIR / IMAGE_NAME в начале demo.py.")


def demo_image(path=None):
    title("5. Уязвимость ECB на графическом файле (BMP)")
    os.makedirs(OUT, exist_ok=True)
    path = path or find_image()
    with open(path, "rb") as f:
        data = f.read()
    header, pixels = split_bmp(data)         
    print(f"Файл {path}: заголовок {len(header)} байт, пиксельных данных {len(pixels)} байт")

    ecb_ct = ecb_encrypt(pixels, KEY)
    cbc_ct = cbc_encrypt(pixels, KEY, IV)
    with open(os.path.join(OUT, "encrypted_ecb.bmp"), "wb") as f:
        f.write(header + ecb_ct[:len(pixels)])
    with open(os.path.join(OUT, "encrypted_cbc.bmp"), "wb") as f:
        f.write(header + cbc_ct[:len(pixels)])

    def stats(ct):
        blocks = [ct[i:i + 16] for i in range(0, len(ct), 16)]
        return len(blocks), len(set(blocks))

    n, u_ecb = stats(ecb_ct)
    _, u_cbc = stats(cbc_ct)
    print(f"Блоков шифротекста: {n}")
    print(f"  ECB: уникальных блоков {u_ecb} (повторяющихся {n - u_ecb}) -> структура видна")
    print(f"  CBC: уникальных блоков {u_cbc} (повторяющихся {n - u_cbc}) -> шум")
    assert ecb_decrypt(ecb_ct, KEY) == pixels and cbc_decrypt(cbc_ct, KEY, IV) == pixels
    print("Расшифрование обоих режимов возвращает исходные пиксели: True")
    print(f"Файлы сохранены в {OUT}: encrypted_ecb.bmp, encrypted_cbc.bmp")


if __name__ == "__main__":
    args = sys.argv[1:]
    blocks = {"1": demo_block, "2": demo_strings, "3": demo_padding, "4": demo_iv_and_chain}
    if args and args[0] in blocks:
        blocks[args[0]]()
    elif args and args[0] == "5":
        demo_image(args[1] if len(args) > 1 else None)
    else:
        demo_block()
        demo_strings()
        demo_padding()
        demo_iv_and_chain()
        demo_image(args[0] if args else None)
