from src.rng.lcg import LCG


def test_full_period_when_condition_met():
    # N=10 (делители 2 и 5): a≡1(mod10) => a-1=0 кратно и 2, и 5.
    gen = LCG(a=1, c=3, N=10, x0=0)
    assert gen.satisfies_max_period_condition() is True
    period, tau = gen.full_period()
    assert period == 10
    assert tau == 0


def test_full_period_for_k_alphabet():
    # K=5 (простое): a≡1(mod5).
    gen = LCG(a=1, c=2, N=5, x0=0)
    assert gen.satisfies_max_period_condition() is True
    period, tau = gen.full_period()
    assert period == 5


def test_condition_violation_detected():
    # a=3: (a-1)=2 не кратно 5 => условие b) нарушено для делителя 5.
    gen = LCG(a=3, c=1, N=10, x0=0)
    assert gen.satisfies_max_period_condition() is False


def test_short_period_when_condition_violated():
    gen = LCG(a=3, c=1, N=10, x0=0)
    period, tau = gen.full_period()
    assert period is not None
    assert period < 10  # период короче максимального N=10


def test_sequence_values_within_alphabet():
    gen = LCG(a=1, c=3, N=10, x0=0)
    seq = gen.sequence(50)
    assert len(seq) == 50
    assert all(0 <= x < 10 for x in seq)


def test_gcd_condition_violation():
    # c=2 не взаимно просто с N=10 (НОД=2) => условие a) нарушено.
    gen = LCG(a=1, c=2, N=10, x0=0)
    assert gen.satisfies_max_period_condition() is False
