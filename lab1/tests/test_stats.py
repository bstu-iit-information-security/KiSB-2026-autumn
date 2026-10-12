from src.stats.tests import (
    frequency_test,
    chi_square_uniform,
    chi_square_critical_95,
    uniformity_verdict,
)


def test_frequencies_sum_to_one():
    seq = list(range(10)) * 20
    freqs = frequency_test(seq, alphabet_size=10)
    assert abs(sum(freqs.values()) - 1.0) < 1e-9


def test_chi_square_zero_for_perfectly_uniform_sequence():
    seq = list(range(10)) * 100
    chi2, df = chi_square_uniform(seq, alphabet_size=10)
    assert chi2 == 0
    assert df == 9


def test_chi_square_detects_skewed_distribution():
    seq = [0] * 900 + list(range(1, 10)) * 11  # сильный перекос к цифре 0
    chi2, df = chi_square_uniform(seq, alphabet_size=10)
    crit = chi_square_critical_95(df)
    assert chi2 > crit  # гипотеза о равномерности должна отвергаться


def test_uniformity_verdict_accepts_uniform_data():
    seq = list(range(10)) * 200
    verdict = uniformity_verdict(seq, alphabet_size=10)
    assert verdict["uniform_hypothesis_accepted"] is True


def test_chi_square_critical_table_known_value():
    assert chi_square_critical_95(9) == 16.919
