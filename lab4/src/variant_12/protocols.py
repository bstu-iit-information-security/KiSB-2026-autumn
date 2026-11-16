"""Модуль 2: криптографические протоколы — ECDH и ЭЦП СТБ 34.101.45.

Использует модуль 1 (ec.py) для арифметики и модуль 3 (ct.py) для всех
операций с секретами: генерации d и k, умножения d·G, k·G, d·Q.

Схема подписи — по методическим указаниям (п. 3, «СТБ 34.101.45 /
ГОСТ Р 34.10-2012»), хэш-функция — belt-hash (СТБ 34.101.31):
  подпись:  k <- (0, q) (constant-time), C = k·G, r = x_C mod q,
            s = (r·d + k·e) mod q; при r = 0 или s = 0 — повтор;
  проверка: 0 < r, s < q, v = e^(-1), z1 = s·v, z2 = -r·v (mod q),
            C' = z1·G + z2·Q, подпись верна, если x_C' mod q = r.
"""

from belt_hash import belt_hash
from ct import ct_random_scalar, secure_multiply, ct_compare_bytes, _system_rng
from ec import BIGN256, Curve, Point

COORD = 32


def int_to_hex(x: int, nbytes: int = COORD) -> str:
    return x.to_bytes(nbytes, "big").hex().upper()


def hex_to_int(h: str) -> int:
    return int(h.strip().replace(" ", ""), 16)


# --------------------------------------------------------------------------
# Хэш сообщения
# --------------------------------------------------------------------------

def message_hash(msg: bytes) -> bytes:
    return belt_hash(msg)


def hash_to_e(h: bytes, C: Curve = BIGN256) -> int:
    """e = H(M) mod q (H как 256-битное число little-endian, как в СТБ).
    Если e = 0, берётся e = 1 (иначе e^(-1) при проверке не существует)."""
    e = int.from_bytes(h, "little") % C.q
    return e if e != 0 else 1


# --------------------------------------------------------------------------
# Ключи и ECDH
# --------------------------------------------------------------------------

def generate_keypair(C: Curve = BIGN256, randbits=_system_rng):
    """Секретный ключ d из (0, q) (constant-time), открытый Q = d·G."""
    d = ct_random_scalar(C.q, randbits)
    return d, secure_multiply(C, d, C.G)


def public_key(d: int, C: Curve = BIGN256) -> Point:
    if not 0 < d < C.q:
        raise ValueError("секретный ключ должен быть в диапазоне 0 < d < q")
    return secure_multiply(C, d, C.G)


def validate_public_key(Q: Point, C: Curve = BIGN256) -> bool:
    """Q != O, координаты в поле, Q лежит на кривой (кофактор bign = 1,
    поэтому любая точка кривой лежит в подгруппе порядка q)."""
    return (not Q.inf) and C.is_on_curve(Q)


def ecdh_shared_point(d: int, Q_peer: Point, C: Curve = BIGN256) -> Point:
    """K = d · Q_peer. Чужой открытый ключ проверяется до умножения."""
    if not validate_public_key(Q_peer, C):
        raise ValueError("открытый ключ собеседника не лежит на кривой")
    K = secure_multiply(C, d, Q_peer)
    if K.inf:
        raise ValueError("общий секрет — бесконечно удалённая точка")
    return K


def ecdh_shared_secret(d: int, Q_peer: Point, C: Curve = BIGN256) -> bytes:
    """Итоговый ключ — координата x точки K (32 байта)."""
    return ecdh_shared_point(d, Q_peer, C).x.to_bytes(COORD, "big")


# --------------------------------------------------------------------------
# ЭЦП
# --------------------------------------------------------------------------

def sign_hash(h: bytes, d: int, C: Curve = BIGN256, randbits=_system_rng):
    """Подпись хэш-значения: возвращает (r, s)."""
    q = C.q
    e = hash_to_e(h, C)
    while True:
        k = ct_random_scalar(q, randbits)            # задача варианта 12
        Cpt = secure_multiply(C, k, C.G)             # C = k·G
        r = Cpt.x % q
        s = (r * d + k * e) % q
        # r = 0 или s = 0 — публичные события вероятности ~2^-256
        if r != 0 and s != 0:
            return r, s


def sign(msg: bytes, d: int, C: Curve = BIGN256, randbits=_system_rng):
    return sign_hash(message_hash(msg), d, C, randbits)


def verify_hash(h: bytes, Q: Point, sig, C: Curve = BIGN256) -> bool:
    """Проверка подписи. Все данные публичны — constant-time не требуется."""
    r, s = sig
    q = C.q
    if not (0 < r < q and 0 < s < q):
        return False
    if not validate_public_key(Q, C):
        return False
    e = hash_to_e(h, C)
    v = pow(e, -1, q)
    z1 = s * v % q
    z2 = (-r * v) % q
    Cp = C.add(C.multiply(z1, C.G), C.multiply(z2, Q))
    if Cp.inf:
        return False
    R = Cp.x % q
    return ct_compare_bytes(R.to_bytes(COORD, "big"), r.to_bytes(COORD, "big"))


def verify(msg: bytes, Q: Point, sig, C: Curve = BIGN256) -> bool:
    return verify_hash(message_hash(msg), Q, sig, C)


def signature_to_hex(sig) -> str:
    r, s = sig
    return int_to_hex(r) + int_to_hex(s)


def signature_from_hex(h: str):
    b = bytes.fromhex(h)
    if len(b) != 2 * COORD:
        raise ValueError("подпись должна быть 64 байта (r || s)")
    return int.from_bytes(b[:COORD], "big"), int.from_bytes(b[COORD:], "big")
