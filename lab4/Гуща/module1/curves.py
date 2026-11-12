
from .elliptic_curve import EllipticCurve


def get_test_curve():
    return EllipticCurve(
        p=0x11,
        a=0x2,
        b=0x2,
        gx=0x5,
        gy=0x1,
        q=0x13
    )


def get_secp256k1():
    p = int(
        "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        "FFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F", 16
    )

    a = 0x0
    b = 0x7

    gx = int(
        "79BE667EF9DCBBAC55A06295CE870B07"
        "029BFCDB2DCE28D959F2815B16F81798", 16
    )

    gy = int(
        "483ADA7726A3C4655DA4FBFC0E1108A8"
        "FD17B448A68554199C47D08FFB10D4B8", 16
    )

    q = int(
        "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFE"
        "BAAEDCE6AF48A03BBFD25E8CD0364141", 16
    )

    return EllipticCurve(p, a, b, gx, gy, q)
