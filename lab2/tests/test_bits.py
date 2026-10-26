from src.bits import bit_str, bits_to_int, bits_to_text, int_to_bits, parity, text_to_bits, weight


def test_text_roundtrip_ascii():
    bits = text_to_bits("Hi")
    assert len(bits) == 16
    assert bits == [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1]
    assert bits_to_text(bits) == "Hi"


def test_text_roundtrip_russian_cp1251():
    text = "Код Хемминга 2026!"
    assert bits_to_text(text_to_bits(text)) == text
    assert len(text_to_bits("Мир")) == 24  # один байт на символ


def test_int_bits_roundtrip():
    bits = [1, 0, 1, 1, 0, 0, 1]
    value = bits_to_int(bits)
    assert int_to_bits(value, 7) == bits
    assert bit_str(value, 7) == "1011001"


def test_weight_and_parity():
    assert weight(0b10110) == 3
    assert parity(0b10110) == 1
    assert parity(0b1001) == 0
