from math import comb

from src.experiments import error_table, run_exhaustive
from src.hamming import HammingCode
from src.iterative import IterativeCode, IterativeConfig


def test_exhaustive_counts_and_partition():
    c = HammingCode(16, 3)
    for i in (1, 2, 3):
        row = run_exhaustive(c, i, max_weight=1)
        assert row["N1"] == comb(c.n, i)
        assert row["exact"] + row["miscorrected"] + row["detected"] + row["undetected"] == row["N1"]


def test_hamming_extended_table_numbers():
    c = HammingCode(16, 4)
    rows = error_table(c, 2, 1000, 1, seed=1)
    assert rows[0]["N3/N1"] == 1.0
    assert rows[1]["detected"] == rows[1]["N1"] == 231 and rows[1]["N3"] == 0


def test_random_trials_are_reproducible_and_partition_n1():
    c = IterativeCode(IterativeConfig(4, 4, 1, 3))
    a = error_table(c, 4, 500, 3, seed=42)
    b = error_table(c, 4, 500, 3, seed=42)
    assert a == b
    for row in a:
        assert row["exact"] + row["miscorrected"] + row["detected"] + row["undetected"] == row["N1"]
        assert row["N3"] <= row["N2"] <= row["N1"]
    assert a[2]["N1"] == a[3]["N1"] == 500 and a[2]["mode"] == "случайные"


def test_n2_equals_n3_for_leader_decoder():
    # лидер единственного минимального веса, найденный для ошибки веса i, - это сама ошибка
    c = IterativeCode(IterativeConfig(4, 2, 2, 4))
    for row in error_table(c, 3, 2000, 3, seed=5):
        assert row["N2"] == row["N3"]
