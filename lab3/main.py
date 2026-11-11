"""
Модуль main.py
Тестирование алгоритма по стандарту NIST FIPS 197,
проверка работы PKCS#7 и сравнительный анализ режимов ECB vs CBC.
"""

import os
from aes128 import encrypt_block, decrypt_block
from cipher_modes import (
    pkcs7_pad, pkcs7_unpad,
    encrypt_ecb, decrypt_ecb,
    encrypt_cbc, decrypt_cbc
)


def test_fips_197_vector():
    print("=" * 60)
    print("ТЕСТ 1: Верификация AES-128 по эталонному вектору NIST FIPS 197")
    print("=" * 60)
    
    key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
    pt = bytes.fromhex("3243f6a8885a308d313198a2e0370734")
    expected_ct = bytes.fromhex("3925841d02dc09fbdc118597196a0b32")

    ct = encrypt_block(pt, key)
    decrypted = decrypt_block(ct, key)

    print(f"Ключ:        {key.hex()}")
    print(f"Открытый текст: {pt.hex()}")
    print(f"Ожидаемый CT:   {expected_ct.hex()}")
    print(f"Полученный CT:  {ct.hex()}")
    
    assert ct == expected_ct, "Ошибка зашифрования блока AES!"
    assert decrypted == pt, "Ошибка расшифрования блока AES!"
    print("=> РЕЗУЛЬТАТ: Эталонный тест FIPS 197 пройден успешно!\n")


def test_padding():
    print("=" * 60)
    print("ТЕСТ 2: Демонстрация работы дополнения PKCS#7")
    print("=" * 60)

    test_cases = [
        ("Меньше 16 байт (11 байт)", b"Hello World"),
        ("Ровно 16 байт", b"0123456789ABCDEF"),
        ("Больше 16 байт (21 байт)", b"Cryptography course 2026!"),
    ]

    for desc, msg in test_cases:
        padded = pkcs7_pad(msg)
        unpadded = pkcs7_unpad(padded)
        pad_len = padded[-1]
        print(f"Сценарий: {desc}")
        print(f"  Исходная длина: {len(msg)} байт")
        print(f"  Длина с паддингом: {len(padded)} байт (добавлено {pad_len} байт)")
        print(f"  Хвост паддинга: {padded[-pad_len:].hex()}")
        assert unpadded == msg, "Ошибка снятия паддинга!"
        print("  => Успешно наложен и снят\n")


def test_modes_comparison():
    print("=" * 60)
    print("ТЕСТ 3: Сравнение устойчивости к паттернам (ECB vs CBC)")
    print("=" * 60)

    key = os.urandom(16)
    iv = os.urandom(16)

    # 4 абсолютно одинаковых блока открытого текста по 16 байт
    repeated_block = b"SECRET_BLOCK_16B"
    plain_data = repeated_block * 4

    print(f"Открытый текст содержит 4 идентичных блока:\n  {plain_data}\n")

    # Шифрование в ECB
    ct_ecb = encrypt_ecb(plain_data, key)
    # Шифрование в CBC
    ct_cbc = encrypt_cbc(plain_data, key, iv)

    print("Шифротекст ECB (разбивка по 16 байт):")
    for i in range(0, len(ct_ecb), 16):
        print(f"  Блок {i//16}: {ct_ecb[i:i+16].hex()}")

    print("\nШифротекст CBC (разбивка по 16 байт):")
    for i in range(0, len(ct_cbc), 16):
        print(f"  Блок {i//16}: {ct_cbc[i:i+16].hex()}")

    # Проверка утечки паттерна
    ecb_blocks = [ct_ecb[i:i+16] for i in range(0, len(plain_data), 16)]
    cbc_blocks = [ct_cbc[i:i+16] for i in range(0, len(plain_data), 16)]

    is_ecb_pattern = len(set(ecb_blocks)) == 1
    is_cbc_pattern = len(set(cbc_blocks)) == 1

    print("\nАнализ статистической избыточности:")
    print(f"  Одинаковы ли блоки в ECB: {is_ecb_pattern} (Паттерны видны напрямую!)")
    print(f"  Одинаковы ли блоки в CBC: {is_cbc_pattern} (Паттерны полностью скрыты благодаря сцеплению)")

    # Проверка обратимости
    assert decrypt_ecb(ct_ecb, key) == plain_data
    assert decrypt_cbc(ct_cbc, key, iv) == plain_data
    print("\n=> Обратимость обоих режимов подтверждена: расшифрованные данные совпадают с оригиналом.")


if __name__ == "__main__":
    test_fips_197_vector()
    test_padding()
    test_modes_comparison()