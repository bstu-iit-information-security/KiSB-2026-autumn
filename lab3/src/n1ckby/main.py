import argparse
from pathlib import Path
from secrets import token_bytes

from modes import decrypt_cbc, decrypt_ecb, encrypt_cbc, encrypt_ecb, pad


def show_message(text: str, key: bytes) -> None:
    data = text.encode("utf-8")
    iv = token_bytes(16)
    ecb = encrypt_ecb(data, key)
    cbc = encrypt_cbc(data, key, iv)
    print(f"Текст: {text!r}")
    print(f"Длина UTF-8: {len(data)} байт")
    print(f"Добавлено PKCS#7: {len(pad(data)) - len(data)} байт")
    print(f"ECB ({len(ecb)} байт): {ecb.hex()}")
    print(f"CBC ({len(cbc)} байт): {cbc.hex()}")
    print(f"IV: {iv.hex()}")
    print(f"После ECB: {decrypt_ecb(ecb, key).decode('utf-8')!r}")
    print(f"После CBC: {decrypt_cbc(cbc, key, iv).decode('utf-8')!r}")
    print()


def demonstrate_patterns(key: bytes, directory: Path) -> None:
    data = b"0123456789ABCDEF" * 8
    iv = token_bytes(16)
    ecb = encrypt_ecb(data, key)
    cbc = encrypt_cbc(data, key, iv)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "patterns.bin").write_bytes(data)
    (directory / "patterns_ecb.bin").write_bytes(ecb)
    (directory / "patterns_cbc.bin").write_bytes(cbc)
    (directory / "patterns_iv.hex").write_text(iv.hex(), encoding="utf-8")

    print("СРАВНЕНИЕ ПАТТЕРНОВ: 8 одинаковых исходных блоков")
    print(f"IV: {iv.hex()}")
    print(" № | ECB                              | CBC")
    for number, offset in enumerate(range(0, len(data), 16), start=1):
        print(f"{number:2} | {ecb[offset:offset + 16].hex()} | "
              f"{cbc[offset:offset + 16].hex()}")
    print("Девятый блок — дополнение PKCS#7, в таблице не показан.")
    for name, encrypted in (("ECB", ecb), ("CBC", cbc)):
        blocks = [encrypted[i:i + 16] for i in range(0, len(data), 16)]
        print(f"{name}: уникальных блоков данных {len(set(blocks))} из 8")
    assert decrypt_ecb(ecb, key) == data
    assert decrypt_cbc(cbc, key, iv) == data
    print("Обратное восстановление обоих файлов: OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="ЛР3, вариант 1: AES-128, ECB и CBC")
    parser.add_argument("--demo", action="store_true", help="Примеры для отчёта")
    arguments = parser.parse_args()

    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    print("ЛР3. Вариант 1. AES-128 / ECB / CBC / PKCS#7")
    print(f"Учебный ключ: {key.hex()}\n")
    if arguments.demo:
        for text in ("Hello", "1234567890ABCDEF", "1234567890ABCDEFG", "Привет, мир!", ""):
            show_message(text, key)
        demonstrate_patterns(key, Path(__file__).resolve().parent / "results")
    else:
        try:
            text = input("Введите текст: ")
            key_hex = input("Ключ: 32 hex-символа (Enter — учебный ключ): ").strip()
            if key_hex:
                key = bytes.fromhex(key_hex)
            show_message(text, key)
        except ValueError as error:
            print(f"Ошибка: {error}")


if __name__ == "__main__":
    main()
