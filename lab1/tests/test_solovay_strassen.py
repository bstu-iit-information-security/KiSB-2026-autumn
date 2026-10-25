import random

from src.primes.jacobi import jacobi_symbol
from src.primes.solovay_strassen import is_probable_prime, solovay_strassen_round

SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
SMALL_COMPOSITES = [4, 6, 8, 9, 10, 12, 15, 21, 25, 27, 33, 35, 45, 49, 51, 63, 77, 91, 99]


class FixedRandom:
    """Тестовая замена random.Random, всегда возвращающая заданное основание a."""

    def __init__(self, value: int):
        self.value = value

    def randrange(self, start: int, stop: int) -> int:
        return self.value


def test_small_primes_always_pass():
    rng = random.Random(42)
    for p in SMALL_PRIMES:
        assert is_probable_prime(p, rounds=15, rng=rng) is True


def test_small_composites_are_rejected():
    rng = random.Random(1)
    for c in SMALL_COMPOSITES:
        assert is_probable_prime(c, rounds=15, rng=rng) is False


def test_fermat_pseudoprime_341_detected_by_solovay_strassen():
    """
    Классический пример: 341 = 11*31 - псевдопростое Ферма по основанию 2
    (2^340 ≡ 1 mod 341), но НЕ является псевдопростым Эйлера по основанию 2,
    поэтому тест Соловея-Штрассена (в отличие от голого теста Ферма) должен
    его отбраковать.
    """
    n = 341
    assert pow(2, n - 1, n) == 1  # тест Ферма "обманывается" на основании 2
    assert jacobi_symbol(2, n) == -1
    assert pow(2, (n - 1) // 2, n) == 1  # не совпадает с символом Якоби (=-1 mod n)

    fixed_rng = FixedRandom(2)
    assert solovay_strassen_round(n, rng=fixed_rng) is False


def test_edge_cases():
    assert is_probable_prime(2) is True
    assert is_probable_prime(3) is True
    assert is_probable_prime(1) is False
    assert is_probable_prime(0) is False
