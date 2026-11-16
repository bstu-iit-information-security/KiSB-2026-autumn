"""ЛР №3, вариант 12: СТБ 34.101.31 («БелТ»), режимы ECB + OFB.

Запуск:  python3 main.py [размер_бенчмарка_КиБ]

Весь вывод дублируется в lab3_output.txt, изображения пишутся в images/.
"""

import os
import random
import struct
import sys
import time
import zlib

import belt
from belt import BLOCK_SIZE, BeltCipher, encrypt_block, decrypt_block, g_ref, G5_T
from modes import (pkcs7_pad, pkcs7_unpad, ecb_encrypt, ecb_decrypt,
                   OfbGamma, ofb_encrypt, ofb_decrypt, ofb_encrypt_naive, xor_bytes)

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "images")

# Фиксированные ключ и IV, чтобы вывод был воспроизводим.
# В реальном применении IV = os.urandom(16) и не повторяется при одном ключе.
KEY = bytes.fromhex("E9DEE72C8F0C0FA62DDB49F46F73964706075316ED247A3739CBA38303A98BF6")
IV = bytes.fromhex("BE32971343FC9A48A02A885F194B09A1")


class Tee:
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")
        self.out = sys.stdout

    def write(self, s):
        self.out.write(s)
        self.f.write(s)

    def flush(self):
        self.out.flush()
        self.f.flush()


def hx(b: bytes, group: int = 16) -> str:
    h = b.hex().upper()
    return " ".join(h[i:i + 2 * group] for i in range(0, len(h), 2 * group))


def title(s: str):
    print()
    print("=" * 78)
    print(s)
    print("=" * 78)


def bit_diff(x: bytes, y: bytes) -> int:
    return sum(bin(a ^ b).count("1") for a, b in zip(x, y))


# --------------------------------------------------------------------------
# 1. Контрольные примеры стандарта
# --------------------------------------------------------------------------

def test_vectors():
    title("1. Контрольные примеры СТБ 34.101.31-2011 (прил. А)")
    cases = [
        ("A.1 зашифрование",
         "E9DEE72C8F0C0FA62DDB49F46F73964706075316ED247A3739CBA38303A98BF6",
         "B194BAC80A08F53B366D008E584A5DE4", "69CCA1C93557C9E3D66BC3E0FA88FA6E", True),
        ("A.4 расшифрование",
         "92BD9B1CE5D141015445FBC95E4D0EF2682080AA227D642F2687F93490405511",
         "E12BDC1AE28257EC703FCCF095EE8DF1", "0DC5300600CAB840B38448E5E993F421", False),
    ]
    ok_all = True
    for name, k, x, y, enc in cases:
        k, x, y = bytes.fromhex(k), bytes.fromhex(x), bytes.fromhex(y)
        if enc:
            ref = encrypt_block(x, k)
            fast = BeltCipher(k).encrypt_block(x)
            back = decrypt_block(ref, k)
        else:
            ref = decrypt_block(x, k)
            fast = BeltCipher(k).decrypt_block(x)
            back = encrypt_block(ref, k)
        ok = ref == y and fast == y and back == x
        ok_all &= ok
        print(f"{name}:")
        print(f"  ключ      {hx(k)}")
        print(f"  вход      {hx(x)}")
        print(f"  выход     {hx(ref)}  (быстрая реализация: {hx(fast)})")
        print(f"  ожидается {hx(y)}  -> {'OK' if ok else 'ОШИБКА'}")
    # табличная G совпадает с G по определению
    rnd = random.Random(1)
    g_ok = True
    for _ in range(2000):
        u = rnd.getrandbits(32)
        t = G5_T[0][u & 255] ^ G5_T[1][(u >> 8) & 255] ^ G5_T[2][(u >> 16) & 255] ^ G5_T[3][u >> 24]
        g_ok &= t == g_ref(u, 5)
    print(f"Табличная G_5 совпадает с определением на 2000 случайных словах: {'OK' if g_ok else 'ОШИБКА'}")
    return ok_all and g_ok


# --------------------------------------------------------------------------
# 2. Шифрование тестовых строк
# --------------------------------------------------------------------------

