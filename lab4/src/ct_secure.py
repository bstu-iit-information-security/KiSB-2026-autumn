# -*- coding: utf-8 -*-
"""
Модуль 3. Constant-time защита и оптимизация памяти.

Индивидуальная задача варианта 15: constant-time извлечение квадратного корня
по модулю (алгоритм Тонелли-Шенкса с изоляцией ветвлений) и его применение
при декомпрессии открытых ключей Ed25519.

Также содержит обёртки для работы с секретами: выбор по маске (CMOV), условный
обмен (CSWAP), сравнение без раннего выхода (SecureCompare) и скалярное умножение
лестницей Монтгомери (SecureMultiply). В коде нет условных операторов и циклов,
число итераций которых зависит от секретных данных; состояние хранится в одномерных
массивах фиксированного размера, вложенные динамические контейнеры не используются.
"""
import ec_curve as ec

SCALAR_BITS = 256
OPS = [0]            # счётчик модульных умножений (для анализа в отчёте)


# ----------------------------------------------------------------------
#                     ПРИМИТИВЫ БЕЗ ВЕТВЛЕНИЙ
# ----------------------------------------------------------------------
def ct_is_zero(x, bits=SCALAR_BITS):
    """1, если x = 0, иначе 0 (0 <= x < 2^bits): при x = 0 разность x - 1 = -1
    и сдвиг даёт -1 (все единицы), иначе 0. Условного оператора нет."""
    return ((x - 1) >> bits) & 1


def ct_eq(a, b, bits=SCALAR_BITS):
    return ct_is_zero(a ^ b, bits)


def ct_select(a, b, flag):
    """CMOV: flag = 0 -> a, flag = 1 -> b. mask = 0 - flag (0...0 или 1...1)."""
    mask = -flag
    return a ^ ((a ^ b) & mask)


def ct_cswap(state, i, j, flag):
    """CSWAP элементов state[i] и state[j]: dummy = mask & (X xor Y), X ^= dummy, Y ^= dummy."""
    mask = -flag
    dummy = mask & (state[i] ^ state[j])
    state[i] ^= dummy
    state[j] ^= dummy


def ct_bytes_eq(a, b):
    """SecureCompare: XOR-аккумулятор без раннего выхода (длины публичны)."""
    if len(a) != len(b):
        return 0
    acc = 0
    for x, y in zip(a, b):
        acc |= x ^ y
    return ct_is_zero(acc, 8)


def ct_point_eq(p1, p2):
    """Сравнение точек через аккумулятор: (x1 xor x2) | (y1 xor y2) = 0."""
    return ct_is_zero((p1.x ^ p2.x) | (p1.y ^ p2.y))


def _mul(a, b, p):
    OPS[0] += 1
    return a * b % p


def _pow(a, e, p):
    """Возведение в степень; стоимость учитывается как число умножений схемы
    «квадрат и умножение», зависящее только от показателя e."""
    OPS[0] += e.bit_length() + bin(e).count("1")
    return pow(a, e, p)


