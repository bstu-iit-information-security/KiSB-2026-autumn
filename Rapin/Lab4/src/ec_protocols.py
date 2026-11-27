"""Модуль 2. Протоколы ECDH и ЭЦП ECDSA."""

import hashlib
import secrets

from ec_algebra import mod_inv
from ec_ct import secure_multiply


def hash_to_scalar(curve, message):
    """e = SHA-256(M) mod q."""
    return int.from_bytes(hashlib.sha256(message).digest(), "big") % curve.q


def random_scalar(curve):
    """Случайное число из диапазона (0, q)."""
    return secrets.randbelow(curve.q - 1) + 1


def generate_keypair(curve):
    d = random_scalar(curve)
    return d, secure_multiply(curve, d, curve.G)


def validate_public_key(curve, Q):
    return (not curve.is_infinity(Q)) and curve.is_on_curve(Q)


def ecdh_shared_secret(curve, d, Q_peer):
    """K = d * Q_peer; общий секрет - координата x точки K."""
    if not validate_public_key(curve, Q_peer):
        raise ValueError("invalid peer public key")
    K = secure_multiply(curve, d, Q_peer)
    if curve.is_infinity(K):
        raise ValueError("shared point is at infinity")
    return curve.to_affine(K)[0]


def ecdsa_sign(curve, e, d, k=None):
    """Подпись ECDSA. Если k не задан, генерируется случайно (k задаётся только для тестов)."""
    q = curve.q
    if not 0 < d < q:
        raise ValueError("private key out of range")
    while True:
        kk = random_scalar(curve) if k is None else k
        C = secure_multiply(curve, kk, curve.G)
        r = curve.to_affine(C)[0] % q
        if r != 0:
            s = mod_inv(kk, q) * (e + r * d) % q
            if s != 0:
                return r, s
        if k is not None:
            raise ValueError("bad fixed k")


def ecdsa_verify(curve, e, signature, Q):
    q = curve.q
    r, s = signature
    if not (0 < r < q and 0 < s < q):
        return False
    if not validate_public_key(curve, Q):
        return False
    w = mod_inv(s, q)
    u1 = e * w % q
    u2 = r * w % q
    C = curve.add(curve.multiply(u1, curve.G), curve.multiply(u2, Q))
    if curve.is_infinity(C):
        return False
    return curve.to_affine(C)[0] % q == r
