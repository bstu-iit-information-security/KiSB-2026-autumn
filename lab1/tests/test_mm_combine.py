from src.rng.lcg import LCG
from src.rng.mm_combine import MaclarenMarsaglia


def make_gen() -> MaclarenMarsaglia:
    g1 = LCG(a=1, c=3, N=10, x0=0)
    g2 = LCG(a=1, c=2, N=5, x0=0)
    return MaclarenMarsaglia(g1, g2, K=5)


def test_alphabet_mismatch_raises():
    g1 = LCG(a=1, c=3, N=10, x0=0)
    g2 = LCG(a=1, c=1, N=7, x0=0)  # N != K
    try:
        MaclarenMarsaglia(g1, g2, K=5)
        assert False, "ожидалось ValueError"
    except ValueError:
        pass


def test_output_within_g1_alphabet():
    gen = make_gen()
    seq = gen.sequence(300)
    assert all(0 <= x < 10 for x in seq)


def test_deterministic_after_reset():
    gen = make_gen()
    seq1 = gen.sequence(40)
    seq2 = gen.sequence(40)
    assert seq1 == seq2


def test_period_is_detected_and_positive():
    gen = make_gen()
    period, tau = gen.detect_period(max_len=5000)
    assert period is not None
    assert period > 0
    assert tau is not None and tau >= 0


def test_table_size_matches_k():
    gen = make_gen()
    gen.reset()
    assert len(gen._table) == 5