# ----------------------------------------------------------------------
#           КВАДРАТНЫЙ КОРЕНЬ: ТОНЕЛЛИ-ШЕНКС (ВАРИАНТ 15)
# ----------------------------------------------------------------------
class SqrtContext:
    """Публичные константы для модуля p: p - 1 = Q * 2^S (Q нечётно), невычет z,
    c = z^Q. Вычисляются один раз и не зависят от секретов."""
    __slots__ = ("p", "S", "Q", "z", "c_q", "e_q", "bits")

    def __init__(self, p):
        self.p, self.bits = p, p.bit_length()
        self.Q, self.S = p - 1, 0
        while self.Q % 2 == 0:
            self.Q //= 2
            self.S += 1
        z = 2
        while pow(z, (p - 1) // 2, p) != p - 1:       # критерий Эйлера
            z += 1
        self.z = z
        self.c_q = pow(z, self.Q, p)                    # c = z^Q
        self.e_q = (self.Q - 1) // 2                    # показатель (Q - 1)/2


CTX25519 = SqrtContext(ec.P)


def ct_sqrt(a, ctx=CTX25519):
    """Constant-time Тонелли-Шенкс. Число итераций фиксировано и задаётся
    только публичным S: внешний цикл i = S..2, внутренний — i - 2 возведения в
    квадрат. Вместо поиска наименьшего i и раннего выхода выполняются все шаги,
    а переназначение R и t делается по битовой маске (ct_select).
    Возвращает (R, ok): ok = 1, если R^2 = a (a — квадратичный вычет)."""
    p = ctx.p
    a %= p
    r = _pow(a, ctx.e_q, p)              # a^((Q-1)/2)
    t = _mul(_mul(r, r, p), a, p)        # t = a^Q
    r = _mul(r, a, p)                    # R = a^((Q+1)/2)
    b, c = t, ctx.c_q
    for i in range(ctx.S, 1, -1):        # S - 1 итераций, число публично
        for _ in range(i - 2):
            b = _mul(b, b, p)            # b = t^(2^(i-2))
        e = ct_eq(b, 1, ctx.bits)        # 1, если коррекция на этом шаге не нужна
        r = ct_select(_mul(r, c, p), r, e)
        c = _mul(c, c, p)
        t = ct_select(_mul(t, c, p), t, e)
        b = t
    ok = ct_eq(_mul(r, r, p), a, ctx.bits)
    return r, ok


def sqrt_classic(a, ctx=CTX25519):
    """Классический (variable-time) Тонелли-Шенкс — ТОЛЬКО для сравнения:
    ранние выходы, цикл while и поиск наименьшего i зависят от a."""
    p = ctx.p
    a %= p
    if a == 0:
        return 0, 1
    if _pow(a, (p - 1) // 2, p) != 1:
        return 0, 0
    m, c = ctx.S, ctx.c_q
    t, r = _pow(a, ctx.Q, p), _pow(a, (ctx.Q + 1) // 2, p)
    while t != 1:
        i, t2 = 0, t
        while t2 != 1:
            t2 = _mul(t2, t2, p)
            i += 1
        b = _pow(c, 1 << (m - i - 1), p)
        m, c = i, _mul(b, b, p)
        t, r = _mul(t, c, p), _mul(r, b, p)
    return r, 1


def ct_decompress(data):
    """Декомпрессия точки Ed25519 (RFC 8032, 5.1.3) без ветвлений:
    y — младшие 255 бит, знак x — старший бит; x = sqrt((y^2 - 1)/(d*y^2 + 1)),
    выбор корня нужной чётности — по маске. Возвращает (точка, valid)."""
    if len(data) != 32:
        raise ValueError("сжатая точка должна занимать 32 байта")
    v = int.from_bytes(data, "little")
    sign, y = v >> 255, v & ((1 << 255) - 1)
    y_ok = ((y - ec.P) >> SCALAR_BITS) & 1                      # 1, если y < p
    x, ok = ct_sqrt(ec.x2_from_y(y))
    x = ct_select(x, (ec.P - x) % ec.P, (x & 1) ^ sign)       # нужная чётность
    bad = ct_is_zero(x) & sign                                 # x = 0, но знак 1
    return ec.Point(x, y), ok & y_ok & (1 - bad)


# ----------------------------------------------------------------------
#           СКАЛЯРНОЕ УМНОЖЕНИЕ ДЛЯ СЕКРЕТНЫХ СКАЛЯРОВ
# ----------------------------------------------------------------------
def secure_multiply(k, pt, bits=SCALAR_BITS):
    """SecureMultiply: лестница Монтгомери на фиксированном числе бит (256).
    На каждый бит — ровно одно сложение и одно удвоение, оба по единой
    формуле Эдвардса; выбор R0/R1 — условным обменом CSWAP без if.
    Состояние [x0, y0, x1, y1] — одномерный массив фиксированного размера."""
    st = [0, 1, pt.x, pt.y]                      # R0 = O, R1 = P
    for i in range(bits - 1, -1, -1):
        b = (k >> i) & 1
        ct_cswap(st, 0, 2, b)
        ct_cswap(st, 1, 3, b)
        r0, r1 = ec.Point(st[0], st[1]), ec.Point(st[2], st[3])
        s = ec.add(r0, r1)                        # R1 = R0 + R1
        d = ec.add(r0, r0)                        # R0 = 2*R0 (та же единая формула)
        st[0], st[1], st[2], st[3] = d.x, d.y, s.x, s.y
        ct_cswap(st, 0, 2, b)
        ct_cswap(st, 1, 3, b)
    return ec.Point(st[0], st[1])
