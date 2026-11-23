# -*- coding: utf-8 -*-
"""
Лабораторная работа №3, вариант 15.
Блочные шифры и классические режимы шифрования.

Вариант 15: базовый шифр AES-128, режимы ECB + CFB.
Фокус тестирования: оценка задержки распространения ошибки при порче
одного байта шифротекста в режимах ECB и CFB.

Структура проекта:
    aes128.py — модуль 1, блочный шифр (encrypt_block / decrypt_block);
    modes.py  — модуль 2, режимы ECB и CFB, дополнение PKCS#7;
    lab3.py   — меню, демонстрации и исследования (этот файл).
Сторонние криптографические библиотеки не используются; matplotlib и numpy
нужны только для рисунков (изображение и графики).
"""
import os
import secrets
import time
from collections import Counter

import aes128
import modes
from aes128 import BLOCK_SIZE
from modes import PaddingError

VARIANT = 15
TABLE_VARIANT = (VARIANT - 1) % 15 + 1          # = 15 (в таблице 15 вариантов)
DEFAULT_KEY = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
DEFAULT_IV = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
OUT_DIR = "results"
RNG = secrets.SystemRandom()


# ======================================================================
#                     ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ======================================================================
def hx(data, group=BLOCK_SIZE):
    """Шестнадцатеричная запись с разбиением на блоки по 16 байт."""
    h = data.hex()
    return " ".join(h[i:i + 2 * group] for i in range(0, len(h), 2 * group)) or "—"


def show_text(data):
    """Байты -> строка (каждый байт — один символ, непечатаемые заменяются на «·»)."""
    return "".join(chr(b) if 32 <= b < 127 else "·" for b in data)


def title(text):
    print("=" * 78)
    print(text)
    print("=" * 78)


def ask_int(prompt, default, lo=None, hi=None):
    s = input(f"{prompt} [{default}]: ").strip()
    if not s:
        return default
    v = int(s)
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ValueError(f"значение должно быть в диапазоне [{lo}, {hi}]")
    return v


def ask_bytes(prompt, default):
    """Ввод ключа / IV: 32 hex-символа, r — случайное значение, Enter — по умолчанию."""
    s = input(f"{prompt} (32 hex-символа, r — случайный) [{default.hex()}]: ").strip()
    if not s:
        return default
    if s.lower() == "r":
        v = secrets.token_bytes(BLOCK_SIZE)
        print(f"  сгенерировано: {v.hex()}")
        return v
    v = bytes.fromhex(s)
    if len(v) != BLOCK_SIZE:
        raise ValueError("нужно ровно 16 байт (32 hex-символа)")
    return v


def out_path(name):
    os.makedirs(OUT_DIR, exist_ok=True)
    return os.path.join(OUT_DIR, name)


# ======================================================================
#                     САМОПРОВЕРКА ПО ТЕСТ-ВЕКТОРАМ
# ======================================================================
# NIST SP 800-38A, приложение F (ключ и IV совпадают с DEFAULT_KEY и DEFAULT_IV)
SP_PT = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a" "ae2d8a571e03ac9c9eb76fac45af8e51"
                      "30c81c46a35ce411e5fbc1191a0a52ef" "f69f2445df4f9b17ad2b417be66c3710")
SP_ECB = bytes.fromhex("3ad77bb40d7a3660a89ecaf32466ef97" "f5d3d58503b9699de785895a96fdbaaf"
                       "43b1cd7f598ece23881b00e3ed030688" "7b0c785e27e8ad3f8223207104725dd4")
SP_CFB128 = bytes.fromhex("3b3fd92eb72dad20333449f8e83cfb4a" "c8a64537a0b3a93fcde3cdad9f1ce58b"
                          "26751f67a3cbb140b1808cf187a4f4df" "c04b05357c5d1c0eeac4c66f9ff7f2e6")
SP_CFB8 = bytes.fromhex("3b79424c9c0dd436bace9e0ed4586a4f32b9")       # первые 18 байт


