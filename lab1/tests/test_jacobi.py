import pytest

from src.primes.jacobi import jacobi_symbol


@pytest.mark.parametrize(
    "a,n,expected",
    [
        (1, 1, 1),
        (15, 1, 1),
        (2, 15, 1),
        (5, 21, 1),
        (7, 15, -1),
        (30, 59, -1),
        (1001, 9907, -1),
    ],
)
def test_known_values(a, n, expected):
    assert jacobi_symbol(a, n) == expected


def test_zero_when_gcd_not_one():
    assert jacobi_symbol(9, 3) == 0
    assert jacobi_symbol(6, 15) == 0


def test_raises_on_even_n():
    with pytest.raises(ValueError):
        jacobi_symbol(3, 10)


def test_raises_on_nonpositive_n():
    with pytest.raises(ValueError):
        jacobi_symbol(3, -5)
