import pytest

from src.bits import bit_str, bits_to_int
from src.experiments import run_exhaustive
from src.iterative import VARIANT1_CONFIGS, IterativeCode, IterativeConfig, cell

ALL = [(k1, k2, z, g) for (k1, k2, z, gs) in VARIANT1_CONFIGS for g in gs]


def make(k1, k2, z, g):
    return IterativeCode(IterativeConfig(k1, k2, z, g))


@pytest.mark.parametrize(
    "k1,k2,z,g,r",
    [
        (4, 4, 1, 2, 8), (4, 4, 1, 3, 15),
        (8, 2, 1, 2, 10), (8, 2, 1, 3, 19),
        (4, 2, 2, 2, 12), (4, 2, 2, 3, 20), (4, 2, 2, 4, 28), (4, 2, 2, 5, 36),
        (2, 4, 2, 2, 12), (2, 4, 2, 3, 20), (2, 4, 2, 4, 28), (2, 4, 2, 5, 36),
    ],
)
def test_number_of_check_bits(k1, k2, z, g, r):
    c = make(k1, k2, z, g)
    assert c.k == 16 and c.r == r and c.n == 16 + r


@pytest.mark.parametrize("k1,k2,z,g", ALL)
def test_every_cell_is_covered_once_per_group(k1, k2, z, g):
    c = make(k1, k2, z, g)
    for group in range(1, g + 1):
        cover = [0] * c.k
        for mask, gid in zip(c.masks, c.group_ids):
            if gid == group:
                for t in range(c.k):
                    cover[t] += (mask >> t) & 1
        assert cover == [1] * c.k, f"группа {group}"


def test_manual_example_fig_5_1_and_5_3():
    # информационное слово 011 101 111: X_h = 001, X_v = 001, диагонали X_d = 00001
    c = make(3, 3, 1, 3)
    info = bits_to_int([0, 1, 1, 1, 0, 1, 1, 1, 1])
    _, checks = c.split(c.encode(info))
    assert bit_str(checks, c.r) == "001" + "001" + "00001"


def test_cell_numbering_follows_fig_5_4():
    cfg = IterativeConfig(4, 4, 2, 2)  # две плоскости 4x4: x17 - начало второй плоскости
    assert cell(cfg, 0) == (0, 0, 0)
    assert cell(cfg, 16) == (1, 0, 0)
    assert cell(cfg, 21) == (1, 1, 1)


@pytest.mark.parametrize("k1,k2,z,g", ALL)
def test_minimum_distance_is_groups_plus_one(k1, k2, z, g):
    assert make(k1, k2, z, g).min_distance() == g + 1


@pytest.mark.parametrize("k1,k2,z,g", ALL)
def test_all_single_errors_are_corrected(k1, k2, z, g):
    c = make(k1, k2, z, g)
    row = run_exhaustive(c, 1, max_weight=3)
    assert row["exact"] == row["N1"] == c.n


@pytest.mark.parametrize("k1,k2,z,g", [(4, 2, 2, 4), (4, 2, 2, 5), (2, 4, 2, 4), (2, 4, 2, 5)])
def test_all_double_errors_are_corrected_when_dmin_at_least_5(k1, k2, z, g):
    c = make(k1, k2, z, g)
    row = run_exhaustive(c, 2, max_weight=3)
    assert row["exact"] == row["N1"]


def test_two_groups_cannot_correct_double_errors_in_4x4():
    c = make(4, 4, 1, 2)
    row = run_exhaustive(c, 2, max_weight=3)
    assert (row["exact"], row["miscorrected"], row["detected"], row["undetected"]) == (0, 48, 228, 0)


def test_three_groups_detect_every_double_error_and_correct_most():
    c = make(4, 4, 1, 3)
    row = run_exhaustive(c, 2, max_weight=3)
    assert row["miscorrected"] == 0 and row["undetected"] == 0
    assert row["exact"] + row["detected"] == row["N1"] == 465


def test_code_is_linear():
    c = make(4, 2, 2, 5)
    a, b = 0x1234, 0xA5C3
    assert c.encode(a ^ b) == c.encode(a) ^ c.encode(b)


def test_five_groups_require_z_planes():
    with pytest.raises(ValueError):
        IterativeConfig(4, 4, 1, 5)


def test_failed_checks_and_position_names():
    c = make(4, 4, 1, 3)
    word = c.encode(0xBEEF)
    res = c.decode(word ^ (1 << 5), max_weight=3)
    assert res.status == "corrected" and res.error_positions == (5,)
    assert c.position_name(5) == "x6=[пл0,стр1,стлб1]"
    assert set(c.failed_checks(res.syndrome)) >= {"H[пл0,стр1]", "V[пл0,стлб1]"}