def self_test():
    title("САМОПРОВЕРКА: тест-векторы FIPS-197 и NIST SP 800-38A, PKCS#7")
    res = []

    def check(name, ok):
        res.append(ok)
        print(f"  [{'OK' if ok else 'ОШИБКА'}] {name}")

    k = bytes(range(16))
    pt = bytes.fromhex("00112233445566778899aabbccddeeff")
    ct = aes128.encrypt_block(pt, k)
    check(f"FIPS-197 C.1: E_K(P) = {ct.hex()}", ct.hex() == "69c4e0d86a7b0430d8cdb78070b4c55a")
    check("FIPS-197 C.1: D_K(C) = P", aes128.decrypt_block(ct, k) == pt)
    trace = []
    pt = bytes.fromhex("3243f6a8885a308d313198a2e0370734")
    ct = aes128.encrypt_block(pt, DEFAULT_KEY, trace)
    check(f"FIPS-197 прил. B: E_K(P) = {ct.hex()}", ct.hex() == "3925841d02dc09fbdc118597196a0b32")
    rk = aes128.round_keys(DEFAULT_KEY)
    check(f"Расширение ключа: K(10) = {rk[10].hex()}",
          rk[10].hex() == "d014f9a8c9ee2589e13f0cc8b6630ca6")
    print("  Раундовые ключи и состояние после каждого раунда (пример FIPS-197, прил. B):")
    print(f"  {'r':>3}  {'K(r)':32}  состояние")
    for (r, st), kr in zip(trace, rk):
        print(f"  {r:>3}  {kr.hex()}  {st.hex()}")

    check("SP 800-38A F.1.1: ECB-AES128, зашифрование 4 блоков",
          modes.ecb_encrypt(SP_PT, DEFAULT_KEY, padding=False) == SP_ECB)
    check("SP 800-38A F.1.2: ECB-AES128, расшифрование",
          modes.ecb_decrypt(SP_ECB, DEFAULT_KEY, padding=False) == SP_PT)
    check("SP 800-38A F.3.13: CFB128-AES128, зашифрование",
          modes.cfb_encrypt(SP_PT, DEFAULT_KEY, DEFAULT_IV) == SP_CFB128)
    check("SP 800-38A F.3.14: CFB128-AES128, расшифрование",
          modes.cfb_decrypt(SP_CFB128, DEFAULT_KEY, DEFAULT_IV) == SP_PT)
    check("SP 800-38A F.3.7: CFB8-AES128, зашифрование 18 байт",
          modes.cfb_encrypt(SP_PT[:18], DEFAULT_KEY, DEFAULT_IV, 1) == SP_CFB8)
    check("SP 800-38A F.3.8: CFB8-AES128, расшифрование",
          modes.cfb_decrypt(SP_CFB8, DEFAULT_KEY, DEFAULT_IV, 1) == SP_PT[:18])

    # CFB: функция D_K подменяется «запрещённой», вызовы E_K подсчитываются
    saved_enc, saved_dec = aes128.encrypt_block, aes128.decrypt_block
    calls = [0]

    def counting(block, key):
        calls[0] += 1
        return saved_enc(block, key)

    def forbidden(*_):
        raise RuntimeError("в режиме CFB вызвана функция D_K")

    aes128.encrypt_block, aes128.decrypt_block = counting, forbidden
    try:
        ct = modes.cfb_encrypt(SP_PT[:40], DEFAULT_KEY, DEFAULT_IV)
        enc_calls = calls[0]
        ok = modes.cfb_decrypt(ct, DEFAULT_KEY, DEFAULT_IV) == SP_PT[:40]
    finally:
        aes128.encrypt_block, aes128.decrypt_block = saved_enc, saved_dec
    check(f"CFB, 40 байт: зашифрование — {enc_calls} вызова E_K, расшифрование — "
          f"{calls[0] - enc_calls} вызова E_K и 0 вызовов D_K", ok)

    pad = modes.pkcs7_pad
    check("PKCS#7: 5 байт -> добавлено 11 байт 0x0b", pad(b"A" * 5) == b"A" * 5 + b"\x0b" * 11)
    check("PKCS#7: 16 байт -> добавлен полный блок 0x10", pad(b"A" * 16) == b"A" * 16 + b"\x10" * 16)
    check("PKCS#7: pad/unpad для длин 0..48",
          all(modes.pkcs7_unpad(pad(bytes(L))) == bytes(L) for L in range(49)))
    bad_cases = [b"A" * 15 + b"\x00", b"A" * 15 + b"\x11", b"A" * 14 + b"\x01\x02", b"A" * 17]
    rejected = 0
    for bad in bad_cases:
        try:
            modes.pkcs7_unpad(bad)
        except PaddingError:
            rejected += 1
    check(f"PKCS#7: отброшено {rejected} из {len(bad_cases)} некорректных дополнений",
          rejected == len(bad_cases))

    ok = True
    for L in range(100):
        key, iv, p = secrets.token_bytes(16), secrets.token_bytes(16), secrets.token_bytes(L)
        ok &= modes.ecb_decrypt(modes.ecb_encrypt(p, key), key) == p
        for seg in (16, 1):
            c = modes.cfb_encrypt(p, key, iv, seg)
            ok &= len(c) == L and modes.cfb_decrypt(c, key, iv, seg) == p
    check("Случайные сообщения 0..99 байт (ECB, CFB-128, CFB-8): D(E(P)) = P", ok)
    print("Самопроверка пройдена" if all(res) else "ВНИМАНИЕ: обнаружены ошибки")
    return all(res)