def test_strings():
    title("2. Зашифрование и расшифрование тестовых строк")
    texts = [
        "Hello, BelT!",
        "Криптография и сетевая безопасность, ЛР №3",
        "СТБ 34.101.31 — государственный стандарт Республики Беларусь.",
    ]
    ok_all = True
    for t in texts:
        p = t.encode("utf-8")
        c_ecb = ecb_encrypt(p, KEY)
        c_ofb = ofb_encrypt(p, KEY, IV)
        d_ecb = ecb_decrypt(c_ecb, KEY).decode("utf-8")
        d_ofb = ofb_decrypt(c_ofb, KEY, IV).decode("utf-8")
        ok = d_ecb == t and d_ofb == t
        ok_all &= ok
        print(f"Текст: \"{t}\" ({len(p)} байт UTF-8)")
        print(f"  ECB  C = {hx(c_ecb)}  ({len(c_ecb)} байт)")
        print(f"  OFB  C = {hx(c_ofb)}  ({len(c_ofb)} байт)")
        print(f"  расшифровано ECB: \"{d_ecb}\"")
        print(f"  расшифровано OFB: \"{d_ofb}\"  -> {'OK' if ok else 'ОШИБКА'}")

    # массовая проверка на случайных сообщениях произвольной длины
    rnd = random.Random(12)
    n_ok = 0
    N = 300
    for i in range(N):
        n = rnd.randrange(0, 100)
        p = bytes(rnd.getrandbits(8) for _ in range(n))
        key = bytes(rnd.getrandbits(8) for _ in range(32))
        iv = bytes(rnd.getrandbits(8) for _ in range(16))
        c1, c2 = ecb_encrypt(p, key), ofb_encrypt(p, key, iv)
        good = (ecb_decrypt(c1, key) == p and ofb_decrypt(c2, key, iv) == p
                and len(c1) == (n // 16 + 1) * 16 and len(c2) == n
                and ofb_encrypt_naive(p, key, iv) == c2)
        n_ok += good
    print(f"\nСлучайные сообщения длиной 0..99 байт, случайные K и IV: {n_ok}/{N} OK")
    return ok_all and n_ok == N


# --------------------------------------------------------------------------
# 3. Паддинг PKCS#7
# --------------------------------------------------------------------------

def test_padding():
    title("3. Дополнение PKCS#7 (режим ECB) и его отсутствие в OFB")
    base = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    print(f"{'L':>3} | {'k':>3} | {'дополненное сообщение (hex)':<100} | ECB | OFB")
    ok_all = True
    for n in (0, 5, 15, 16, 17, 31, 32):
        p = base[:n]
        padded = pkcs7_pad(p)
        k = len(padded) - n
        c_ecb = ecb_encrypt(p, KEY)
        c_ofb = ofb_encrypt(p, KEY, IV)
        ok = (ecb_decrypt(c_ecb, KEY) == p and ofb_decrypt(c_ofb, KEY, IV) == p
              and 1 <= k <= 16 and padded[-k:] == bytes([k]) * k)
        ok_all &= ok
        print(f"{n:>3} | {k:>3} | {hx(padded):<100} | {len(c_ecb):>3} | {len(c_ofb):>3}")
    print("L — длина текста, k — число байт дополнения; ECB/OFB — длина шифротекста.")
    print("Сообщение ровно 16 байт получает целый блок 10 10 ... 10 (k = 16).")

    print("\nСнятие паддинга с некорректных данных:")
    bad_cases = [
        ("последний байт 0x00", b"A" * 15 + b"\x00"),
        ("последний байт 0x11 (> 16)", b"A" * 15 + b"\x11"),
        ("k = 4, но байты 03 04 04 04", b"A" * 12 + b"\x03\x04\x04\x04"),
        ("длина не кратна 16", b"A" * 17),
        ("пустой ввод", b""),
    ]
    for name, data in bad_cases:
        try:
            pkcs7_unpad(data)
            print(f"  {name:<32} -> принято (ОШИБКА)")
            ok_all = False
        except ValueError as e:
            print(f"  {name:<32} -> отклонено: {e}")
    # подмена последнего блока шифротекста ECB ломает паддинг
    c = bytearray(ecb_encrypt(b"short message", KEY))
    c[-1] ^= 0x01
    try:
        ecb_decrypt(bytes(c), KEY)
        print("  искажённый шифротекст ECB        -> принят (паддинг совпал случайно)")
    except ValueError as e:
        print(f"  искажённый шифротекст ECB        -> отклонено: {e}")
    return ok_all


# --------------------------------------------------------------------------
# 4. Свойства OFB: неполный блок, независимость гаммы, повтор IV
# --------------------------------------------------------------------------

def test_ofb_properties():
    title("4. Свойства режима OFB")
    p = b"23 bytes, not 16*k !!!!"
    c = ofb_encrypt(p, KEY, IV)
    g = OfbGamma(KEY, IV).take(32)
    print(f"Текст {len(p)} байт -> шифротекст {len(c)} байт (без паддинга).")
    print(f"  P     = {hx(p)}")
    print(f"  гамма = {hx(g)}")
    print(f"  C     = {hx(c)}")
    print("  Второй блок использует только первые 7 байт I_2, остаток гаммы отбрасывается.")

    # гамма не зависит от текста
    p1 = b"A" * 48
    p2 = "Другой текст той же длины".encode("utf-8").ljust(48, b".")[:48]
    g1 = xor_bytes(ofb_encrypt(p1, KEY, IV), p1)
    g2 = xor_bytes(ofb_encrypt(p2, KEY, IV), p2)
    print(f"\nC xor P для двух разных текстов при одном (K, IV) совпадает: {g1 == g2}")
    print("  => гамма — функция только от K и IV, её можно выработать заранее.")

    # повтор IV
    x = xor_bytes(ofb_encrypt(p1, KEY, IV), ofb_encrypt(p2, KEY, IV))
    print(f"При повторе IV: C1 xor C2 == P1 xor P2: {x == xor_bytes(p1, p2)}")
    print("  => знание одного текста раскрывает другой; IV нельзя повторять при одном ключе.")

    # ECB для сравнения: одинаковые блоки
    c_ecb = ecb_encrypt(b"0123456789ABCDEF" * 3, KEY, pad=False)
    c_ofb = ofb_encrypt(b"0123456789ABCDEF" * 3, KEY, IV)
    print("\nТри одинаковых блока '0123456789ABCDEF':")
    print(f"  ECB: {hx(c_ecb)}")
    print(f"  OFB: {hx(c_ofb)}")

    # гамма предвычисляется частями и продолжается
    gen = OfbGamma(KEY, IV)
    gen.precompute(20)
    parts = gen.take(7) + gen.take(30) + gen.take(11)
    same = parts == OfbGamma(KEY, IV).take(48)
    print(f"\nГамма, выданная порциями 7+30+11 байт после предвычисления 20 байт, "
          f"совпадает с выработанной целиком: {same}")
    return g1 == g2 and same


# --------------------------------------------------------------------------
# 5. Искажение одного бита шифротекста
# --------------------------------------------------------------------------

def test_bit_error():
    title("5. Инверсия одного бита шифротекста (ошибка передачи)")
    p = bytes(range(64))
    c_ecb = bytearray(ecb_encrypt(p, KEY, pad=False))
    c_ofb = bytearray(ofb_encrypt(p, KEY, IV))
    pos = 16 * 1 + 5          # байт 5 второго блока
    c_ecb[pos] ^= 0x08
    c_ofb[pos] ^= 0x08
    d_ecb = ecb_decrypt(bytes(c_ecb), KEY, pad=False)
    d_ofb = ofb_decrypt(bytes(c_ofb), KEY, IV)
    print(f"Инвертирован бит 3 байта {pos} (блок 2). Отличия расшифрованного текста от исходного:")
    print(f"{'блок':>5} | {'ECB, бит':>9} | {'OFB, бит':>9}")
    for i in range(4):
        s = slice(16 * i, 16 * i + 16)
        print(f"{i + 1:>5} | {bit_diff(p[s], d_ecb[s]):>9} | {bit_diff(p[s], d_ofb[s]):>9}")
    print("ECB: искажается весь блок (~64 бит из 128), соседние блоки целы.")
    print("OFB: искажается ровно тот же бит открытого текста, ошибка не размножается.")


# --------------------------------------------------------------------------
# 6. Изображение: ECB vs OFB
# --------------------------------------------------------------------------

W, HGT = 256, 256


def make_image() -> bytes:
    """RGB-картинка с крупными однотонными областями (сырые пиксели, построчно сверху вниз)."""
    bg = (240, 240, 235)
    cols = [(200, 30, 45), (25, 90, 170), (30, 150, 70), (250, 190, 20), (20, 20, 20)]
    px = bytearray()
    for y in range(HGT):
        for x in range(W):
            c = bg
            if 24 <= x < 112 and 24 <= y < 112:
                c = cols[0]                                        # квадрат
            if (x - 180) ** 2 + (y - 68) ** 2 < 46 ** 2:
                c = cols[1]                                        # круг
            if 140 <= y < 236 and abs(x - 68) < (y - 140) // 2 + 2:
                c = cols[2]                                        # треугольник
            if 140 <= y < 236 and 140 <= x < 236 and ((x // 16) + (y // 16)) % 2 == 0:
                c = cols[3]                                        # шахматка
            if 120 <= y < 128 or 120 <= x < 128 and y < 120:
                c = cols[4]                                        # полосы
            px += bytes(c)
    return bytes(px)


def write_png(path: str, rgb: bytes, w: int, h: int, scale: int = 2):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = bytearray()
    for y in range(h):
        row = rgb[y * w * 3:(y + 1) * w * 3]
        big = b"".join(row[i:i + 3] * scale for i in range(0, len(row), 3))
        for _ in range(scale):
            raw += b"\x00" + big
    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w * scale, h * scale, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)


def write_bmp(path: str, rgb: bytes, w: int, h: int):
    """24-битный BMP: заголовок 54 байта, строки снизу вверх, порядок BGR."""
    rows = []
    for y in range(h - 1, -1, -1):
        row = rgb[y * w * 3:(y + 1) * w * 3]
        bgr = bytearray(len(row))
        bgr[0::3], bgr[1::3], bgr[2::3] = row[2::3], row[1::3], row[0::3]
        rows.append(bytes(bgr) + b"\x00" * ((4 - (w * 3) % 4) % 4))
    pixels = b"".join(rows)
    header = struct.pack("<2sIHHI", b"BM", 54 + len(pixels), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + pixels)


def read_bmp_pixels(path: str):
    with open(path, "rb") as f:
        data = f.read()
    off = struct.unpack_from("<I", data, 10)[0]
    return data[:off], data[off:]


def bmp_to_rgb(pixels: bytes, w: int, h: int) -> bytes:
    stride = w * 3 + (4 - (w * 3) % 4) % 4
    out = bytearray()
    for y in range(h - 1, -1, -1):
        row = pixels[y * stride:y * stride + w * 3]
        rgb = bytearray(len(row))
        rgb[0::3], rgb[1::3], rgb[2::3] = row[2::3], row[1::3], row[0::3]
        out += rgb
    return bytes(out)


def repeated_blocks(data: bytes) -> int:
    blocks = [data[i:i + 16] for i in range(0, len(data) - len(data) % 16, 16)]
    return len(blocks) - len(set(blocks))


def test_image():
    title("6. Шифрование графического файла: ECB против OFB")
    os.makedirs(IMG_DIR, exist_ok=True)
    rgb = make_image()
    bmp_path = os.path.join(IMG_DIR, "original.bmp")
    write_bmp(bmp_path, rgb, W, HGT)

    header, pixels = read_bmp_pixels(bmp_path)
    # Заголовок BMP оставляем открытым, шифруем только массив пикселей,
    # чтобы результат можно было открыть как картинку. Длина массива
    # 256*256*3 = 196608 кратна 16, поэтому ECB работает без паддинга.
    t0 = time.perf_counter()
    enc_ecb = ecb_encrypt(pixels, KEY, pad=False)
    t1 = time.perf_counter()
    enc_ofb = ofb_encrypt(pixels, KEY, IV)
    t2 = time.perf_counter()

    for name, px in (("ecb", enc_ecb), ("ofb", enc_ofb)):
        with open(os.path.join(IMG_DIR, f"encrypted_{name}.bmp"), "wb") as f:
            f.write(header + px)
    for name, px in (("original", pixels), ("encrypted_ecb", enc_ecb), ("encrypted_ofb", enc_ofb)):
        write_png(os.path.join(IMG_DIR, f"{name}.png"), bmp_to_rgb(px, W, HGT), W, HGT)

    ok = (ecb_decrypt(enc_ecb, KEY, pad=False) == pixels and ofb_decrypt(enc_ofb, KEY, IV) == pixels)
    nblocks = len(pixels) // 16
    print(f"Изображение {W}x{HGT}, 24 бит, массив пикселей {len(pixels)} байт = {nblocks} блоков.")
    print(f"Время: ECB {t1 - t0:.2f} c, OFB {t2 - t1:.2f} c. Обратное расшифрование: {'OK' if ok else 'ОШИБКА'}")
    print(f"{'':<14} | {'повторяющихся блоков':>21} | {'уникальных':>10}")
    for name, d in (("исходный", pixels), ("ECB", enc_ecb), ("OFB", enc_ofb)):
        r = repeated_blocks(d)
        print(f"{name:<14} | {r:>21} | {nblocks - r:>10}")
    print("Файлы: images/original.*, images/encrypted_ecb.*, images/encrypted_ofb.*")
    print("ECB сохраняет контуры фигур (одинаковые блоки пикселей -> одинаковые блоки")
    print("шифротекста), OFB даёт равномерный шум.")
    return ok


# --------------------------------------------------------------------------
# 7. Оптимизация выработки гаммы OFB (фокус варианта 12)
# --------------------------------------------------------------------------

def best_time(fn, repeat=3):
    best = float("inf")
    res = None
    for _ in range(repeat):
        t = time.perf_counter()
        res = fn()
        best = min(best, time.perf_counter() - t)
    return best, res


def benchmark(kib_list):
    title("7. Оптимизация выработки гаммы OFB")
    print("Сравниваются реализации OFB (время — лучшее из 3 запусков):")
    print("  A — наивная: encrypt_block(I, key) на каждом блоке (ключ разворачивается")
    print("      каждый раз, G по определению), побайтовый XOR;")
    print("  B — оптимизированная «на лету»: ключ развёрнут один раз, табличные G,")
    print("      состояние в виде 4 слов, XOR одной операцией над длинным целым;")
    print("  C — предвычисленная гамма: выработка заранее (офлайн) + только XOR (онлайн).")

    # микро-бенчмарк одного блока
    x = IV
    n = 3000
    c = BeltCipher(KEY)
    t_ref, _ = best_time(lambda: [encrypt_block(x, KEY) for _ in range(n)])
    t_fast, _ = best_time(lambda: [c.encrypt_block(x) for _ in range(n)])
    words = belt.bytes_to_words(x)
    t_words, _ = best_time(lambda: [c.encrypt_words(*words) for _ in range(n)])
    print(f"\nОдин блок E_K ({n} вызовов): эталон {t_ref / n * 1e6:.1f} мкс, "
          f"BeltCipher.encrypt_block {t_fast / n * 1e6:.1f} мкс, "
          f"encrypt_words {t_words / n * 1e6:.1f} мкс")

    print(f"\n{'объём':>9} | {'A наивн., с':>11} | {'B опт., с':>9} | {'C офлайн, с':>11} | "
          f"{'C онлайн, мс':>12} | {'A/B':>5} | {'A/C онл.':>9} | {'МиБ/с B':>8}")
    rows = []
    rnd = random.Random(3)
    for kib in kib_list:
        size = kib * 1024
        data = bytes(rnd.getrandbits(8) for _ in range(size))
        ta, ca = best_time(lambda: ofb_encrypt_naive(data, KEY, IV), repeat=1 if kib > 256 else 3)
        tb, cb = best_time(lambda: ofb_encrypt(data, KEY, IV))

        gens = []

        def offline():
            g = OfbGamma(KEY, IV)
            g.precompute(size)
            gens.append(g)
        toff, _ = best_time(offline)
        pre = gens[-1]
        gamma = pre.take(size)
        ton, cc = best_time(lambda: xor_bytes(data, gamma), repeat=5)
        assert ca == cb == cc, "результаты реализаций OFB не совпали"
        assert ofb_decrypt(cb, KEY, IV) == data
        rows.append((kib, ta, tb, toff, ton))
        print(f"{kib:>5} КиБ | {ta:>11.3f} | {tb:>9.3f} | {toff:>11.3f} | {ton * 1e3:>12.3f} | "
              f"{ta / tb:>5.1f} | {ta / ton:>9.0f} | {kib / 1024 / tb:>8.3f}")
    print("Все три реализации дают побитово одинаковый шифротекст.")
    print("Вывод: выработка гаммы — последовательная цепочка E_K, её нельзя распараллелить,")
    print("но её можно вынести за пределы критического пути: после предвычисления")
    print("зашифрование и расшифрование сводятся к одному XOR и почти не зависят от шифра.")
    return rows


def main():
    kib = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    sys.stdout = Tee(os.path.join(HERE, "lab3_output.txt"))
    print("ЛР №3. Блочные шифры и классические режимы шифрования")
    print("Вариант 12: СТБ 34.101.31 («БелТ»), режимы ECB + OFB,")
    print("оптимизация предварительной генерации псевдослучайной гаммы для OFB.")
    print(f"Ключ K  = {hx(KEY)}")
    print(f"IV      = {hx(IV)}")
    results = [
        ("контрольные примеры", test_vectors()),
        ("тестовые строки", test_strings()),
        ("паддинг", test_padding()),
        ("свойства OFB", test_ofb_properties()),
    ]
    test_bit_error()
    results.append(("изображение", test_image()))
    benchmark([kib] if kib else [16, 64, 256, 1024])
    title("Итог")
    for name, ok in results:
        print(f"  {name:<22} {'OK' if ok else 'ОШИБКА'}")
    sys.stdout.flush()
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
