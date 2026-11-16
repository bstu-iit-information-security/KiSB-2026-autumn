import struct

import matplotlib.pyplot as plt

from aes128 import decrypt_block, encrypt_block
from modes import (
    DecryptionError,
    cbc_decrypt,
    cbc_encrypt,
    cbc_open,
    cbc_seal,
    cmac,
    ecb_decrypt,
    ecb_encrypt,
    pad,
    split_blocks,
    unpad,
)

KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
MAC_KEY = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
IV = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff")
IMAGE_SIZE = 128
MESSAGE = "Привет, мир!"


def emit(text=""):
    print(text)


def status(flag):
    return "да" if flag else "нет"


def check_standards():
    block = bytes.fromhex("00112233445566778899aabbccddeeff")
    expected = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    emit(f"AES-128 (FIPS-197), зашифрование: {status(encrypt_block(block, KEY) == expected)}")
    emit(f"AES-128 (FIPS-197), расшифрование: {status(decrypt_block(expected, KEY) == block)}")
    emit(f"AES-CMAC (RFC 4493): {status(cmac(MAC_KEY, b'') == bytes.fromhex('bb1d6929e95937287fa37d129b756746'))}")


def check_strings():
    data = MESSAGE.encode("utf-8")
    ecb = ecb_encrypt(data, KEY)
    cbc = cbc_encrypt(data, KEY, IV)
    emit(f"Сообщение: {MESSAGE} ({len(data)} байт)")
    emit(f"ECB: {ecb.hex()}")
    emit(f"CBC: {cbc.hex()}")
    emit(f"ECB расшифровано верно: {status(ecb_decrypt(ecb, KEY) == data)}")
    emit(f"CBC расшифровано верно: {status(cbc_decrypt(cbc, KEY, IV) == data)}")


def check_padding():
    for length in (15, 16, 17):
        data = bytes(range(65, 65 + length))
        padded = pad(data)
        count = padded[-1]
        ecb = ecb_encrypt(data, KEY)
        cbc = cbc_encrypt(data, KEY, IV)
        emit(
            f"{length} байт: +{count} (0x{count:02x}), шифротекст {len(ecb)} байт, "
            f"снятие: {status(unpad(padded) == data)}, "
            f"ECB: {status(ecb_decrypt(ecb, KEY) == data)}, "
            f"CBC: {status(cbc_decrypt(cbc, KEY, IV) == data)}"
        )


def describe_unpad(data):
    try:
        unpad(data)
        return "принято"
    except DecryptionError as error:
        return f"{type(error).__name__}: {error}"


def check_oracle_protection():
    head = bytes(range(1, 13))
    cases = (
        ("корректное 04 04 04 04", head + b"\x04" * 4),
        ("последний байт 00", head + b"\x01\x02\x03\x00"),
        ("последний байт 11", head + b"\x01\x02\x03\x11"),
        ("нарушена цепочка 03", head + b"\x01\x09\x03\x03"),
        ("длина не кратна 16", head),
    )
    for title, data in cases:
        emit(f"Паддинг, {title} -> {describe_unpad(data)}")
    sealed = cbc_seal(MESSAGE.encode("utf-8"), KEY, MAC_KEY, IV)
    broken_body = sealed[:20] + bytes([sealed[20] ^ 1]) + sealed[21:]
    broken_tag = sealed[:-1] + bytes([sealed[-1] ^ 1])
    emit(f"CMAC, исходное сообщение расшифровано: {status(cbc_open(sealed, KEY, MAC_KEY) == MESSAGE.encode('utf-8'))}")
    for title, data in (("изменён бит шифротекста", broken_body), ("изменён бит тега", broken_tag)):
        try:
            cbc_open(data, KEY, MAC_KEY)
            result = "принято"
        except DecryptionError as error:
            result = f"{type(error).__name__}: {error}"
        emit(f"CMAC, {title} -> {result}")


def build_image(size):
    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            color = (235, 235, 235, 255)
            if (x - size // 2) ** 2 + (y - size // 2) ** 2 < (size * 0.38) ** 2:
                color = (40, 40, 220, 255)
            if size * 0.38 < x < size * 0.62 and size * 0.38 < y < size * 0.62:
                color = (200, 80, 20, 255)
            if y > size * 0.88:
                color = (60, 160, 60, 255)
            pixels += bytes(color)
    return bytes(pixels)


def write_bmp(path, size, pixels):
    header = b"BM" + struct.pack("<IHHI", 54 + len(pixels), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, size, -size, 1, 32, 0, len(pixels), 2835, 2835, 0, 0)
    with open(path, "wb") as file:
        file.write(header + info + pixels)


def to_rows(pixels, size):
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            offset = (y * size + x) * 4
            row.append((pixels[offset + 2], pixels[offset + 1], pixels[offset]))
        rows.append(row)
    return rows


def repeated_blocks(data):
    blocks = split_blocks(data)
    return len(blocks) - len(set(blocks)), len(blocks)


def compare_modes():
    pixels = build_image(IMAGE_SIZE)
    ecb = ecb_encrypt(pixels, KEY)[:len(pixels)]
    cbc = cbc_encrypt(pixels, KEY, IV)[:len(pixels)]
    write_bmp("original.bmp", IMAGE_SIZE, pixels)
    write_bmp("ecb.bmp", IMAGE_SIZE, ecb)
    write_bmp("cbc.bmp", IMAGE_SIZE, cbc)
    for name, data in (("Исходные данные", pixels), ("ECB", ecb), ("CBC", cbc)):
        repeated, total = repeated_blocks(data)
        emit(f"{name}: повторяющихся блоков {repeated} из {total}")
    figure, axes = plt.subplots(1, 3, figsize=(12, 4.4))
    for axis, title, data in zip(axes, ("Исходное изображение", "Режим ECB", "Режим CBC"), (pixels, ecb, cbc)):
        axis.imshow(to_rows(data, IMAGE_SIZE))
        axis.set_title(title)
        axis.axis("off")
    figure.tight_layout()
    plt.show(block=False)


def main():
    emit("Проверка шифра и MAC по стандартным векторам")
    check_standards()
    emit()
    emit("Шифрование тестовой строки")
    check_strings()
    emit()
    emit("Дополнение PKCS#7")
    check_padding()
    emit()
    emit("Защита от Padding Oracle")
    check_oracle_protection()
    emit()
    emit("Сравнение режимов на изображении 128x128, 32 бит на пиксель")
    compare_modes()
    plt.show()


if __name__ == "__main__":
    main()