# ======================================================================
#                     ШИФРОВАНИЕ ТЕСТОВЫХ СТРОК И ПАДДИНГ
# ======================================================================
DEFAULT_TEXTS = ["Hello, AES!", "Вариант 15: ECB + CFB",
                 "Лабораторная работа №3. Блочный шифр AES-128."]


def demo_strings(texts=DEFAULT_TEXTS, key=DEFAULT_KEY, iv=DEFAULT_IV):
    title("ШИФРОВАНИЕ И РАСШИФРОВАНИЕ ТЕСТОВЫХ СТРОК (ECB и CFB)")
    print(f"K  = {key.hex()}\nIV = {iv.hex()}  (только для CFB)")
    for t in texts:
        p = t.encode("utf-8")
        c_ecb = modes.ecb_encrypt(p, key)
        c_cfb = modes.cfb_encrypt(p, key, iv)
        d_ecb = modes.ecb_decrypt(c_ecb, key)
        d_cfb = modes.cfb_decrypt(c_cfb, key, iv)
        print(f"\nP = «{t}» ({len(p)} байт в UTF-8)")
        print(f"  P (hex)   = {hx(p)}")
        print(f"  ECB: C    = {hx(c_ecb)}  ({len(c_ecb)} байт)")
        print(f"  ECB: D(C) = «{d_ecb.decode('utf-8')}» — {'совпадает' if d_ecb == p else 'НЕ СОВПАДАЕТ'}")
        print(f"  CFB: C    = {hx(c_cfb)}  ({len(c_cfb)} байт)")
        print(f"  CFB: D(C) = «{d_cfb.decode('utf-8')}» — {'совпадает' if d_cfb == p else 'НЕ СОВПАДАЕТ'}")


