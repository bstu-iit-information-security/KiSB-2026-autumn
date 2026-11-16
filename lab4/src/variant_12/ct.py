"""Модуль 3: Constant-time защита операций с секретами.

Главная задача варианта 12 — constant-time генерация эфемерного ключа k
(защита от утечки через Rejection Sampling).

Классический способ получить k из (0, q):

    while True:
        k = random(bits)
        if 0 < k < q: return k

Число итераций случайно и видно по времени: атакующий узнаёт, сколько
кандидатов было отброшено, а значит — что отброшенные числа были >= q,
то есть что старшие биты того генератора были «большими». Для
неудачного q (сильно меньше 2^bits) это ощутимая утечка о состоянии
ГПСЧ и о распределении k; кроме того, время подписи начинает зависеть
от случайности, связанной с секретом.

Безопасный способ (ct_random_scalar): цикл ВСЕГДА выполняется
фиксированное число раз N. На каждой итерации генерируется кандидат,
его допустимость (0 < k < q) вычисляется арифметически, без if,
а первый допустимый кандидат переносится в результат маской (CMOV).
Последующие допустимые кандидаты игнорируются той же маской, но вся
работа на итерации выполняется полностью.

Кроме того, модуль содержит:
  * примитивы без ветвлений: ct_is_zero, ct_lt, ct_select, ct_cswap;
  * ct_inv — инверсия по малой теореме Ферма (показатель p-2 публичен);
  * secure_multiply — скалярное умножение лестницей Монтгомери с
    условным обменом точек по маске и фиксированной длиной скаляра.

Ограничение: Python не даёт гарантий постоянного времени для длинной
арифметики (длина чисел и работа интерпретатора). Здесь устранены
ветвления и переменное число итераций, зависящие от секрета, — именно
то, что требуется в задании; аппаратная независимость времени
достижима только на языке с фиксированными машинными словами.
"""

import secrets

from ec import Point, Curve

# Все сравниваемые значения меньше 2^WIDTH. Сдвиг разности на WIDTH бит
# вправо даёт 0 для неотрицательной разности и -1 для отрицательной.
WIDTH = 1024

DEFAULT_ITERATIONS = 100


# --------------------------------------------------------------------------
# Примитивы без ветвлений
# --------------------------------------------------------------------------

def ct_lt(a: int, b: int) -> int:
    """1, если a < b, иначе 0 (для 0 <= a, b < 2^WIDTH)."""
    return ((a - b) >> WIDTH) & 1


def ct_is_zero(a: int) -> int:
    """1, если a == 0, иначе 0 (для 0 <= a < 2^WIDTH)."""
    return ((a - 1) >> WIDTH) & 1


def ct_eq(a: int, b: int) -> int:
    return ct_is_zero(a ^ b)


def ct_mask(bit: int) -> int:
    """bit = 0 -> 0x00...00, bit = 1 -> 0xFF...FF (в Python: -1, все единицы)."""
    return -bit


def ct_select(bit: int, a: int, b: int) -> int:
    """CMOV: возвращает a при bit = 1 и b при bit = 0, без if."""
    m = ct_mask(bit)
    return b ^ ((a ^ b) & m)


def ct_cswap(bit: int, a: int, b: int):
    """Условный обмен: dummy = mask & (a ^ b); a ^= dummy; b ^= dummy."""
    dummy = ct_mask(bit) & (a ^ b)
    return a ^ dummy, b ^ dummy


def ct_cswap_points(bit: int, P: Point, Q: Point) -> None:
    """Обмен координат двух точек на месте по маске."""
    P.x, Q.x = ct_cswap(bit, P.x, Q.x)
    P.y, Q.y = ct_cswap(bit, P.y, Q.y)
    P.inf, Q.inf = ct_cswap(bit, P.inf, Q.inf)


def ct_compare_bytes(a: bytes, b: bytes) -> bool:
    """Сравнение без раннего выхода: XOR-аккумулятор по всем байтам."""
    if len(a) != len(b):
        return False
    acc = 0
    for x, y in zip(a, b):
        acc |= x ^ y
    return acc == 0


# --------------------------------------------------------------------------
# Генерация эфемерного ключа k (задача варианта 12)
# --------------------------------------------------------------------------

def _system_rng(bits: int) -> int:
    return secrets.randbits(bits)


