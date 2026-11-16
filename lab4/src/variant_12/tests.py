"""Модульные тесты: python3 -m unittest tests.py"""

import random
import unittest

import protocols as pr
from belt_hash import belt_hash
from ct import (ct_lt, ct_is_zero, ct_select, ct_cswap, ct_random_scalar,
                naive_random_scalar, secure_multiply, fixed_length_scalar)
from ec import BIGN256 as C, Point


def le(h):
    return int.from_bytes(bytes.fromhex(h), "little")


class TestCurve(unittest.TestCase):
    def test_params(self):
        self.assertTrue(C.is_on_curve(C.G))
        self.assertTrue(C.multiply(C.q, C.G).inf)
        self.assertEqual(C.p, 2 ** 256 - 189)

    def test_group_law(self):
        rnd = random.Random(1)
        for _ in range(5):
            a, b = rnd.randrange(1, C.q), rnd.randrange(1, C.q)
            Pa, Pb = C.multiply(a, C.G), C.multiply(b, C.G)
            self.assertEqual(C.add(Pa, Pb), C.multiply((a + b) % C.q, C.G))
            self.assertEqual(C.double(Pa), C.multiply(2 * a % C.q, C.G))
            self.assertTrue(C.add(Pa, C.neg(Pa)).inf)

    def test_stb_key_vector(self):
        d = le("1F66B5B84B7339674533F0329C74F21834281FED0732429E0C79235FC273E269")
        Q = secure_multiply(C, d, C.G)
        self.assertEqual(Q.x, le("BD1A5650179D79E03FCEE49D4C2BD5DDF54CE46D0CF11E4FF87BF7A890857FD0"))
        self.assertEqual(Q.y, le("7AC6A60361E8C8173491686D461B2826190C2EDA5909054A9AB84D2AB9D99A90"))


class TestBeltHash(unittest.TestCase):
    def test_vectors(self):
        H = bytes.fromhex("B194BAC80A08F53B366D008E584A5DE48504FA9D1BB6C7AC252E72C202FDCE0D"
                          "5BE3D61217B96181FE6786AD716B890B")
        self.assertEqual(belt_hash(H[:13]).hex().upper(),
                         "ABEF9725D4C5A83597A367D14494CC2542F20F659DDFECC961A3EC550CBA8C75")
        self.assertEqual(belt_hash(H[:32]).hex().upper(),
                         "749E4C3653AECE5E48DB4761227742EB6DBE13F4A80F7BEFF1A9CF8D10EE7786")
        self.assertEqual(belt_hash(H[:48]).hex().upper(),
                         "9D02EE446FB6A29FE5C982D4B13AF9D3E90861BC4CEF27CF306BFB0B174A154A")


class TestConstantTime(unittest.TestCase):
    def test_primitives(self):
        self.assertEqual(ct_lt(3, 5), 1)
        self.assertEqual(ct_lt(5, 5), 0)
        self.assertEqual(ct_lt(7, 5), 0)
        self.assertEqual(ct_is_zero(0), 1)
        self.assertEqual(ct_is_zero(9), 0)
        self.assertEqual(ct_select(1, 10, 20), 10)
        self.assertEqual(ct_select(0, 10, 20), 20)
        self.assertEqual(ct_cswap(1, 1, 2), (2, 1))
        self.assertEqual(ct_cswap(0, 1, 2), (1, 2))

    def test_random_scalar_matches_first_valid(self):
        for q in (C.q, 2 ** 255 + 1, 1000):
            for seed in range(50):
                calls = []
                r1 = random.Random(seed)

                def rb(bits, r=r1):
                    calls.append(bits)
                    return r.getrandbits(bits)
                k = ct_random_scalar(q, rb)
                k_naive, _ = naive_random_scalar(q, random.Random(seed).getrandbits)
                self.assertEqual(k, k_naive)
                self.assertTrue(0 < k < q)
                self.assertEqual(len(calls), 100)

    def test_fixed_length(self):
        n = C.q.bit_length()
        for k in (1, 5, 2 ** 100, C.q - 1):
            kk = fixed_length_scalar(k, C.q)
            self.assertEqual(kk.bit_length(), n + 1)
            self.assertEqual(kk % C.q, k)

    def test_ladder(self):
        rnd = random.Random(2)
        for k in [1, 2, 3, C.q - 1] + [rnd.randrange(1, C.q) for _ in range(5)]:
            self.assertEqual(secure_multiply(C, k, C.G), C.multiply(k, C.G))


class TestProtocols(unittest.TestCase):
    def test_ecdh(self):
        da, Qa = pr.generate_keypair()
        db, Qb = pr.generate_keypair()
        self.assertEqual(pr.ecdh_shared_secret(da, Qb), pr.ecdh_shared_secret(db, Qa))
        with self.assertRaises(ValueError):
            pr.ecdh_shared_point(da, Point(Qb.x, (Qb.y + 1) % C.p))

    def test_sign_verify(self):
        d, Q = pr.generate_keypair()
        msg = b"test message"
        sig = pr.sign(msg, d)
        self.assertTrue(pr.verify(msg, Q, sig))
        r, s = sig
        sb = bytearray(s.to_bytes(32, "big"))
        sb[5] ^= 0x10
        self.assertFalse(pr.verify(msg, Q, (r, int.from_bytes(sb, "big"))))
        self.assertFalse(pr.verify(msg + b"!", Q, sig))
        self.assertFalse(pr.verify(msg, Q, (0, s)))
        self.assertFalse(pr.verify(msg, Q, (r, C.q)))

    def test_hex_roundtrip(self):
        sig = (12345, 67890)
        self.assertEqual(pr.signature_from_hex(pr.signature_to_hex(sig)), sig)


if __name__ == "__main__":
    unittest.main()
