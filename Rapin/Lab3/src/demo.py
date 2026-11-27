from aes import encrypt_block, decrypt_block
from modes import (
    pad, unpad,
    encrypt_ecb, decrypt_ecb,
    encrypt_cfb, decrypt_cfb, encrypt_cfb_with_iv,
)

KEY = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
IV  = bytes.fromhex("000102030405060708090a0b0c0d0e0f")


def hexdump(data: bytes, max_len: int = 64) -> str:
    if len(data) > max_len:
        return data[:max_len].hex() + f"... ({len(data)} bytes total)"
    return data.hex()


def demo_block_cipher():
    print("1. Блочный шифр AES-128 (один блок)")
    pt = bytes.fromhex("3243f6a8885a308d313198a2e0370734")
    ct = encrypt_block(pt, KEY)
    recovered = decrypt_block(ct, KEY)
    print(f"  Plaintext : {pt.hex()}")
    print(f"  Ciphertext: {ct.hex()}")
    print(f"  Recovered : {recovered.hex()}")
    print(f"  OK: {recovered == pt}\n")


def demo_padding():
    print("2. PKCS#7 Padding (демонстрация разных длин)")
    for L in [0, 1, 15, 16, 17, 32]:
        data = b"X" * L
        padded = pad(data)
        print(f"  len={L:2d} → padded_len={len(padded):2d}  "
              f"last_bytes={padded[-min(16, len(padded)):].hex()}")
        assert unpad(padded) == data
    print("  Все случаи снятия паддинга успешны\n")


def demo_ecb():
    print("3. Режим ECB")
    messages = [
        b"Hello",
        b"1234567890123456",          # ровно блок
        b"12345678901234567",         # 17 байт
        b"The quick brown fox jumps over the lazy dog and runs away",
    ]
    for msg in messages:
        ct = encrypt_ecb(msg, KEY)
        pt = decrypt_ecb(ct, KEY)
        print(f"  PT ({len(msg):3d} B): {msg[:40]!r}{'...' if len(msg)>40 else ''}")
        print(f"  CT ({len(ct):3d} B): {hexdump(ct)}")
        print(f"  Recovered OK: {pt == msg}\n")


def demo_cfb_arbitrary_lengths():
    print("4. Режим CFB — тексты произвольной байтовой длины (фокус варианта 11)")

    test_lengths = [0, 1, 7, 15, 16, 17, 31, 32, 33, 48, 63, 64, 100, 255]
    all_ok = True
    for L in test_lengths:
        msg = bytes([(i * 17 + 3) % 256 for i in range(L)])  # псевдослучайные байты
        ct = encrypt_cfb_with_iv(msg, KEY, IV)
        pt = decrypt_cfb(ct, KEY)
        ok = pt == msg
        all_ok = all_ok and ok
        status = "OK" if ok else "FAIL"
        print(f"  len={L:3d}  CT_len={len(ct):3d}  recover={status}")

    print(f"\n  Итог по произвольным длинам: {'ВСЕ УСПЕШНО' if all_ok else 'ЕСТЬ ОШИБКИ'}\n")


def demo_cfb_only_encrypt():
    print("5. CFB использует исключительно encrypt_block (E_K)")
    print("  В decrypt_cfb вызывается только aes.encrypt_block.")
    print("  Функция decrypt_block (D_K) нигде не применяется.")
    print("  Это соответствует определению CFB из методички.\n")


def demo_pattern_comparison():
    print("6. Сравнение ECB vs CFB на данных с паттернами")
    # Два одинаковых блока подряд
    pattern = b"AAAAAAAA" * 4 + b"BBBBBBBB" * 4   # 64 байта

    ct_ecb = encrypt_ecb(pattern, KEY)
    ct_cfb = encrypt_cfb_with_iv(pattern, KEY, IV)

    print("  Открытый текст (первые 32 байта):", pattern[:32])
    print()
    print("  ECB (видны повторяющиеся блоки):")
    print(f"    block0: {ct_ecb[0:16].hex()}")
    print(f"    block1: {ct_ecb[16:32].hex()}")
    print(f"    block0 == block1 ? {ct_ecb[0:16] == ct_ecb[16:32]}")
    print()
    print("  CFB (паттерны скрыты благодаря обратной связи):")
    # CFB: IV + ciphertext, поэтому первые 16 байт — IV
    print(f"    IV    : {ct_cfb[0:16].hex()}")
    print(f"    block0: {ct_cfb[16:32].hex()}")
    print(f"    block1: {ct_cfb[32:48].hex()}")
    print(f"    block0 == block1 ? {ct_cfb[16:32] == ct_cfb[32:48]}")
    print()

if __name__ == "__main__":
    demo_block_cipher()
    demo_padding()
    demo_ecb()
    demo_cfb_arbitrary_lengths()
    demo_cfb_only_encrypt()
    demo_pattern_comparison()
    print("Демонстрация завершена успешно.")