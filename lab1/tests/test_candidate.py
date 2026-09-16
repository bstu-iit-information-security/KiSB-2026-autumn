import pytest

from src.rng.factory import build_variant1_generator
from src.rng.seeding import build_stage2_rng
from src.primes.candidate import (
    generate_prime,
    naive_candidate_factory,
    seeded_candidate_factory,
)


_MR_WITNESSES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def is_prime_deterministic(n: int) -> bool:
    """
    Независимая (от Соловея-Штрассена) детерминированная проверка простоты -
    тест Миллера-Рабина с фиксированным набором свидетелей, доказанно точный
    для всех n < 3.3*10^24 (см. Pomerance-Selfridge-Wagstaff / Jaeschke).
    Используется в тестах вместо пробного деления, т.к. для 64-битных чисел
    пробное деление до sqrt(n) неоправданно медленно.
    """
    if n < 2:
        return False
    for p in _MR_WITNESSES:
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in _MR_WITNESSES:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def test_naive_candidate_has_correct_bit_length_and_is_odd():
    gen = build_variant1_generator()
    gen.reset()
    make_candidate = naive_candidate_factory(gen, p=16)
    n = make_candidate()
    assert n.bit_length() == 16
    assert n % 2 == 1


def test_naive_candidate_rejects_too_small_p():
    gen = build_variant1_generator()
    with pytest.raises(ValueError):
        naive_candidate_factory(gen, p=1)


def test_seeded_generate_prime_returns_actual_prime():
    gen = build_variant1_generator()
    rng = build_stage2_rng(gen, digits=64)
    make_candidate = seeded_candidate_factory(rng, p=64)
    log: list[dict] = []
    n = generate_prime(make_candidate, p=64, ss_rounds=8, rng=rng, log=log)

    assert n.bit_length() == 64
    assert n % 2 == 1
    assert is_prime_deterministic(n)
    assert log and log[-1]["n"] == n
    assert log[-1]["attempts"] >= 1


def test_seeded_generate_prime_log_contains_diagnostics():
    gen = build_variant1_generator()
    rng = build_stage2_rng(gen, digits=64)
    make_candidate = seeded_candidate_factory(rng, p=48)
    log: list[dict] = []
    generate_prime(make_candidate, p=48, ss_rounds=5, rng=rng, log=log)
    entry = log[-1]
    assert "sieved_out" in entry
    assert "elapsed_sec" in entry
    assert entry["elapsed_sec"] >= 0


def test_stage2_rng_is_deterministic_given_same_stage1_state():
    """Один и тот же генератор Этапа 1 (сброшенный) должен давать один и тот же сид."""
    gen_a = build_variant1_generator()
    gen_b = build_variant1_generator()
    rng_a = build_stage2_rng(gen_a, digits=32)
    rng_b = build_stage2_rng(gen_b, digits=32)
    assert rng_a.getrandbits(128) == rng_b.getrandbits(128)


def test_variant1_generator_too_short_for_large_candidates():
    """
    Документирует важное для отчёта наблюдение: генератор варианта 1
    (N=10, K=5) достигает МАКСИМАЛЬНОГО периода по условиям §4.1, но этот
    период (порядка десятков состояний) на много порядков меньше, чем 2^p
    различных p-битных чисел. При p=20 бит "буквальная" схема начинает
    повторять один и тот же небольшой набор кандидатов, и если среди них
    нет простых, поиск не сходится за разумное число попыток. Именно
    поэтому для Этапа 2 используется build_stage2_rng (генератор Этапа 1
    как источник СИДА), а не naive_candidate_factory напрямую.
    """
    gen = build_variant1_generator()
    gen.reset()
    make_candidate = naive_candidate_factory(gen, p=20)
    with pytest.raises(RuntimeError):
        generate_prime(make_candidate, p=20, ss_rounds=5, max_attempts=2000)
