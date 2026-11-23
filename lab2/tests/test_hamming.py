from itertools import combinations

import pytest

from src.bits import weight
from src.hamming import HammingCode, min_check_bits, p_columns
from src.reports import hamming_demo


@pytest.mark.parametrize("k,r", [(4, 3), (6, 4), (8, 4), (9, 4), (10, 4), (11, 4), (15, 5), (16, 5)])
def test_number_of_check_bits(k, r):
    assert min_check_bits(k) == r


def test_h_matrix_of_hamming_7_4_matches_manual():
    # проверочная матрица (7,4)-кода из методички (стр. 40)
    c = HammingCode(4)
    assert c.h_matrix() == [
        [0, 1, 1, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],
        [1, 1, 0, 1, 0, 0, 1],
    ]


def test_p_columns_follow_weight_order():
    cols = p_columns(16, 5)
    assert cols[:2] == [0b00011, 0b00101]          # примеры методички: 3 -> 00011, 5 -> 00101
    assert [weight(c) for c in cols] == [2] * 10 + [3] * 6
    assert len(set(cols)) == 16


@pytest.mark.parametrize("k,dmin", [(4, 3), (4, 4), (8, 3), (8, 4), (16, 3), (16, 4)])
def test_measured_minimum_distance(k, dmin):
    assert HammingCode(k, dmin).min_distance() == dmin


def test_extended_code_has_n_plus_one_parity():
    c3, c4 = HammingCode(16, 3), HammingCode(16, 4)
    assert (c3.n, c3.r) == (21, 5)
    assert (c4.n, c4.r) == (22, 6)
    # все кодовые слова расширенного кода имеют чётный вес
    for info in range(0, 1 << 16, 997):
        assert weight(c4.encode(info)) % 2 == 0


@pytest.mark.parametrize("dmin", [3, 4])
def test_encode_decode_without_errors(dmin):
    c = HammingCode(16, dmin)
    for info in (0, 1, 0xA5A5, 0xFFFF):
        word = c.encode(info)
        res = c.decode_word(word)
        assert res.status == "ok" and res.word == word and res.syndrome == 0


@pytest.mark.parametrize("dmin", [3, 4])
def test_every_single_error_is_corrected(dmin):
    c = HammingCode(16, dmin)
    word = c.encode(0xBEEF)
    for p in range(c.n):
        res = c.decode_word(word ^ (1 << p))
        assert res.status == "corrected" and res.error_positions == (p,) and res.word == word


def test_syndrome_is_xor_of_h_columns_at_error_positions():
    c = HammingCode(16, 3)
    word = c.encode(0x1234)
    for pos in combinations(range(c.n), 2):
        received = word ^ (1 << pos[0]) ^ (1 << pos[1])
        assert c.syndrome(received) == c.columns[pos[0]] ^ c.columns[pos[1]]


def test_extended_code_detects_all_double_errors():
    c = HammingCode(16, 4)
    word = c.encode(0x00FF)
    for a, b in combinations(range(c.n), 2):
        res = c.decode_word(word ^ (1 << a) ^ (1 << b))
        assert res.status == "detected"


def test_basic_code_miscorrects_or_detects_double_errors():
    # d_min = 3: двойная ошибка никогда не исправляется верно (147 ошибочных коррекций, 63 обнаружено)
    c = HammingCode(16, 3)
    word = c.encode(0x00FF)
    stats = {"corrected": 0, "detected": 0}
    for a, b in combinations(range(c.n), 2):
        res = c.decode_word(word ^ (1 << a) ^ (1 << b))
        stats[res.status] += 1
        assert res.word != word
    assert stats == {"corrected": 147, "detected": 63}


def test_demo_requires_at_least_16_bits():
    with pytest.raises(ValueError):
        hamming_demo("A")


def test_demo_output_contains_required_items():
    text = hamming_demo("Hi", dmin=3, n_errors=1, seed=7)
    for token in ("k = 16", "r = 5", "n = 21", "X_n", "X_r", "Y_n", "Y_r'", "S ", "E_n", "H = [P' | I]"):
        assert token in text
    assert "восстановлено верно" in text
