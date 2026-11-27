import re
import sys

from belt import belt_hash
from curve import G, O, Q, add, double, multiply
from ladder import ladder
from protocols import _signature, encode, keypair, le, shared, sign, verify

MESSAGE = "b194bac80a08f53b366d008e58"
HASH = "abef9725d4c5a83597a367d14494cc2542f20f659ddfecc961a3ec550cba8c75"
TEST_D = "1f66b5b84b7339674533f0329c74f21834281fed0732429e0c79235fc273e269"
TEST_X = "bd1a5650179d79e03fcee49d4c2bd5ddf54ce46d0cf11e4ff87bf7a890857fd0"
TEST_Y = "7ac6a60361e8c8173491686d461b2826190c2eda5909054a9ab84d2ab9d99a90"
TEST_SIG = ("e36b7f0377ae4c524027c387fadf1b20"
            "ce72f1530b71f2b5fd3a8c584fe2e1aed20082e30c8af65011f4fb54649dfd3d")


def check(ok, label):
    if not ok:
        raise RuntimeError(label)
    print(label, "OK")


def reference_tests():
    digest = belt_hash(bytes.fromhex(MESSAGE))
    check(digest.hex() == HASH, "belt-hash A.23-1")
    d = le(bytes.fromhex(TEST_D))
    public = ladder(d, G)
    check(encode(public.x).hex() == TEST_X and encode(public.y).hex() == TEST_Y,
          "BIGN Г.1")
    sig = bytes.fromhex(TEST_SIG)
    k = (le(sig[16:]) + le(digest) + ((1 << 128) + le(sig[:16]))*d) % Q
    check(_signature(d, digest, k) == sig and verify(public, digest, sig),
          "BIGN Г.2")
    check(all(ladder(n, G) == multiply(n, G) for n in (0, 1, 2, Q-1, Q))
          and add(G, O) == G and double(G) == add(G, G), "Арифметика и лестница")


def demo(message):
    alice, qa = keypair()
    bob, qb = keypair()
    for name, point in (("QA", qa), ("QB", qb)):
        print(name + ".x =", encode(point.x).hex())
        print(name + ".y =", encode(point.y).hex())
    a, b = shared(alice, qb), shared(bob, qa)
    print("XA =", a.hex())
    print("XB =", b.hex())
    check(a == b, "ECDH")
    digest = belt_hash(message)
    sig = sign(alice, digest)
    print("M =", message.hex())
    print("H =", digest.hex())
    print("s0 =", sig[:16].hex())
    print("s1 =", sig[16:].hex())
    check(verify(qa, digest, sig), "Подпись принята")
    damaged = bytearray(sig)
    damaged[16] ^= 1
    print("s1' =", damaged[16:].hex())
    check(not verify(qa, digest, damaged), "Искажённая подпись отклонена")


if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else MESSAGE
    if len(sys.argv) > 2 or not re.fullmatch(r"(?:[0-9a-fA-F]{2})*", raw):
        sys.exit("Запуск: python main.py [сообщение в hex, по две цифры на байт]")
    reference_tests()
    demo(bytes.fromhex(raw))
