"""ЛР №3, вариант 1: AES-128, режимы ECB/CBC и PKCS#7.
    
Запуск: uv run python main.py
Результаты: каталог out/.

ВНИМАНИЕ: реализация AES здесь учебная. Для реальных данных используйте
проверенную библиотеку и аутентифицированный режим, например AES-GCM.
"""

from pathlib import Path
import secrets
import struct


BLOCK_SIZE = 16


def _xtime(value: int) -> int:
    """Умножение на x в GF(2^8)."""
    return ((value << 1) ^ 0x1B) & 0xFF if value & 0x80 else value << 1


def _gf_mul(a: int, b: int) -> int:
    """Умножение байтов в GF(2^8)."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        a = _xtime(a)
        b >>= 1
    return result


def _make_sbox() -> tuple[int, ...]:
    """Построение S-box AES по определению из FIPS-197."""
    def rotate_left(value: int, shift: int) -> int:
        return ((value << shift) | (value >> (8 - shift))) & 0xFF

    sbox = [0] * 256
    p = q = 1
    while True:
        p ^= _xtime(p)
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09

        sbox[p] = (
            q
            ^ rotate_left(q, 1)
            ^ rotate_left(q, 2)
            ^ rotate_left(q, 3)
            ^ rotate_left(q, 4)
            ^ 0x63
        )
        if p == 1:
            break

    sbox[0] = 0x63
    return tuple(sbox)


_AES_SBOX = _make_sbox()
_AES_INV_SBOX_LIST = [0] * 256
for _index, _value in enumerate(_AES_SBOX):
    _AES_INV_SBOX_LIST[_value] = _index
_AES_INV_SBOX = tuple(_AES_INV_SBOX_LIST)
del _AES_INV_SBOX_LIST, _index, _value


class AES128:
    """Учебная реализация блочного шифра AES-128.

    Ключ передаётся один раз при создании объекта. В объекте хранятся
    раундовые ключи; исходный ключ отдельно не сохраняется.
    """

    KEY_SIZE = 16
    BLOCK_SIZE = 16

    def __init__(self, key: bytes) -> None:
        if not isinstance(key, bytes) or len(key) != self.KEY_SIZE:
            raise ValueError("Ключ AES-128 должен состоять ровно из 16 байт")
        self._round_keys = self._expand_key(key)

    @staticmethod
    def _expand_key(key: bytes) -> tuple[bytes, ...]:
        words = [list(key[i:i + 4]) for i in range(0, 16, 4)]
        round_constant = 1

        for index in range(4, 44):
            temp = words[index - 1].copy()
            if index % 4 == 0:
                temp = temp[1:] + temp[:1]  # RotWord
                temp = [_AES_SBOX[byte] for byte in temp]  # SubWord
                temp[0] ^= round_constant
                round_constant = _xtime(round_constant)

            words.append([
                left ^ right
                for left, right in zip(words[index - 4], temp)
            ])

        round_keys = []
        for round_index in range(11):
            round_key = bytes(
                byte
                for word in words[round_index * 4:round_index * 4 + 4]
                for byte in word
            )
            round_keys.append(round_key)
        return tuple(round_keys)

    @staticmethod
    def _add_round_key(state: list[int], round_key: bytes) -> list[int]:
        return [left ^ right for left, right in zip(state, round_key)]

    @staticmethod
    def _shift_rows(state: list[int]) -> list[int]:
        return [
            state[row + 4 * ((column + row) % 4)]
            for column in range(4)
            for row in range(4)
        ]

    @staticmethod
    def _inv_shift_rows(state: list[int]) -> list[int]:
        result = [0] * BLOCK_SIZE
        for column in range(4):
            for row in range(4):
                result[row + 4 * ((column + row) % 4)] = state[row + 4 * column]
        return result

    @staticmethod
    def _mix_columns(state: list[int]) -> list[int]:
        result = []
        for column in range(4):
            a0, a1, a2, a3 = state[column * 4:column * 4 + 4]
            result.extend((
                _xtime(a0) ^ (_xtime(a1) ^ a1) ^ a2 ^ a3,
                a0 ^ _xtime(a1) ^ (_xtime(a2) ^ a2) ^ a3,
                a0 ^ a1 ^ _xtime(a2) ^ (_xtime(a3) ^ a3),
                (_xtime(a0) ^ a0) ^ a1 ^ a2 ^ _xtime(a3),
            ))
        return result

    @staticmethod
    def _inv_mix_columns(state: list[int]) -> list[int]:
        result = []
        for column in range(4):
            a0, a1, a2, a3 = state[column * 4:column * 4 + 4]
            result.extend((
                _gf_mul(a0, 14) ^ _gf_mul(a1, 11) ^ _gf_mul(a2, 13) ^ _gf_mul(a3, 9),
                _gf_mul(a0, 9) ^ _gf_mul(a1, 14) ^ _gf_mul(a2, 11) ^ _gf_mul(a3, 13),
                _gf_mul(a0, 13) ^ _gf_mul(a1, 9) ^ _gf_mul(a2, 14) ^ _gf_mul(a3, 11),
                _gf_mul(a0, 11) ^ _gf_mul(a1, 13) ^ _gf_mul(a2, 9) ^ _gf_mul(a3, 14),
            ))
        return result

    def encrypt_block(self, plaintext_block: bytes) -> bytes:
        if len(plaintext_block) != self.BLOCK_SIZE:
            raise ValueError("AES принимает на вход блок ровно 16 байт")

        state = self._add_round_key(list(plaintext_block), self._round_keys[0])
        for round_index in range(1, 10):
            state = [_AES_SBOX[byte] for byte in state]
            state = self._shift_rows(state)
            state = self._mix_columns(state)
            state = self._add_round_key(state, self._round_keys[round_index])

        state = [_AES_SBOX[byte] for byte in state]
        state = self._shift_rows(state)
        state = self._add_round_key(state, self._round_keys[10])
        return bytes(state)

    def decrypt_block(self, ciphertext_block: bytes) -> bytes:
        if len(ciphertext_block) != self.BLOCK_SIZE:
            raise ValueError("AES принимает на вход блок ровно 16 байт")

        state = self._add_round_key(list(ciphertext_block), self._round_keys[10])
        for round_index in range(9, 0, -1):
            state = self._inv_shift_rows(state)
            state = [_AES_INV_SBOX[byte] for byte in state]
            state = self._add_round_key(state, self._round_keys[round_index])
            state = self._inv_mix_columns(state)

        state = self._inv_shift_rows(state)
        state = [_AES_INV_SBOX[byte] for byte in state]
        state = self._add_round_key(state, self._round_keys[0])
        return bytes(state)


class CipherModes:
    """PKCS#7, ECB и CBC поверх объекта AES128."""

    BLOCK_SIZE = BLOCK_SIZE

    @staticmethod
    def pad(data: bytes) -> bytes:
        padding_size = BLOCK_SIZE - len(data) % BLOCK_SIZE
        return data + bytes([padding_size]) * padding_size

    @staticmethod
    def unpad(data: bytes) -> bytes:
        if not data or len(data) % BLOCK_SIZE:
            raise ValueError("Некорректная длина данных с PKCS#7")

        padding_size = data[-1]
        if not 1 <= padding_size <= BLOCK_SIZE:
            raise ValueError("Некорректный PKCS#7 padding")
        if data[-padding_size:] != bytes([padding_size]) * padding_size:
            raise ValueError("Некорректный PKCS#7 padding")
        return data[:-padding_size]

    @staticmethod
    def _xor(left: bytes, right: bytes) -> bytes:
        if len(left) != len(right):
            raise ValueError("Для XOR нужны блоки одинаковой длины")
        return bytes(a ^ b for a, b in zip(left, right))

    @staticmethod
    def _blocks(data: bytes):
        for offset in range(0, len(data), BLOCK_SIZE):
            yield data[offset:offset + BLOCK_SIZE]

    @classmethod
    def ecb_encrypt(cls, data: bytes, aes: AES128) -> bytes:
        padded_data = cls.pad(data)
        return b"".join(aes.encrypt_block(block) for block in cls._blocks(padded_data))

    @classmethod
    def ecb_decrypt(cls, ciphertext: bytes, aes: AES128) -> bytes:
        if not ciphertext or len(ciphertext) % BLOCK_SIZE:
            raise ValueError("Длина ECB-шифротекста должна быть положительной и кратной 16")
        plaintext = b"".join(
            aes.decrypt_block(block) for block in cls._blocks(ciphertext)
        )
        return cls.unpad(plaintext)

    @classmethod
    def cbc_encrypt(cls, data: bytes, aes: AES128, iv: bytes) -> bytes:
        if not isinstance(iv, bytes) or len(iv) != BLOCK_SIZE:
            raise ValueError("IV для CBC должен состоять ровно из 16 байт")

        previous_block = iv
        ciphertext_blocks = []
        for plaintext_block in cls._blocks(cls.pad(data)):
            encrypted_block = aes.encrypt_block(
                cls._xor(plaintext_block, previous_block)
            )
            ciphertext_blocks.append(encrypted_block)
            previous_block = encrypted_block
        return b"".join(ciphertext_blocks)

    @classmethod
    def cbc_decrypt(cls, ciphertext: bytes, aes: AES128, iv: bytes) -> bytes:
        if (
            not isinstance(iv, bytes)
            or len(iv) != BLOCK_SIZE
            or not ciphertext
            or len(ciphertext) % BLOCK_SIZE
        ):
            raise ValueError("Некорректные IV или длина CBC-шифротекста")

        previous_block = iv
        plaintext_blocks = []
        for ciphertext_block in cls._blocks(ciphertext):
            decrypted_block = aes.decrypt_block(ciphertext_block)
            plaintext_blocks.append(cls._xor(decrypted_block, previous_block))
            previous_block = ciphertext_block
        return cls.unpad(b"".join(plaintext_blocks))


