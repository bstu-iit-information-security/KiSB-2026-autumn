from secrets import randbelow
from curve import A, B, G, P, Q, add, affine, multiply
from protection import secure_multiply


def scalar():
    return 1 + randbelow(Q - 1)


def keypair():
    d = scalar()
    return d, secure_multiply(d, G)


def valid(t):
    if t.z == 0:
        return False
    x, y = affine(t)
    return (y*y - x**3 - A*x - B) % P == 0 and multiply(Q, t).z == 0


def ecdh(d, peer):
    if not valid(peer):
        raise ValueError("Недопустимый открытый ключ")
    return secure_multiply(d, peer)


def sign_once(d, e, k):
    x, _ = affine(secure_multiply(k, G))
    r = x % Q
    return r, (r*d + k*(e % Q or 1)) % Q


def sign(d, e):
    while True:
        r, s = sign_once(d, e, scalar())
        if r and s:
            return r, s


def verify(public, e, r, s):
    if not (0 < r < Q and 0 < s < Q and valid(public)):
        return False
    v = pow(e % Q or 1, -1, Q)
    c = add(multiply(s*v % Q, G), multiply(-r*v % Q, public))
    return c.z != 0 and affine(c)[0] % Q == r
