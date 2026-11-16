import unittest
from unittest.mock import patch

import modes


KEY = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
IV = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
PLAINTEXT = bytes.fromhex(
    "6bc1bee22e409f96e93d7e117393172a"
    "ae2d8a571e03ac9c9eb76fac45af8e51"
    "30c81c46a35ce411e5fbc1191a0a52ef"
    "f69f2445df4f9b17ad2b417be66c3710"
)
ECB_CIPHERTEXT = bytes.fromhex(
    "3ad77bb40d7a3660a89ecaf32466ef97"
    "f5d3d58503b9699de785895a96fdbaaf"
    "43b1cd7f598ece23881b00e3ed030688"
    "7b0c785e27e8ad3f8223207104725dd4"
)
CFB_CIPHERTEXT = bytes.fromhex(
    "3b3fd92eb72dad20333449f8e83cfb4a"
    "c8a64537a0b3a93fcde3cdad9f1ce58b"
    "26751f67a3cbb140b1808cf187a4f4df"
    "c04b05357c5d1c0eeac4c66f9ff7f2e6"
)


class PaddingTests(unittest.TestCase):
    def test_empty_input_gets_a_full_padding_block(self):
        self.assertEqual(modes.pkcs7_pad(b""), bytes([16]) * 16)

    def test_padding_roundtrip_at_block_boundaries(self):
        for length in (0, 1, 15, 16, 17, 31, 32, 33):
            with self.subTest(length=length):
                data = bytes(range(length))
                padded = modes.pkcs7_pad(data)
                count = 16 - length % 16
                self.assertEqual(padded, data + bytes([count]) * count)
                self.assertEqual(modes.pkcs7_unpad(padded), data)

    def test_rejects_invalid_padding(self):
        invalid = (b"", b"a", b"a" * 15 + b"\x00",
                   b"a" * 15 + b"\x11", b"a" * 14 + b"\x01\x02",
                   b"a" * 16 + b"\x01")
        for data in invalid:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    modes.pkcs7_unpad(data)


class ModeTests(unittest.TestCase):
    def test_nist_ecb_vectors_and_full_block_padding(self):
        encrypted = modes.encrypt_ecb(PLAINTEXT, KEY)
        self.assertEqual(encrypted[:64], ECB_CIPHERTEXT)
        self.assertEqual(len(encrypted), 80)
        self.assertEqual(modes.decrypt_ecb(encrypted, KEY), PLAINTEXT)

    def test_nist_cfb128_vectors_including_partial_blocks(self):
        for length in (0, 1, 15, 16, 17, 31, 32, 33, 64):
            with self.subTest(length=length):
                plaintext = PLAINTEXT[:length]
                ciphertext = CFB_CIPHERTEXT[:length]
                self.assertEqual(modes.encrypt_cfb(plaintext, KEY, IV), ciphertext)
                self.assertEqual(modes.decrypt_cfb(ciphertext, KEY, IV), plaintext)

    def test_roundtrip_boundaries_and_large_input(self):
        for length in (0, 1, 15, 16, 17, 31, 32, 33, 4096, 4097):
            with self.subTest(length=length):
                data = bytes(i % 256 for i in range(length))
                ecb = modes.encrypt_ecb(data, KEY)
                self.assertEqual(len(ecb), (length // 16 + 1) * 16)
                self.assertEqual(modes.decrypt_ecb(ecb, KEY), data)
                cfb = modes.encrypt_cfb(data, KEY, IV)
                self.assertEqual(len(cfb), length)
                self.assertEqual(modes.decrypt_cfb(cfb, KEY, IV), data)

    def test_ecb_rejects_invalid_ciphertext_length(self):
        for ciphertext in (b"", b"x", b"x" * 15, b"x" * 17):
            with self.subTest(length=len(ciphertext)):
                with self.assertRaises(ValueError):
                    modes.decrypt_ecb(ciphertext, KEY)

    def test_ecb_rejects_invalid_decrypted_padding(self):
        # Build valid AES ciphertext for a block with invalid PKCS#7 bytes.
        bad_block = b"a" * 14 + b"\x01\x02"
        ciphertext = modes.aes128.encrypt_block(bad_block, KEY)
        with self.assertRaises(ValueError):
            modes.decrypt_ecb(ciphertext, KEY)

    def test_invalid_keys_are_rejected_even_for_empty_input(self):
        for key in (b"", b"x" * 15, b"x" * 17, b"x" * 24, b"x" * 32):
            for operation in (lambda: modes.encrypt_ecb(b"", key),
                              lambda: modes.decrypt_ecb(b"", key),
                              lambda: modes.encrypt_cfb(b"", key, IV),
                              lambda: modes.decrypt_cfb(b"", key, IV)):
                with self.subTest(length=len(key), operation=operation):
                    with self.assertRaises(ValueError):
                        operation()

    def test_invalid_ivs_are_rejected_even_for_empty_input(self):
        for iv in (b"", b"x" * 15, b"x" * 17):
            for operation in (modes.encrypt_cfb, modes.decrypt_cfb):
                with self.subTest(length=len(iv), operation=operation):
                    with self.assertRaises(ValueError):
                        operation(b"", KEY, iv)

    def test_key_and_iv_must_be_bytes_even_for_empty_input(self):
        for key in ("x" * 16, bytearray(16), [0] * 16):
            for operation in (modes.encrypt_ecb, modes.decrypt_ecb):
                with self.subTest(key=key, operation=operation):
                    with self.assertRaises(TypeError):
                        operation(b"", key)
            for operation in (modes.encrypt_cfb, modes.decrypt_cfb):
                with self.subTest(key=key, operation=operation):
                    with self.assertRaises(TypeError):
                        operation(b"", key, IV)
        for iv in ("x" * 16, bytearray(16), [0] * 16):
            for operation in (modes.encrypt_cfb, modes.decrypt_cfb):
                with self.subTest(iv=iv, operation=operation):
                    with self.assertRaises(TypeError):
                        operation(b"", KEY, iv)

    def test_cfb_decryption_never_uses_aes_decrypt_block(self):
        with patch.object(modes.aes128, "decrypt_block", side_effect=AssertionError):
            self.assertEqual(modes.decrypt_cfb(CFB_CIPHERTEXT, KEY, IV), PLAINTEXT)


if __name__ == "__main__":
    unittest.main()
