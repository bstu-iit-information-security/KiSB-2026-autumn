"""Лабораторная №3, вариант 11: AES-128 в режимах ECB и CFB-128."""
import argparse
import csv
import sys
from pathlib import Path

from modes import encrypt_ecb, decrypt_ecb, encrypt_cfb, decrypt_cfb, pkcs7_pad

# Постоянные значения нужны только для воспроизводимых учебных примеров.
DEMO_KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
DEMO_IV = bytes.fromhex("101112131415161718191a1b1c1d1e1f")


def demonstrate(save_results=False):
    """Показывает произвольную длину, паддинг и повторяющиеся блоки."""
    messages = [b"", b"Hello!", b"0123456789ABCDEF", b"Longer than 16 bytes!", "Привет, мир!".encode("utf-8")]
    rows = []
    print("AES-128, вариант 11. Учебные ключ и IV — фиксированные.")
    for message in messages:
        print("\nИсходные байты (hex):", message.hex() or "(пусто)")
        for name in ("ECB", "CFB"):
            if name == "ECB":
                encrypted = encrypt_ecb(message, DEMO_KEY)
                restored = decrypt_ecb(encrypted, DEMO_KEY)
            else:
                encrypted = encrypt_cfb(message, DEMO_KEY, DEMO_IV)
                restored = decrypt_cfb(encrypted, DEMO_KEY, DEMO_IV)
            print(f"{name}: длина {len(message)} -> {len(encrypted)} байт; шифротекст {encrypted.hex()}")
            print("Совпадает:", "да" if restored == message else "нет")
            rows.append([name, len(message), message.hex(), encrypted.hex(), restored == message])
        print("PKCS#7:", pkcs7_pad(message).hex())

    pattern = b"0123456789ABCDEF" * 4
    print("\nСравнение: четыре одинаковых открытых блока")
    for name, encrypted in (("ECB", encrypt_ecb(pattern, DEMO_KEY)),
                            ("CFB", encrypt_cfb(pattern, DEMO_KEY, DEMO_IV))):
        # У ECB есть дополнительный полный блок паддинга; сравниваются первые четыре.
        blocks = [encrypted[i:i + 16] for i in range(0, 64, 16)]
        print(name + ":")
        for index, block in enumerate(blocks, 1):
            print(f"  блок {index}: {block.hex()}")
            rows.append([name + " pattern", 16, pattern[:16].hex(), block.hex(), ""])
        print("  Различных блоков:", len(set(blocks)))

    if save_results:
        directory = Path(__file__).resolve().parent / "results" / "latest_run"
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "demonstration.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["mode", "plaintext_length", "plaintext_hex", "ciphertext_hex", "restored"])
            writer.writerows(rows)
        print("\nРезультаты сохранены:", directory / "demonstration.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", nargs="?", choices=["encrypt", "decrypt"],
                        help="без аргументов запускается демонстрация")
    parser.add_argument("mode", nargs="?", choices=["ecb", "cfb"])
    parser.add_argument("key", nargs="?", help="ключ AES-128: 32 шестнадцатеричных символа")
    parser.add_argument("data", nargs="?", help="сообщение или шифротекст в hex; пустая строка допустима")
    parser.add_argument("--iv", help="для CFB: 16 байт в hex")
    parser.add_argument("--save-results", action="store_true", help="сохранить результаты демонстрации в CSV")
    args = parser.parse_args()
    if args.operation is None:
        if args.mode is not None or args.key is not None or args.data is not None or args.iv:
            parser.error("укажите операцию encrypt или decrypt")
        demonstrate(args.save_results)
        return
    if args.save_results:
        parser.error("--save-results используется только с демонстрацией")
    if args.mode is None or args.key is None or args.data is None:
        parser.error("укажите режим, ключ и данные")
    if args.mode == "cfb" and args.iv is None:
        parser.error("режиму CFB нужен --iv")
    if args.mode == "ecb" and args.iv is not None:
        parser.error("режим ECB не использует IV")
    try:
        key = bytes.fromhex(args.key)
        data = bytes.fromhex(args.data)
        if args.mode == "ecb":
            result = encrypt_ecb(data, key) if args.operation == "encrypt" else decrypt_ecb(data, key)
        else:
            iv = bytes.fromhex(args.iv)
            result = encrypt_cfb(data, key, iv) if args.operation == "encrypt" else decrypt_cfb(data, key, iv)
        print(result.hex())
    except ValueError as error:
        print("Ошибка:", error, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
