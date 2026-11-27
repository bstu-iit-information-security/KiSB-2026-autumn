import hmac
import secrets

from belt import belt_hash
from curve import G, Q, add, multiply, valid
from ladder import ladder

OID = bytes.fromhex("06092a7000020022651f51")


def scalar():
    return secrets.randbelow(Q-1) + 1


def le(data):
    return int.from_bytes(data, "little")


def encode(value):
    return value.to_bytes(32, "little")


def keypair():
    d = scalar()
    return d, ladder(d, G)


def shared(d, peer):
    if not 0 < d < Q or not valid(peer):
        raise ValueError("Недопустимый ключ ECDH")
    return encode(ladder(d, peer).x)


def challenge(point, digest):
    return belt_hash(OID + encode(point.x) + digest)[:16]


def _signature(d, digest, k):
    s0 = challenge(ladder(k, G), digest)
    t = (1 << 128) + le(s0)
    s1 = (k - le(digest) - t*d) % Q
    return s0 + encode(s1)


def sign(d, digest):
    if not 0 < d < Q or len(digest) != 32:
        raise ValueError("Недопустимый ключ или длина хэша")
    return _signature(d, digest, scalar())


def verify(public, digest, sig):
    if len(digest) != 32 or len(sig) != 48 or not valid(public):
        return False
    s0, s1 = sig[:16], le(sig[16:])
    if s1 >= Q:
        return False
    u = (s1 + le(digest)) % Q
    t = (1 << 128) + le(s0)
    point = add(multiply(u, G), multiply(t, public))
    return not point.infinity and hmac.compare_digest(challenge(point, digest), s0)
