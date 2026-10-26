"""
Вспомогательные функции для работы с двоичными данными.

Соглашение о представлении слов: слово длины n хранится как целое число,
где бит с номером p (p = 0..n-1) - это p-й символ слова. Позиции
0..k-1 - информационные символы, k..n-1 - проверочные (избыточные).
При выводе на экран слова записываются в порядке возрастания позиций
(слева направо), как это принято в методичке.
"""
from __future__ import annotations


def weight(x: int) -> int:
    """Вес (число единиц) двоичного числа."""
    return x.bit_count()


def parity(x: int) -> int:
    """Чётность числа единиц: 0 - чётное, 1 - нечётное (сумма по модулю 2)."""
    return x.bit_count() & 1


def text_to_bits(text: str, encoding: str = "cp1251") -> list[int]:
    """
    Информационное сообщение -> список бит (старший бит каждого байта первым).
    Для латиницы, цифр и служебных символов кодировка cp1251 совпадает с ASCII;
    кириллица кодируется одним байтом (методичка допускает ASCII-коды символов
    русского/английского алфавитов).
    """
    bits: list[int] = []
    for byte in text.encode(encoding):
        bits.extend((byte >> shift) & 1 for shift in range(7, -1, -1))
    return bits


def bits_to_text(bits: list[int], encoding: str = "cp1251") -> str:
    """Обратное преобразование; длина списка должна быть кратна 8."""
    if len(bits) % 8:
        raise ValueError("длина должна быть кратна 8 для преобразования в текст")
    data = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for b in bits[i : i + 8]:
            byte = (byte << 1) | b
        data.append(byte)
    return data.decode(encoding, errors="replace")


def bits_to_int(bits: list[int]) -> int:
    """Список бит -> целое (bits[p] становится битом с номером p)."""
    value = 0
    for p, b in enumerate(bits):
        if b:
            value |= 1 << p
    return value


def int_to_bits(value: int, length: int) -> list[int]:
    """Целое -> список бит длины length (бит p -> элемент p)."""
    return [(value >> p) & 1 for p in range(length)]


def bit_str(value: int, length: int, group: int = 0) -> str:
    """Строка из 0/1 в порядке возрастания позиций; group>0 - разбивка пробелами."""
    s = "".join(str((value >> p) & 1) for p in range(length))
    if group:
        s = " ".join(s[i : i + group] for i in range(0, len(s), group))
    return s
