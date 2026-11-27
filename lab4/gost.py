from secrets import randbelow
from sys import argv

P_MOD = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFD97", 16)
A_COEF = int("C2173F1513981673AF4892C23035A27CE25E2013BF95AA33B22C656F277E7335", 16)
B_COEF = int("295F9BAE7428ED9CCC20E7C359A9D41A22FCCD9108E17BF7BA9337A6F8AE9513", 16)
ORDER = int("400000000000000000000000000000000FD8CDDFC87B6635C115AF556C360C67", 16)
G = (
    int("91E38443A5E82C0D880923425712B2BB658B9196932E02C78B2582FE742DAA28", 16),
    int("32879423AB1A0375895786C4BB46E9565FDE0B5344766740AF268ADB32322E5C", 16),
    1,
)
INF = (0, 1, 0)

D_A = int("123456789ABCDEF0123456789ABCDEF", 16)
D_B = int("FEDCBA9876543210FEDCBA9876543210", 16)
MESSAGE = bytes.fromhex("616263")
DIGEST = bytes.fromhex("BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD")


def inv(value, modulus):
    return pow(value, modulus - 2, modulus)


def is_infinity(point):
    return point[2] == 0


def affine(point):
    z_inv = inv(point[2], P_MOD)
    z2 = z_inv * z_inv % P_MOD
    return point[0] * z2 % P_MOD, point[1] * z2 * z_inv % P_MOD


def double(point):
    x, y, z = point
    if z == 0 or y == 0:
        return INF
    yy = y * y % P_MOD
    s = 4 * x * yy % P_MOD
    m = (3 * x * x + A_COEF * pow(z, 4, P_MOD)) % P_MOD
    x3 = (m * m - 2 * s) % P_MOD
    y3 = (m * (s - x3) - 8 * yy * yy) % P_MOD
    z3 = 2 * y * z % P_MOD
    return x3, y3, z3


def add(p1, p2):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    if z1 == 0:
        return p2
    if z2 == 0:
        return p1
    z1z1 = z1 * z1 % P_MOD
    z2z2 = z2 * z2 % P_MOD
    u1 = x1 * z2z2 % P_MOD
    u2 = x2 * z1z1 % P_MOD
    s1 = y1 * z2 * z2z2 % P_MOD
    s2 = y2 * z1 * z1z1 % P_MOD
    h = (u2 - u1) % P_MOD
    r = (s2 - s1) % P_MOD
    if h == 0:
        return double(p1) if r == 0 else INF
    hh = h * h % P_MOD
    hhh = h * hh % P_MOD
    v = u1 * hh % P_MOD
    x3 = (r * r - hhh - 2 * v) % P_MOD
    y3 = (r * (v - x3) - s1 * hhh) % P_MOD
    z3 = h * z1 * z2 % P_MOD
    return x3, y3, z3


def cswap(p1, p2, bit):
    mask = -bit
    return (
        tuple(a ^ (mask & (a ^ b)) for a, b in zip(p1, p2)),
        tuple(b ^ (mask & (a ^ b)) for a, b in zip(p1, p2)),
    )


def multiply(scalar, point):
    if scalar == 0:
        return INF
    r0, r1 = INF, point
    for i in range(scalar.bit_length() - 1, -1, -1):
        bit = (scalar >> i) & 1
        r0, r1 = cswap(r0, r1, bit)
        r1 = add(r0, r1)
        r0 = double(r0)
        r0, r1 = cswap(r0, r1, bit)
    return r0


def blinded_multiply(scalar, point):
    return multiply(scalar + randbelow(ORDER - 1) * ORDER, point)


def public_key(private):
    return blinded_multiply(private, G)


def shared_secret(private, peer_public):
    return affine(blinded_multiply(private, peer_public))[0]


def digest_value(digest):
    value = int.from_bytes(digest, "little") % ORDER
    return value or 1


def sign(private, digest):
    e = digest_value(digest)
    while True:
        k = randbelow(ORDER - 1) + 1
        x = affine(blinded_multiply(k, G))[0]
        r = x % ORDER
        s = (private * r + k * e) % ORDER
        if r and s:
            return r, s


def verify(public, digest, signature):
    r, s = signature
    if not 0 < s < ORDER or not 0 < r < ORDER:
        return False
    e = digest_value(digest)
    v = inv(e, ORDER)
    z1 = s * v % ORDER
    z2 = -r * v % ORDER
    point = add(multiply(z1, G), multiply(z2, public))
    if is_infinity(point):
        return False
    return affine(point)[0] % ORDER == r


def hex32(value):
    return f"{value:064X}"


def hex_point(point):
    x, y = affine(point)
    return hex32(x), hex32(y)


def main():
    d_a = int(argv[1], 16) if len(argv) > 1 else D_A
    d_b = int(argv[2], 16) if len(argv) > 2 else D_B
    digest = bytes.fromhex(argv[3]) if len(argv) > 3 else DIGEST
    if not 0 < d_a < ORDER or not 0 < d_b < ORDER:
        raise ValueError("private key must be in (0, q)")
    qa = public_key(d_a)
    qb = public_key(d_b)
    ka = shared_secret(d_a, qb)
    kb = shared_secret(d_b, qa)
    r, s = sign(d_a, digest)
    if len(argv) < 4:
        print("message", MESSAGE.hex().upper())
    print("digest", digest.hex().upper())
    print("base on curve", (G[1] * G[1] - (G[0] ** 3 + A_COEF * G[0] + B_COEF)) % P_MOD == 0)
    print("order*G infinity", is_infinity(multiply(ORDER, G)))
    print("Q_A", *hex_point(qa))
    print("Q_B", *hex_point(qb))
    print("shared", hex32(ka), ka == kb)
    print("signature", hex32(r), hex32(s))
    print("verify", verify(qa, digest, (r, s)))
    print("tampered", verify(qa, digest, (r, s ^ 1)))


if __name__ == "__main__":
    main()
