import math


def monobit_test(bits: list[int]) -> tuple[float, float]:
    n = len(bits)
    ones = sum(bits)
    p = ones / n
    # z = (2·ones − n) / sqrt(n) ~ N(0,1) при H0
    z = (2 * ones - n) / math.sqrt(n)
    return p, z


def block_test(bits: list[int], block_size: int = 8) -> float:
    n = len(bits)
    n_blocks = n // block_size
    if n_blocks < 5 * (1 << block_size):
        raise ValueError("Слишком мало данных для блочного теста")

    counts = [0] * (1 << block_size)
    for i in range(n_blocks):
        val = 0
        base = i * block_size
        for j in range(block_size):
            val = (val << 1) | bits[base + j]
        counts[val] += 1

    expected = n_blocks / (1 << block_size)
    chi2 = sum((c - expected) ** 2 / expected for c in counts)
    return chi2


def chi2_critical(df: int, alpha: float = 0.05) -> float:
    z = {0.05: 1.6449, 0.01: 2.3263, 0.10: 1.2816}[alpha]
    t = 2.0 / (9.0 * df)
    return df * (1 - t + z * math.sqrt(t)) ** 3


def runs_test(bits: list[int]) -> dict:
    n = len(bits)
    runs = 1
    for i in range(1, n):
        if bits[i] != bits[i - 1]:
            runs += 1
    ones = sum(bits)
    zeros = n - ones
    expected = 1 + 2 * ones * zeros / n
    var = (2 * ones * zeros * (2 * ones * zeros - n)) / (n * n * (n - 1))
    z = (runs - expected) / math.sqrt(var) if var > 0 else 0.0
    return {"runs": runs, "expected": expected, "z": z}