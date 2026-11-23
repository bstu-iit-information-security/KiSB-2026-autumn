# -*- coding: utf-8 -*-
"""
Модуль 2. Криптографические протоколы: согласование ключей ECDH и ЭЦП EdDSA (Ed25519,
RFC 8032). Хэш-функция SHA-512 (FIPS 180-4) реализована здесь же.
Для операций с секретами (d, r) используется модуль 3 (secure_multiply,
ct_decompress, ct_point_eq), для проверки подписи по публичным данным — модуль 1.
"""
import secrets
import struct

import ec_curve as ec
import ct_secure as ct

# ----------------------------------------------------------------------
#                     ХЭШ-ФУНКЦИЯ SHA-512
# ----------------------------------------------------------------------
MASK64 = (1 << 64) - 1


def _first_primes(n):
    primes, k = [], 2
    while len(primes) < n:
        if all(k % q for q in primes if q * q <= k):
            primes.append(k)
        k += 1
    return primes


def _icbrt(n):
    """Целая часть кубического корня (метод Ньютона)."""
    x = 1 << ((n.bit_length() + 2) // 3)
    while True:
        y = (2 * x + n // (x * x)) // 3
        if y >= x:
            return x
        x = y


def _isqrt(n):
    x = 1 << ((n.bit_length() + 1) // 2)
    while True:
        y = (x + n // x) // 2
        if y >= x:
            return x
        x = y


# Константы FIPS 180-4: дробные части кубических (K) и квадратных (H0) корней первых
# 80 и 8 простых чисел (первые 64 бита). Правильность проверяется тест-векторами.
SHA512_K = tuple(_icbrt(q << 192) & MASK64 for q in _first_primes(80))
SHA512_H0 = tuple(_isqrt(q << 128) & MASK64 for q in _first_primes(8))


def _rotr(x, n):
    return ((x >> n) | (x << (64 - n))) & MASK64


def sha512(data):
    data = bytes(data)
    ml = len(data) * 8
    data += b"\x80" + b"\x00" * ((111 - len(data)) % 128) + ml.to_bytes(16, "big")
    h = list(SHA512_H0)
    w = [0] * 80                                  # фиксированный массив расписания
    for off in range(0, len(data), 128):
        w[:16] = struct.unpack(">16Q", data[off:off + 128])
        for i in range(16, 80):
            s0 = _rotr(w[i - 15], 1) ^ _rotr(w[i - 15], 8) ^ (w[i - 15] >> 7)
            s1 = _rotr(w[i - 2], 19) ^ _rotr(w[i - 2], 61) ^ (w[i - 2] >> 6)
            w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & MASK64
        a, b, c, d, e, f, g, hh = h
        for i in range(80):
            t1 = (hh + (_rotr(e, 14) ^ _rotr(e, 18) ^ _rotr(e, 41)) + ((e & f) ^ (~e & g))
                  + SHA512_K[i] + w[i]) & MASK64
            t2 = ((_rotr(a, 28) ^ _rotr(a, 34) ^ _rotr(a, 39)) + ((a & b) ^ (a & c) ^ (b & c))) & MASK64
            hh, g, f, e, d, c, b, a = g, f, e, (d + t1) & MASK64, c, b, a, (t1 + t2) & MASK64
        h = [(x + y) & MASK64 for x, y in zip(h, (a, b, c, d, e, f, g, hh))]
    return b"".join(x.to_bytes(8, "big") for x in h)


def hash_int(*parts):
    """SHA-512(parts) как целое little-endian по модулю q."""
    return int.from_bytes(sha512(b"".join(parts)), "little") % ec.Q


# ----------------------------------------------------------------------
#                     КЛЮЧИ Ed25519
# ----------------------------------------------------------------------
def clamp(h32):
    """«Зажим» секретного скаляра (RFC 8032, 5.1.5): сброс 3 младших бит (кратность
    кофактору 8), сброс бита 255 и установка бита 254."""
    d = int.from_bytes(h32, "little")
    d &= ~7
    d &= (1 << 254) - 1
    d |= 1 << 254
    return d


def keypair(seed):
    """Секретный ключ — 32 случайных байта seed. h = SHA-512(seed): d = clamp(h[0:32]),
    prefix = h[32:64] (старшая половина h_B), открытый ключ A = d*G."""
    if len(seed) != 32:
        raise ValueError("секретный ключ Ed25519 должен содержать 32 байта")
    h = sha512(seed)
    d = clamp(h[:32])
    A = ct.secure_multiply(d, ec.G)
    return d, h[32:], A, ec.encode_point(A)


# ----------------------------------------------------------------------
#                     ЭЦП EdDSA (Ed25519)
# ----------------------------------------------------------------------
def sign(msg, seed):
    """r = SHA-512(prefix || M) mod q,  R = r*G,  S = (r + SHA-512(R || A || M)*d) mod q.
    Подпись — 64 байта: encode(R) || S (little-endian)."""
    d, prefix, _, a_enc = keypair(seed)
    r = hash_int(prefix, msg)
    R = ct.secure_multiply(r, ec.G)
    r_enc = ec.encode_point(R)
    k = hash_int(r_enc, a_enc, msg)
    s = (r + k * d) % ec.Q
    return r_enc + s.to_bytes(32, "little")


def verify(msg, sig, pub):
    """Проверка: h = SHA-512(R || A || M) mod q; подпись верна, если S*G = R + h*A.
    Возвращает (результат, причина, словарь промежуточных значений)."""
    if len(sig) != 64 or len(pub) != 32:
        return False, "неверная длина подписи или ключа", {}
    A, ok_a = ct.ct_decompress(pub)
    R, ok_r = ct.ct_decompress(sig[:32])
    s = int.from_bytes(sig[32:], "little")
    if not ok_a:
        return False, "открытый ключ не является точкой кривой", {}
    if not ok_r:
        return False, "R не является точкой кривой", {}
    if s >= ec.Q:
        return False, "S >= q (вне допустимого диапазона)", {"S": s}
    h = hash_int(sig[:32], pub, msg)
    left = ec.multiply(s, ec.G)
    right = ec.add(R, ec.multiply(h, A))
    ok = ct.ct_point_eq(left, right) == 1
    info = {"S": s, "h": h, "left": left, "right": right}
    return ok, ("S*G = R + h*A" if ok else "S*G != R + h*A"), info


# ----------------------------------------------------------------------
#                     ПРОТОКОЛ ECDH НА КРИВОЙ Ed25519
# ----------------------------------------------------------------------
def ecdh_keypair(seed=None):
    """Эфемерная пара: d = clamp(seed) (seed — 32 случайных байта), Q = d*G.
    Открытый ключ передаётся в сжатом виде (32 байта)."""
    seed = secrets.token_bytes(32) if seed is None else seed
    if len(seed) != 32:
        raise ValueError("секрет ECDH должен содержать 32 байта")
    d = clamp(seed)
    Qp = ct.secure_multiply(d, ec.G)
    return d, Qp, ec.encode_point(Qp)


def ecdh_shared(d, peer_pub):
    """K = d * Q_peer. Q_peer распаковывается constant-time Тонелли-Шенксом и
    проверяется; общий секрет — координата x точки K."""
    Qp, ok = ct.ct_decompress(peer_pub)
    if not ok:
        raise ValueError("открытый ключ собеседника не является точкой кривой")
    K = ct.secure_multiply(d, Qp)
    if K == ec.O:
        raise ValueError("общий секрет — нейтральная точка (точка малого порядка)")
    return K