def make_bmp(width: int = 256, height: int = 256) -> tuple[bytes, bytes]:
    """Создаёт 24-битный BMP: белый фон, чёрный круг и красный квадрат."""
    if width <= 0 or height <= 0:
        raise ValueError("Размеры BMP должны быть положительными")

    row_size = (width * 3 + 3) & ~3  # строки BMP выравниваются по 4 байта
    pixels = bytearray()

    # В BMP с положительной высотой строки записываются снизу вверх.
    for y in range(height - 1, -1, -1):
        row = bytearray()
        for x in range(width):
            if (x - width // 2) ** 2 + (y - height // 2) ** 2 < min(width, height) ** 2 // 10:
                bgr = (0, 0, 0)
            elif 10 < x < min(60, width) and 10 < y < min(60, height):
                bgr = (0, 0, 255)
            else:
                bgr = (255, 255, 255)
            row.extend(bgr)
        row.extend(b"\x00" * (row_size - width * 3))
        pixels.extend(row)

    pixel_data = bytes(pixels)
    file_size = 54 + len(pixel_data)
    header = (
        b"BM"
        + struct.pack("<IHHI", file_size, 0, 0, 54)
        + struct.pack(
            "<IiiHHIIiiII",
            40, width, height, 1, 24, 0, len(pixel_data),
            2835, 2835, 0, 0,
        )
    )
    return header, pixel_data


def unique_blocks(data: bytes) -> tuple[int, int]:
    """Количество уникальных полных 16-байтных блоков и общее число блоков."""
    blocks = [data[i:i + BLOCK_SIZE] for i in range(0, len(data) - BLOCK_SIZE + 1, BLOCK_SIZE)]
    return len(set(blocks)), len(blocks)


def demo_padding(aes: AES128) -> None:
    print("== 1. PKCS#7 и проверка round-trip ==")
    iv = secrets.token_bytes(BLOCK_SIZE)

    for size in (5, 15, 16, 17, 32):
        message = b"A" * size
        padded = CipherModes.pad(message)
        ecb_ciphertext = CipherModes.ecb_encrypt(message, aes)
        cbc_ciphertext = CipherModes.cbc_encrypt(message, aes, iv)

        correct = (
            CipherModes.ecb_decrypt(ecb_ciphertext, aes) == message
            and CipherModes.cbc_decrypt(cbc_ciphertext, aes, iv) == message
        )
        print(
            f"  len={size:>2} -> padded={len(padded):>2} "
            f"(+{len(padded) - size:>2} байт, последний байт=0x{padded[-1]:02x}), "
            f"ct={len(ecb_ciphertext)} Б, расшифровка верна: {correct}"
        )

    message = "Привет, AES-128!".encode("utf-8")
    print("  Строка:", message, "->", CipherModes.cbc_encrypt(message, aes, iv).hex()[:32] + "...")


def demo_ecb_vs_cbc(aes: AES128) -> None:
    print("\n== 2. ECB vs CBC на изображении ==")
    output_dir = Path("out")
    output_dir.mkdir(parents=True, exist_ok=True)

    header, pixels = make_bmp()
    iv = secrets.token_bytes(BLOCK_SIZE)

    ecb_full = CipherModes.ecb_encrypt(pixels, aes)
    cbc_full = CipherModes.cbc_encrypt(pixels, aes, iv)

    # Для демонстрационного BMP оставляем исходную длину массива пикселей.
    # Это намеренно обрезает добавленный PKCS#7-блок: такие файлы нельзя
    # использовать как полноценный шифротекст или пытаться ими расшифровывать.
    results = {
        "original": pixels,
        "ecb": ecb_full[:len(pixels)],
        "cbc": cbc_full[:len(pixels)],
    }

    for name, image_data in results.items():
        (output_dir / f"{name}.bmp").write_bytes(header + image_data)
        unique_count, block_count = unique_blocks(image_data)
        print(
            f"  {name:<8} уникальных 16-байтных блоков: "
            f"{unique_count:>6} из {block_count}"
        )

    # Проверяем расшифровку полных шифротекстов, а не обрезанных BMP.
    assert CipherModes.ecb_decrypt(ecb_full, aes) == pixels
    assert CipherModes.cbc_decrypt(cbc_full, aes, iv) == pixels
    print("  Полные ECB/CBC шифротексты успешно прошли проверку расшифровки.")
    print("  BMP-файлы для визуального сравнения сохранены в out/.")


def main() -> None:
    # Один ключ создаётся на запуск и не выводится в консоль.
    key = secrets.token_bytes(AES128.KEY_SIZE)
    aes = AES128(key)

    print("Сгенерирован новый случайный ключ AES-128.")
    demo_padding(aes)
    demo_ecb_vs_cbc(aes)


if __name__ == "__main__":
    main()
