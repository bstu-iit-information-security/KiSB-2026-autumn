"""Статистические тесты равномерности (без внешних зависимостей)."""
import math
from collections import Counter


# ---- хи-квадрат: функция распределения через неполную гамма-функцию -------------
def _gamma_q(a, x):
    """Регуляризованная верхняя неполная гамма-функция Q(a, x)."""
    if x <= 0:
        return 1.0
    lg = math.lgamma(a)
    if x < a + 1:  # ряд для P(a, x)
        term = s = 1.0 / a
        n = a
        for _ in range(10000):
            n += 1
            term *= x / n
            s += term
            if abs(term) < abs(s) * 1e-16:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - lg)
    tiny = 1e-300  # цепная дробь (Ленц)
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-16:
            break
    return math.exp(-x + a * math.log(x) - lg) * h


def chi2_sf(x, df):
    """P(chi2_df >= x)."""
    return _gamma_q(df / 2.0, x / 2.0)


def chi2_critical(df, alpha=0.05):
    """Квантиль уровня 1-alpha (метод бисекции)."""
    lo, hi = 0.0, 1.0
    while chi2_sf(hi, df) > alpha:
        hi *= 2
    for _ in range(100):
        mid = (lo + hi) / 2
        if chi2_sf(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---- тесты ----------------------------------------------------------------------
def chi_square_uniform(seq, alphabet, alpha=0.05):
    """Критерий согласия хи-квадрат: H0 - символы равномерны на {0..N-1}."""
    n = len(seq)
    cnt = Counter(seq)
    expected = n / alphabet
    chi2 = sum((cnt.get(i, 0) - expected) ** 2 / expected for i in range(alphabet))
    df = alphabet - 1
    p = chi2_sf(chi2, df)
    return {"n": n, "expected": expected, "chi2": chi2, "df": df,
            "crit": chi2_critical(df, alpha), "p": p, "ok": p >= alpha,
            "counts": [cnt.get(i, 0) for i in range(alphabet)]}


def bits_to_symbols(bits, k):
    """Склейка k соседних бит в символ алфавита мощности 2^k (без перекрытия)."""
    out = []
    for i in range(0, len(bits) - k + 1, k):
        v = 0
        for b in bits[i:i + k]:
            v = (v << 1) | b
        out.append(v)
    return out


def smallest_period(seq):
    """Наименьший период конечной последовательности (префикс-функция).
    Надёжен, если len(seq) >= 2*period (возвращается флаг reliable)."""
    n = len(seq)
    pi = [0] * n
    k = 0
    for i in range(1, n):
        while k and seq[i] != seq[k]:
            k = pi[k - 1]
        if seq[i] == seq[k]:
            k += 1
        pi[i] = k
    p = n - pi[-1]
    return p, n >= 2 * p
