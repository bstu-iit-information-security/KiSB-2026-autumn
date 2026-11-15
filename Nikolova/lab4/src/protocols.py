
import secrets
import ec
from ec import q, G
from secure import ct_equal, ct_point_equal, secure_multiply


def gen_keys():
    d = secrets.randbelow(q - 1) + 1
    Q = secure_multiply(d, G)
    return d, Q


def ecdh(d, Q_other):
    K = secure_multiply(d, Q_other)
    x, y = ec.to_affine(K)
    return x


def sign(e, d, k=None):
    e = e % q
    if e == 0:
        e = 1
    while True:
        if k is None:
            k = secrets.randbelow(q - 1) + 1
        C = secure_multiply(k, G)
        x, y = ec.to_affine(C)
        r = x % q
        s = (r * d + k * e) % q
        if r != 0 and s != 0:
            return r, s
        k = None


def verify(e, r, s, Q):
    if not (0 < r < q and 0 < s < q):
        return False
    e = e % q
    if e == 0:
        e = 1
    v = ec.inv(e, q)
    z1 = s * v % q
    z2 = (-r * v) % q
    C = ec.add(ec.multiply(z1, G), ec.multiply(z2, Q))
    if ec.is_inf(C):
        return False
    x, y = ec.to_affine(C)
    R = x % q
    return ct_equal(R, r)
