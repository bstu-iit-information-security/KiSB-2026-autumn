from secrets import token_bytes

from belt import H, encrypt_block
from modes import pad, ecb_encrypt, ecb_decrypt, ctr_crypt, ctr_parallel


def demonstrate():
    key = H[128:160]
    iv = bytes.fromhex("0011223344556677")
    expected = "69cca1c93557c9e3d66bc3e0fa88fa6e"
    actual = encrypt_block(H[:16], key).hex()
    print("БелТ, вариант 6. Контрольный пример:", actual)
    assert actual == expected
    print("Контрольный пример: OK")

    for text in ("Привет, БелТ!", "", "Hello, world!"):
        data = text.encode("utf-8")
        ecb = ecb_encrypt(data, key)
        ctr = ctr_crypt(data, key, iv)
        assert ecb_decrypt(ecb, key) == data
        assert ctr_crypt(ctr, key, iv) == data
        print(f"\nТекст: {text!r}; байт UTF-8: {len(data)}")
        print("ECB:", ecb.hex())
        print("CTR:", ctr.hex())
        print("Обратное преобразование обоих режимов: OK")

    print("\nДополнение PKCS#7:")
    for size in (5, 16, 21):
        data = b"A" * size
        padded = pad(data)
        print(f"{size} байт -> {len(padded)} байт; "
              f"дополнение: {padded[size:].hex()}")

    data = b"0123456789ABCDEF" * 4
    print("\nЧетыре одинаковых исходных блока:")
    for name, encrypted in (("ECB", ecb_encrypt(data, key)),
                            ("CTR", ctr_crypt(data, key, iv))):
        print(name)
        for offset in range(0, len(data), 16):
            print(f"  Блок {offset // 16 + 1}: {encrypted[offset:offset + 16].hex()}")

    parallel = ctr_parallel(data + b"tail", key, iv)
    assert parallel == ctr_crypt(data + b"tail", key, iv)
    print("\nПараллельный CTR совпадает с последовательным: OK")


def main():
    demonstrate()
    try:
        text = input("\nВведите свой текст (Enter — завершить): ")
    except EOFError:
        return
    if not text:
        return
    key = token_bytes(32)
    iv = token_bytes(8)
    data = text.encode("utf-8")
    print("Ключ (hex):", key.hex())
    print("IV (hex):", iv.hex())
    ecb = ecb_encrypt(data, key)
    ctr = ctr_crypt(data, key, iv)
    print("ECB (hex):", ecb.hex())
    print("После расшифрования ECB:", ecb_decrypt(ecb, key).decode("utf-8"))
    print("CTR (hex):", ctr.hex())
    print("После расшифрования CTR:", ctr_crypt(ctr, key, iv).decode("utf-8"))


if __name__ == "__main__":
    main()
