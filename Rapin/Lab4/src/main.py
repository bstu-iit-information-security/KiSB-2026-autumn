import hashlib

from ec_algebra import Curve, infinity, int_to_hex, hex_to_int
from ec_ct import secure_multiply, secure_compare
from ec_protocols import (generate_keypair, ecdh_shared_secret, ecdsa_sign,
                          ecdsa_verify, hash_to_scalar)

# secp256k1
CURVE = Curve(
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F",
    "0",
    "7",
    "79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798",
    "483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8",
    "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141",
)

MESSAGES_HEX = [
    "48656c6c6f",
    "4c61623420454344534120766172696174203131",
    "00",
]
EXPECTED_SHA256_HELLO = "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969"

# 2G, 3G (известные значения для secp256k1)
TWO_G_X = "C6047F9441ED7D6D3045406E95C07CD85C778E4B8CEF3CA7ABAC09B95C709EE5"
TWO_G_Y = "1AE168FEA63DC339A3C58419466CEAEEF7F632653266D0E1236431A950CFE52A"
THREE_G_X = "F9308A019258C31049344F85F89D5229B531C845836F99B08601F113BCE036F9"


def fmt(v):
    return int_to_hex(v, CURVE.nbytes)


def show_point(name, P):
    x, y = CURVE.to_affine(P)
    print("{} x: {}".format(name, fmt(x)))
    print("{} y: {}".format(name, fmt(y)))


def self_check():
    G = CURVE.G
    x2, y2 = CURVE.to_affine(secure_multiply(CURVE, 2, G))
    assert (x2, y2) == (hex_to_int(TWO_G_X), hex_to_int(TWO_G_Y))
    assert CURVE.to_affine(secure_multiply(CURVE, 3, G))[0] == hex_to_int(THREE_G_X)

    q = CURVE.q
    scalars = [0, 1, 2, 3, 4, 5, 255, 256, q - 2, q - 1, q,
               hex_to_int("5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A"),
               hex_to_int("123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0")]
    for k in scalars:
        secure = secure_multiply(CURVE, k, G)
        classic = CURVE.multiply(k, G)
        assert secure_compare(CURVE, secure, classic) == 1, hex(k)
        assert CURVE.is_on_curve(secure)
    assert CURVE.is_infinity(secure_multiply(CURVE, q, G))
    assert secure_compare(CURVE, secure_multiply(CURVE, 0, G), infinity()) == 1
    assert secure_compare(CURVE, secure_multiply(CURVE, 2, G), G) == 0

    digest = hashlib.sha256(bytes.fromhex(MESSAGES_HEX[0])).hexdigest()
    assert digest == EXPECTED_SHA256_HELLO
    print("self-check: OK")


def main():
    self_check()

    print("\n=== ECDH ===")
    dA, QA = generate_keypair(CURVE)
    dB, QB = generate_keypair(CURVE)
    show_point("Alice Q", QA)
    show_point("Bob Q  ", QB)
    kA = ecdh_shared_secret(CURVE, dA, QB)
    kB = ecdh_shared_secret(CURVE, dB, QA)
    print("Alice shared: " + fmt(kA))
    print("Bob shared:   " + fmt(kB))
    print("equal: {}".format(kA == kB))
    assert kA == kB

    print("\n=== ECDSA ===")
    d, Q = generate_keypair(CURVE)
    show_point("Public Q", Q)
    for m_hex in MESSAGES_HEX:
        message = bytes.fromhex(m_hex)
        e = hash_to_scalar(CURVE, message)
        r, s = ecdsa_sign(CURVE, e, d)
        ok = ecdsa_verify(CURVE, e, (r, s), Q)

        s_bytes = bytearray(s.to_bytes(CURVE.nbytes, "big"))
        s_bytes[-1] ^= 0x01
        s_bad = int.from_bytes(s_bytes, "big")
        bad = ecdsa_verify(CURVE, e, (r, s_bad), Q)

        print("\nmessage (hex): " + m_hex)
        print("e:             " + fmt(e))
        print("r:             " + fmt(r))
        print("s:             " + fmt(s))
        print("valid:         {}".format(ok))
        print("tampered s:    " + fmt(s_bad))
        print("tampered valid:{}".format(bad))
        assert ok and not bad


if __name__ == "__main__":
    main()