def naive_random_scalar(q: int, randbits=_system_rng):
    """Классический Rejection Sampling — для сравнения. УЯЗВИМ.

    Возвращает (k, attempts): число попыток и есть то, что утекает по времени.
    """
    bits = q.bit_length()
    attempts = 0
    while True:
        attempts += 1
        k = randbits(bits)
        if 0 < k < q:
            return k, attempts


def ct_random_scalar(q: int, randbits=_system_rng, iterations: int = DEFAULT_ITERATIONS) -> int:
    """Constant-time генерация k из (0, q).

    Ровно `iterations` итераций; в каждой:
        cand  = random(bits)
        valid = (cand != 0) & (cand < q)          — арифметически
        take  = valid & (found == 0)
        k     = CMOV(take, cand, k)
        found = found | valid
    Ни один if не зависит от cand, k или номера удачной итерации.
    Вероятность того, что за N итераций не нашлось ни одного кандидата,
    равна ((2^bits - q + 1) / 2^bits)^N: для bign-curve256v1 это ~2^(-12800).
    """
    bits = q.bit_length()
    k = 0
    found = 0
    for _ in range(iterations):
        cand = randbits(bits)
        valid = (1 - ct_is_zero(cand)) & ct_lt(cand, q)
        take = valid & (1 - found)
        k = ct_select(take, cand, k)
        found |= valid
    # Проверка публичного итога: зависит только от того, нашёлся ли хоть один
    # кандидат (событие пренебрежимо малой вероятности), а не от значения k.
    if not found:
        raise RuntimeError("не удалось выработать k за фиксированное число итераций")
    return k


# --------------------------------------------------------------------------
# Constant-time инверсия и скалярное умножение
# --------------------------------------------------------------------------

def ct_inv(x: int, p: int) -> int:
    """x^(p-2) mod p (малая теорема Ферма). Показатель фиксирован и публичен,
    поэтому последовательность возведений не зависит от x."""
    return pow(x, p - 2, p)


def _ladder_add(C: Curve, P: Point, Q: Point) -> Point:
    """P + Q в аффинных координатах с инверсией по Ферма.
    В лестнице всегда R1 - R0 = P0, поэтому R0 != ±R1 (кроме событий
    пренебрежимо малой вероятности, которые обрабатываются общим add)."""
    p = C.p
    if P.inf | Q.inf | (P.x == Q.x):
        return C.add(P, Q)
    s = (Q.y - P.y) * ct_inv((Q.x - P.x) % p, p) % p
    x3 = (s * s - P.x - Q.x) % p
    return Point(x3, (s * (P.x - x3) - P.y) % p)


def _ladder_double(C: Curve, P: Point) -> Point:
    p = C.p
    if P.inf | (P.y == 0):
        return C.double(P)
    s = (3 * P.x * P.x + C.a) * ct_inv(2 * P.y % p, p) % p
    x3 = (s * s - 2 * P.x) % p
    return Point(x3, (s * (P.x - x3) - P.y) % p)


def fixed_length_scalar(k: int, q: int) -> int:
    """k' = k + q или k + 2q так, чтобы старший бит всегда был на позиции
    bitlen(q): длина цикла лестницы не зависит от длины k, а k'·P = k·P."""
    n = q.bit_length()
    k1 = k + q
    k2 = k1 + q
    need_second = 1 - ((k1 >> n) & 1)          # у k1 нет бита n -> берём k2
    return ct_select(need_second, k2, k1)


def secure_multiply(C: Curve, k: int, P: Point) -> Point:
    """SecureMultiply: лестница Монтгомери с CSWAP по маске.

    На каждом бите — ровно одно сложение и одно удвоение:
        cswap(bit, R0, R1); R1 = R0 + R1; R0 = 2·R0; cswap(bit, R0, R1)
    Число итераций = bitlen(q) (скаляр приведён к фиксированной длине).
    """
    n = C.q.bit_length()
    kk = fixed_length_scalar(k % C.q, C.q)
    R0 = P.copy()                       # старший бит kk (позиция n) равен 1
    R1 = _ladder_double(C, P)
    for i in range(n - 1, -1, -1):
        bit = (kk >> i) & 1
        ct_cswap_points(bit, R0, R1)
        R1 = _ladder_add(C, R0, R1)
        R0 = _ladder_double(C, R0)
        ct_cswap_points(bit, R0, R1)
    return R0
