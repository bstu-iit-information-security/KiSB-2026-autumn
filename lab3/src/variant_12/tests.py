"""Модульные тесты: python3 -m unittest tests.py"""

import random
import unittest

from belt import BeltCipher, encrypt_block, decrypt_block
from modes import (pkcs7_pad, pkcs7_unpad, ecb_encrypt, ecb_decrypt,
                   OfbGamma, ofb_encrypt, ofb_decrypt, ofb_encrypt_naive)


class TestBelt(unittest.TestCase):
    def test_stb_a1_encrypt(self):
        k = bytes.fromhex("E9DEE72C8F0C0FA62DDB49F46F73964706075316ED247A3739CBA38303A98BF6")
        x = bytes.fromhex("B194BAC80A08F53B366D008E584A5DE4")
        y = bytes.fromhex("69CCA1C93557C9E3D66BC3E0FA88FA6E")
        self.assertEqual(encrypt_block(x, k), y)
        self.assertEqual(BeltCipher(k).encrypt_block(x), y)

    def test_stb_a4_decrypt(self):
        k = bytes.fromhex("92BD9B1CE5D141015445FBC95E4D0EF2682080AA227D642F2687F93490405511")
        y = bytes.fromhex("E12BDC1AE28257EC703FCCF095EE8DF1")
        x = bytes.fromhex("0DC5300600CAB840B38448E5E993F421")
        self.assertEqual(decrypt_block(y, k), x)
        self.assertEqual(BeltCipher(k).decrypt_block(y), x)

    def test_roundtrip_random(self):
        rnd = random.Random(0)
        for _ in range(50):
            k = rnd.randbytes(32) if hasattr(rnd, "randbytes") else bytes(rnd.getrandbits(8) for _ in range(32))
            x = bytes(rnd.getrandbits(8) for _ in range(16))
            c = BeltCipher(k)
            self.assertEqual(c.encrypt_block(x), encrypt_block(x, k))
            self.assertEqual(c.decrypt_block(c.encrypt_block(x)), x)

    def test_bad_sizes(self):
        with self.assertRaises(ValueError):
            encrypt_block(b"\x00" * 15, b"\x00" * 32)
        with self.assertRaises(ValueError):
            encrypt_block(b"\x00" * 16, b"\x00" * 16)


class TestModes(unittest.TestCase):
    KEY = bytes(range(32))
    IV = bytes(range(100, 116))

    def test_padding_lengths(self):
        for n in range(0, 50):
            p = bytes(n)
            padded = pkcs7_pad(p)
            self.assertEqual(len(padded) % 16, 0)
            self.assertTrue(1 <= len(padded) - n <= 16)
            self.assertEqual(pkcs7_unpad(padded), p)
        self.assertEqual(pkcs7_pad(b"A" * 16), b"A" * 16 + b"\x10" * 16)

    def test_bad_padding(self):
        for bad in (b"", b"A" * 15 + b"\x00", b"A" * 15 + b"\x11",
                    b"A" * 12 + b"\x03\x04\x04\x04", b"A" * 17):
            with self.assertRaises(ValueError):
                pkcs7_unpad(bad)

    def test_ecb_ofb_roundtrip(self):
        for n in (0, 1, 15, 16, 17, 33, 100):
            p = bytes((i * 7) & 255 for i in range(n))
            self.assertEqual(ecb_decrypt(ecb_encrypt(p, self.KEY), self.KEY), p)
            c = ofb_encrypt(p, self.KEY, self.IV)
            self.assertEqual(len(c), n)
            self.assertEqual(ofb_decrypt(c, self.KEY, self.IV), p)
            self.assertEqual(ofb_encrypt_naive(p, self.KEY, self.IV), c)

    def test_ofb_first_block_is_ek_iv(self):
        g = OfbGamma(self.KEY, self.IV).take(32)
        i1 = encrypt_block(self.IV, self.KEY)
        self.assertEqual(g[:16], i1)
        self.assertEqual(g[16:], encrypt_block(i1, self.KEY))

    def test_ofb_precompute_in_parts(self):
        gen = OfbGamma(self.KEY, self.IV)
        gen.precompute(40)
        got = gen.take(5) + gen.take(50) + gen.take(9)
        self.assertEqual(got, OfbGamma(self.KEY, self.IV).take(64))

    def test_ecb_equal_blocks(self):
        c = ecb_encrypt(b"X" * 32, self.KEY, pad=False)
        self.assertEqual(c[:16], c[16:])
        o = ofb_encrypt(b"X" * 32, self.KEY, self.IV)
        self.assertNotEqual(o[:16], o[16:])

    def test_bad_iv(self):
        with self.assertRaises(ValueError):
            ofb_encrypt(b"abc", self.KEY, b"short")


if __name__ == "__main__":
    unittest.main()