def demo_padding(key=DEFAULT_KEY, iv=DEFAULT_IV):
    title("ДОПОЛНЕНИЕ PKCS#7 (ECB) И ПОТОКОВЫЙ РЕЖИМ CFB БЕЗ ДОПОЛНЕНИЯ")
    print(f"{'L, байт':>9}{'L mod 16':>10}{'k':>4}{'|C| ECB':>9}{'|C| CFB':>9}  дополнение   D(E(P)) = P")
    for L in (0, 5, 15, 16, 17, 31, 32, 40):
        p = bytes(ord("a") + i % 26 for i in range(L))
        k = len(modes.pkcs7_pad(p)) - L
        c_ecb, c_cfb = modes.ecb_encrypt(p, key), modes.cfb_encrypt(p, key, iv)
        ok = modes.ecb_decrypt(c_ecb, key) == p and modes.cfb_decrypt(c_cfb, key, iv) == p
        print(f"{L:>9}{L % 16:>10}{k:>4}{len(c_ecb):>9}{len(c_cfb):>9}  {k:>2} x 0x{k:02x}"
              f"     {'да' if ok else 'НЕТ'}")
    for label, p in (("меньше 16 байт", b"Short msg"), ("ровно 16 байт", b"Exactly16bytes!!"),
                     ("больше 16 байт", b"More than sixteen bytes")):
        padded = modes.pkcs7_pad(p)
        c = modes.ecb_encrypt(p, key)
        print(f"\nСообщение {label}: «{p.decode()}», L = {len(p)}, k = {len(padded) - len(p)}")
        print(f"  M_pad      = {hx(padded)}")
        print(f"  ECB: C     = {hx(c)}")
        print(f"  D_K(C)     = {hx(modes.ecb_decrypt(c, key, padding=False))}")
        print(f"  unpad      = «{modes.ecb_decrypt(c, key).decode()}»")
        print(f"  CFB: C     = {hx(modes.cfb_encrypt(p, key, iv))}  (длина {len(p)}, без дополнения)")
    print("\nПроверка дополнения при расшифровании (ECB):")
    c = modes.ecb_encrypt(b"More than sixteen bytes", key)
    cases = (("неверный ключ", c, bytes(16)),
             ("испорчен последний байт C", c[:-1] + bytes([c[-1] ^ 0x80]), key),
             ("шифротекст укорочен до 31 байта", c[:-1], key))
    for label, data, k in cases:
        try:
            modes.ecb_decrypt(data, k)
            print(f"  {label}: дополнение случайно оказалось корректным")
        except ValueError as e:
            print(f"  {label}: отказ — {e}")


# ======================================================================
#                     СРАВНЕНИЕ РЕЖИМОВ НА ИЗОБРАЖЕНИИ (BMP)
# ======================================================================
def bmp_parse(data):
    """Смещение массива пикселей, ширина, высота и число бит на пиксель."""
    if data[:2] != b"BM":
        raise ValueError("файл не является BMP")
    off = int.from_bytes(data[10:14], "little")
    w = int.from_bytes(data[18:22], "little", signed=True)
    h = int.from_bytes(data[22:26], "little", signed=True)
    bpp = int.from_bytes(data[28:30], "little")
    if bpp not in (24, 32) or int.from_bytes(data[30:34], "little") not in (0, 3):
        raise ValueError("поддерживаются несжатые 24- и 32-битные BMP")
    return off, w, h, bpp


def bmp_build(img):
    """Массив H x W x 3 (RGB) -> байты 24-битного BMP (строки снизу вверх, BGR)."""
    h, w, _ = img.shape
    row = (w * 3 + 3) // 4 * 4
    body = bytearray()
    for y in range(h - 1, -1, -1):
        line = img[y, :, ::-1].tobytes()
        body += line + bytes(row - len(line))
    le = lambda v, n: int(v).to_bytes(n, "little")
    header = b"BM" + le(54 + len(body), 4) + bytes(4) + le(54, 4)
    info = (le(40, 4) + le(w, 4) + le(h, 4) + le(1, 2) + le(24, 2) + bytes(4)
            + le(len(body), 4) + le(2835, 4) + le(2835, 4) + bytes(8))
    return header + info + bytes(body)


def bmp_to_array(data):
    """Байты BMP -> массив H x W x 3 (RGB) для отображения."""
    import numpy as np
    off, w, h, bpp = bmp_parse(data)
    nb = bpp // 8
    row = (w * nb + 3) // 4 * 4
    raw = np.frombuffer(data[off:off + row * abs(h)].ljust(row * abs(h), b"\0"), dtype=np.uint8)
    img = raw.reshape(abs(h), row)[:, :w * nb].reshape(abs(h), w, nb)[:, :, 2::-1]
    return img[::-1] if h > 0 else img


def make_test_image(w=320, h=240):
    """Тестовое изображение с крупными однотонными областями (выраженные паттерны),
    цвета приводятся к палитре из 5 цветов."""
    import numpy as np
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    for i in range(6):
        ax.add_patch(plt.Rectangle((16 + i * 50, 10), 25, 70, color="#c0392b"))
    ax.text(w / 2, 112, "AES-128", ha="center", va="center", fontsize=30, weight="bold")
    ax.add_patch(plt.Rectangle((25, 142), 120, 85, color="#1f4e9c"))
    ax.add_patch(plt.Circle((240, 185), 45, color="#e0a000"))
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].astype(int)
    plt.close(fig)
    palette = np.array([[255, 255, 255], [192, 57, 43], [0, 0, 0], [31, 78, 156], [224, 160, 0]])
    dist = ((img[:, :, None, :] - palette[None, None]) ** 2).sum(-1)
    return palette[dist.argmin(-1)].astype(np.uint8)


