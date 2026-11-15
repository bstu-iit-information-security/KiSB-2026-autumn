import os
import unittest

import aes
from modes import *

h = bytes.fromhex
K = h("2b7e151628aed2a6abf7158809cf4f3c")
IV = h("000102030405060708090a0b0c0d0e0f")
P = h("6bc1bee22e409f96e93d7e117393172a" "ae2d8a571e03ac9c9eb76fac45af8e51")


class TestAES(unittest.TestCase):
    def test_fips197_c1(self):
        k = bytes(range(16)); p = h("00112233445566778899aabbccddeeff")
        c = h("69c4e0d86a7b0430d8cdb78070b4c55a")
        self.assertEqual(aes.encrypt_block(p, k), c)
        self.assertEqual(aes.decrypt_block(c, k), p)

    def test_fips197_b(self):
        self.assertEqual(aes.encrypt_block(h("3243f6a8885a308d313198a2e0370734"), K),
                         h("3925841d02dc09fbdc118597196a0b32"))

    def test_last_round_key(self):   
        self.assertEqual(bytes(aes.expand_key(K)[10]), h("d014f9a8c9ee2589e13f0cc8b6630ca6"))

    def test_random_roundtrip(self):
        for _ in range(50):
            k, p = os.urandom(16), os.urandom(16)
            self.assertEqual(aes.decrypt_block(aes.encrypt_block(p, k), k), p)

    def test_bad_sizes(self):
        with self.assertRaises(ValueError): aes.encrypt_block(b"x" * 15, K)
        with self.assertRaises(ValueError): aes.encrypt_block(b"x" * 16, b"short")


class TestModes(unittest.TestCase):
    def test_ecb_nist(self):
        self.assertEqual(ecb_encrypt(P, K, padding=False),
                         h("3ad77bb40d7a3660a89ecaf32466ef97" "f5d3d58503b9699de785895a96fdbaaf"))

    def test_cbc_nist(self):
        self.assertEqual(cbc_encrypt(P, K, IV, padding=False),
                         h("7649abac8119b246cee98e9b12e9197d" "5086cb9b507219ee95db113a917678b2"))

    def test_roundtrip_all_lengths(self):
        for n in range(0, 70):
            m = os.urandom(n)
            self.assertEqual(ecb_decrypt(ecb_encrypt(m, K), K), m)
            self.assertEqual(cbc_decrypt(cbc_encrypt(m, K, IV), K, IV), m)

    def test_padding_lengths(self):
        self.assertEqual(len(pad(b"a" * 15)), 16)
        self.assertEqual(len(pad(b"a" * 16)), 32)     
        self.assertEqual(pad(b"a" * 16)[-16:], b"\x10" * 16)
        self.assertEqual(len(pad(b"a" * 17)), 32)

    def test_unpad_errors(self):
        for bad in (bytes(16), bytes(15) + b"\x11", bytes(12) + b"\x01\x02\x03\x04", b"", b"abc"):
            with self.assertRaises(PaddingError): unpad(bad)

    def test_iv_strict(self):
        for bad in (None, bytes(15), bytes(17), "0123456789abcdef", 5):
            with self.assertRaises(IVError): cbc_encrypt(b"x", K, bad)
            with self.assertRaises(IVError): cbc_decrypt(bytes(16), K, bad)

    def test_ct_length(self):
        for bad in (b"", bytes(17)):
            with self.assertRaises(CiphertextError): cbc_decrypt(bad, K, IV)
            with self.assertRaises(CiphertextError): ecb_decrypt(bad, K)

    def test_chain(self):
        m = b"chain test message, 3 blocks long!!"
        ct = cbc_encrypt(m, K, IV)
        self.assertTrue(cbc_verify_chain(ct, K, IV, pad(m)))
        t = bytearray(ct); t[20] ^= 1
        self.assertFalse(cbc_verify_chain(bytes(t), K, IV, pad(m)))

    def test_ecb_pattern_cbc_no_pattern(self):
        m = b"A" * 64
        e = ecb_encrypt(m, K, padding=False)
        c = cbc_encrypt(m, K, IV, padding=False)
        self.assertEqual(e[:16], e[16:32])
        self.assertNotEqual(c[:16], c[16:32])

    def test_against_reference_lib(self):   
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes as m
        except ImportError:
            self.skipTest("cryptography не установлена")
        for n in (0, 1, 15, 16, 17, 100):
            data = os.urandom(n); k = os.urandom(16); iv = os.urandom(16)
            p = pad(data)
            ref = Cipher(algorithms.AES(k), m.CBC(iv)).encryptor()
            self.assertEqual(cbc_encrypt(data, k, iv), ref.update(p) + ref.finalize())
            ref = Cipher(algorithms.AES(k), m.ECB()).encryptor()
            self.assertEqual(ecb_encrypt(data, k), ref.update(p) + ref.finalize())


if __name__ == "__main__":
    unittest.main(verbosity=2)