def block_stats(data):
    """Число блоков, уникальных блоков, доля повторяющихся и максимальное число повторов."""
    blocks = modes.split_blocks(data[:len(data) // BLOCK_SIZE * BLOCK_SIZE])
    cnt = Counter(blocks)
    repeated = sum(v for v in cnt.values() if v > 1)
    return len(blocks), len(cnt), repeated / len(blocks), cnt.most_common(1)[0][1]


def demo_image(path=None, key=DEFAULT_KEY, iv=DEFAULT_IV, show=True):
    title("СРАВНЕНИЕ РЕЖИМОВ: ШИФРОВАНИЕ BMP-ИЗОБРАЖЕНИЯ В ECB И CFB")
    if path:
        with open(path, "rb") as f:
            data = f.read()
        name = os.path.splitext(os.path.basename(path))[0]
    else:
        data, name = bmp_build(make_test_image()), "pattern"
        with open(out_path("pattern.bmp"), "wb") as f:
            f.write(data)
    off, w, h, bpp = bmp_parse(data)
    head, pix = data[:off], data[off:]
    print(f"Изображение: {w} x {abs(h)}, {bpp} бит/пиксель, заголовок {off} байт, "
          f"данные {len(pix)} байт ({len(pix) / BLOCK_SIZE:.0f} блоков)")
    t0 = time.perf_counter()
    full = modes.ecb_encrypt(pix, key)
    t_ecb = time.perf_counter() - t0
    t0 = time.perf_counter()
    c_cfb = modes.cfb_encrypt(pix, key, iv)
    t_cfb = time.perf_counter() - t0
    ok = modes.ecb_decrypt(full, key) == pix and modes.cfb_decrypt(c_cfb, key, iv) == pix
    c_ecb = full[:len(pix)]
    for tag, body in (("ecb", c_ecb), ("cfb", c_cfb)):
        with open(out_path(f"{name}_{tag}.bmp"), "wb") as f:
            f.write(head + body)
    print("Заголовок BMP не шифруется, чтобы результат оставался изображением; для отображения\n"
          "блок дополнения ECB отбрасывается. Расшифрование обоих режимов: "
          + ("верно" if ok else "ОШИБКА"))
    print(f"\n{'Данные':<11}{'блоков':>8}{'уникальных':>12}{'повторяющихся':>17}{'макс. повторов':>16}")
    rows = []
    for label, d in (("исходные", pix), ("ECB", c_ecb), ("CFB", c_cfb)):
        n, u, rep, mx = block_stats(d)
        rows.append((label, n, u, rep, mx))
        print(f"{label:<11}{n:>8}{u:>12}{rep:>17.1%}{mx:>16}")
    print(f"\nВремя шифрования: ECB {t_ecb:.2f} с, CFB {t_cfb:.2f} с. Файлы сохранены в папку {OUT_DIR}")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, (lbl, d) in zip(axes, (("Исходное изображение", data), ("Режим ECB", head + c_ecb),
                                   ("Режим CFB", head + c_cfb))):
        ax.imshow(bmp_to_array(d), interpolation="nearest")
        ax.set_title(lbl)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path("ecb_vs_cfb.png"), dpi=110)
    if show:
        plt.show()
    plt.close(fig)
    return rows


# ======================================================================
#           ИССЛЕДОВАНИЕ РАСПРОСТРАНЕНИЯ ОШИБКИ (фокус варианта 15)
# ======================================================================
RESEARCH_MODES = (("ECB", 0), ("CFB-128", 16), ("CFB-8", 1))     # (режим, сегмент s)
ERR_TEXT = b"".join(f"[Block {i:02d}] text!".encode() for i in range(8))   # 8 блоков


def r_encrypt(mode, p, key, iv):
    seg = dict(RESEARCH_MODES)[mode]
    return modes.ecb_encrypt(p, key, padding=False) if seg == 0 else modes.cfb_encrypt(p, key, iv, seg)


def r_decrypt(mode, c, key, iv):
    seg = dict(RESEARCH_MODES)[mode]
    return modes.ecb_decrypt(c, key, padding=False) if seg == 0 else modes.cfb_decrypt(c, key, iv, seg)


def bit_errors(a, b):
    """Число отличающихся бит в каждом байте."""
    return [bin(x ^ y).count("1") for x, y in zip(a, b)]


def damage(prof, pos):
    bad = [i for i, v in enumerate(prof) if v]
    return {"bytes": len(bad), "bits": sum(prof), "bad": bad,
            "blocks": sorted({i // BLOCK_SIZE for i in bad}),
            "tail": max(bad[-1] - pos, 0) if bad else 0}


def marks(n, positions, ch="^"):
    line = [" "] * n
    for p in positions:
        line[p] = ch
    return "".join(line).rstrip()


def error_demo(pos, err, key=DEFAULT_KEY, iv=DEFAULT_IV):
    p = ERR_TEXT
    print(f"Открытый текст ({len(p)} байт, {len(p) // BLOCK_SIZE} блоков):\n  P  = {show_text(p)}")
    print(f"Порча байта шифротекста № {pos} (нумерация с 0): блок {pos // BLOCK_SIZE + 1}, "
          f"байт {pos % BLOCK_SIZE} внутри блока; C[{pos}] ^= 0x{err:02x}")
    profiles = {}
    for mode, _ in RESEARCH_MODES:
        c = bytearray(r_encrypt(mode, p, key, iv))
        c[pos] ^= err
        d = r_decrypt(mode, bytes(c), key, iv)
        prof = bit_errors(p, d)
        s = damage(prof, pos)
        profiles[mode] = prof
        per_block = [sum(prof[i:i + BLOCK_SIZE]) for i in range(0, len(p), BLOCK_SIZE)]
        print(f"\n{mode}:\n  P' = {show_text(d)}\n       {marks(len(p), s['bad'])}")
        print(f"  искажено бит по блокам 1..{len(per_block)}: {per_block}")
        print(f"  искажено байт: {s['bytes']}, бит: {s['bits']}; позиции {s['bad'][0]}..{s['bad'][-1]}; "
              f"блоки: {[b + 1 for b in s['blocks']]}")
        e = d[pos] ^ p[pos]
        print(f"  в позиции {pos}: P'⊕P = 0x{e:02x} — "
              + ("совпадает с вектором ошибки" if e == err else "случайное искажение"))
        print(f"  после испорченного байта искажено ещё {s['tail']} байт, "
              f"с байта {s['bad'][-1] + 1} текст снова верный")
    return profiles


def loss_demo(pos, key=DEFAULT_KEY, iv=DEFAULT_IV):
    p = ERR_TEXT
    b0 = pos // BLOCK_SIZE * BLOCK_SIZE
    profiles = {}
    for what, cut in ((f"потеря байта № {pos}", (pos, pos + 1)),
                      (f"потеря блока {b0 // BLOCK_SIZE + 1} (16 байт)", (b0, b0 + BLOCK_SIZE))):
        print(f"\nРассинхронизация — {what} шифротекста:")
        for mode, _ in RESEARCH_MODES:
            c = r_encrypt(mode, p, key, iv)
            c2, expected = c[:cut[0]] + c[cut[1]:], p[:cut[0]] + p[cut[1]:]
            try:
                d = r_decrypt(mode, c2, key, iv)
            except ValueError as e:
                print(f"  {mode:<8} расшифрование невозможно: {e}")
                continue
            prof = bit_errors(expected, d)
            bad = [i for i, v in enumerate(prof) if v]
            if cut[1] - cut[0] == 1:
                profiles[mode] = prof
            rest = len(expected) - cut[0]
            if not bad:
                verdict = "искажений нет, теряется только удалённый фрагмент"
            elif len(expected) - 1 - bad[-1] >= BLOCK_SIZE:
                verdict = (f"искажено {len(bad)} байт (позиции {bad[0]}..{bad[-1]}), "
                           f"синхронизация восстановлена с байта {bad[-1] + 1}")
            else:
                verdict = (f"искажено {len(bad)} из {rest} последующих байт, "
                           "синхронизация не восстанавливается")
            print(f"  {mode:<8} {verdict}")
            print(f"           P' = {show_text(d)}")
    return profiles


def error_statistics(trials=300, nblocks=16):
    L = nblocks * BLOCK_SIZE
    print(f"\nСтатистика: {trials} испытаний; случайные K, IV и сообщение {L} байт ({nblocks} блоков); "
          f"случайный байт 0..{L - 2 * BLOCK_SIZE - 1} и случайный вектор ошибки 1..255")
    acc = {m: {"bytes": [], "bits": [], "blocks": [], "tail": [], "exact": 0} for m, _ in RESEARCH_MODES}
    for _ in range(trials):
        key, iv, p = secrets.token_bytes(16), secrets.token_bytes(16), secrets.token_bytes(L)
        pos, err = RNG.randrange(L - 2 * BLOCK_SIZE), RNG.randrange(1, 256)
        for mode, _ in RESEARCH_MODES:
            c = bytearray(r_encrypt(mode, p, key, iv))
            c[pos] ^= err
            d = r_decrypt(mode, bytes(c), key, iv)
            s = damage(bit_errors(p, d), pos)
            a = acc[mode]
            for name in ("bytes", "bits", "tail"):
                a[name].append(s[name])
            a["blocks"].append(len(s["blocks"]))
            a["exact"] += (d[pos] ^ p[pos]) == err
    hdr = (f"{'Режим':<9}{'байт ср.':>10}{'мин':>5}{'макс':>6}{'бит ср.':>10}{'блоков':>9}"
           f"{'хвост ср.':>11}{'макс':>6}{'P′⊕P=e':>9}")
    print(hdr + "\n" + "-" * len(hdr))
    rows = []
    for mode, a in acc.items():
        n = len(a["bytes"])
        row = (mode, sum(a["bytes"]) / n, min(a["bytes"]), max(a["bytes"]), sum(a["bits"]) / n,
               sum(a["blocks"]) / n, sum(a["tail"]) / n, max(a["tail"]), a["exact"] / n)
        rows.append(row)
        print(f"{row[0]:<9}{row[1]:>10.2f}{row[2]:>5}{row[3]:>6}{row[4]:>10.2f}{row[5]:>9.2f}"
              f"{row[6]:>11.2f}{row[7]:>6}{row[8]:>9.1%}")
    print("байт/бит — искажено в расшифрованном тексте; хвост — сколько байт после испорченного\n"
          "ещё искажено (задержка восстановления); P′⊕P=e — доля случаев, когда в позиции\n"
          "ошибки открытый текст искажён ровно на вектор ошибки e")
    return rows


def error_figure(corr, loss, pos, show=True):
    import matplotlib.pyplot as plt
    n = len(ERR_TEXT)
    fig, axes = plt.subplots(3, 2, figsize=(13, 7.2), sharex=True, sharey=True)
    for row, (mode, _) in enumerate(RESEARCH_MODES):
        for col, (prof, what) in enumerate(((corr.get(mode), f"порча байта C[{pos}]"),
                                            (loss.get(mode), f"потеря байта C[{pos}]"))):
            ax = axes[row][col]
            for b in range(0, n + 1, BLOCK_SIZE):
                ax.axvline(b - 0.5, color="grey", lw=0.6, ls="--")
            ax.axvline(pos, color="red", lw=1)
            if prof is None:
                ax.text(n / 2, 4, "расшифрование невозможно:\nдлина не кратна 16 байтам",
                        ha="center", va="center")
            else:
                ax.bar(range(len(prof)), prof, width=1.0, color="tab:blue" if col == 0 else "tab:orange")
            ax.set_title(f"{mode}: {what}", fontsize=10)
            ax.set_ylim(0, 8.5)
            if col == 0:
                ax.set_ylabel("искажено бит")
            if row == 2:
                ax.set_xlabel("номер байта расшифрованного текста (пунктир — границы блоков)")
    fig.tight_layout()
    fig.savefig(out_path("error_propagation.png"), dpi=110)
    if show:
        plt.show()
    plt.close(fig)


def error_research(pos=37, err=0x01, trials=300, show=True):
    title("ИССЛЕДОВАНИЕ РАСПРОСТРАНЕНИЯ ОШИБКИ В РЕЖИМАХ ECB И CFB")
    print("Для чистоты сравнения длина сообщений кратна 16 байтам, дополнение не применяется.\n"
          "Кроме CFB-128 (s = 128 бит) для сравнения показан CFB-8 (s = 8 бит).")
    corr = error_demo(pos, err)
    loss = loss_demo(pos)
    rows = error_statistics(trials)
    print("\nИтог: ECB — ошибка не выходит за пределы своего блока (задержка 0 блоков), но\n"
          "блок искажается целиком (~64 бита). CFB-128 — в текущем блоке искажается ровно\n"
          "испорченный байт, следующий блок — целиком, затем восстановление (задержка 1 блок).\n"
          "CFB-8 — испорченный байт и 16 следующих байт (задержка n/s = 16 сегментов).")
    error_figure(corr, loss, pos, show)
    return corr, loss, rows


# ======================================================================
#                     ШИФРОВАНИЕ ФАЙЛА
# ======================================================================
def file_mode():
    path = input("Путь к файлу: ").strip().strip('"')
    act = input("1 — зашифровать, 2 — расшифровать [1]: ").strip() or "1"
    mode = input("Режим ECB или CFB [CFB]: ").strip().upper() or "CFB"
    if mode not in ("ECB", "CFB"):
        raise ValueError("режим должен быть ECB или CFB")
    key = ask_bytes("Ключ K", DEFAULT_KEY)
    iv = ask_bytes("IV", DEFAULT_IV) if mode == "CFB" else None
    with open(path, "rb") as f:
        data = f.read()
    t0 = time.perf_counter()
    if act == "1":
        res, out = modes.encrypt(mode, data, key, iv), f"{path}.{mode.lower()}.enc"
    else:
        res, out = modes.decrypt(mode, data, key, iv), f"{path}.dec"
    dt = time.perf_counter() - t0
    with open(out, "wb") as f:
        f.write(res)
    print(f"{len(data)} -> {len(res)} байт за {dt:.2f} с ({len(data) / 1024 / max(dt, 1e-9):.1f} КБ/с), "
          f"результат: {out}")


# ======================================================================
def main():
    while True:
        print(f"\nМЕНЮ (лабораторная работа №3, вариант {VARIANT}: AES-128, ECB + CFB)\n"
              " 1 — Самопроверка (FIPS-197, NIST SP 800-38A, PKCS#7)\n"
              " 2 — Шифрование и расшифрование строк\n"
              " 3 — Дополнение PKCS#7 (L < 16, L = 16, L > 16)\n"
              " 4 — Сравнение ECB и CFB на BMP-изображении\n"
              " 5 — Исследование распространения ошибки (порча и потеря байта)\n"
              " 6 — Зашифровать / расшифровать файл\n"
              " 0 — Выполнить всё и выйти")
        ch = input("Выбор: ").strip()
        try:
            if ch == "1":
                self_test()
            elif ch == "2":
                s = input("Текст (Enter — тестовые строки): ")
                key = ask_bytes("Ключ K", DEFAULT_KEY)
                iv = ask_bytes("IV", DEFAULT_IV)
                demo_strings([s] if s else DEFAULT_TEXTS, key, iv)
            elif ch == "3":
                demo_padding()
            elif ch == "4":
                path = input("Путь к BMP (Enter — сгенерировать тестовое изображение): ")
                demo_image(path.strip().strip('"') or None)
            elif ch == "5":
                pos = ask_int("Номер искажаемого байта шифротекста", 37, 0, len(ERR_TEXT) - 1)
                err = int(input("Вектор ошибки e (hex, 01..ff) [01]: ").strip() or "01", 16)
                if not 1 <= err <= 255:
                    raise ValueError("вектор ошибки должен быть от 01 до ff")
                error_research(pos, err, ask_int("Число испытаний для статистики", 300, 10))
            elif ch == "6":
                file_mode()
            elif ch == "0":
                self_test()
                demo_strings()
                demo_padding()
                demo_image()
                error_research()
                break
        except (ValueError, OSError) as e:
            print("Ошибка:", e)


if __name__ == "__main__":
    main()
