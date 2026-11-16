"""Tests against the AES-128 examples in FIPS 197."""

import unittest


class AES128Tests(unittest.TestCase):
    def test_fips_197_encryption(self):
        from aes128 import encrypt_block

        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        plaintext = bytes.fromhex("00112233445566778899aabbccddeeff")
        expected = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
        self.assertEqual(encrypt_block(plaintext, key), expected)

    def test_fips_197_decryption(self):
        from aes128 import decrypt_block

        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        ciphertext = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
        expected = bytes.fromhex("00112233445566778899aabbccddeeff")
        self.assertEqual(decrypt_block(ciphertext, key), expected)

    def test_nist_sp800_38a_vector_both_directions(self):
        from aes128 import decrypt_block, encrypt_block

        key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
        plaintext = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
        ciphertext = bytes.fromhex("3ad77bb40d7a3660a89ecaf32466ef97")
        self.assertEqual(encrypt_block(plaintext, key), ciphertext)
        self.assertEqual(decrypt_block(ciphertext, key), plaintext)

    def test_wrong_lengths_are_rejected(self):
        from aes128 import decrypt_block, encrypt_block

        for function in (encrypt_block, decrypt_block):
            for length in (0, 1, 15, 17, 24, 32):
                for block, key in ((bytes(length), bytes(16)),
                                   (bytes(16), bytes(length))):
                    with self.subTest(function=function.__name__, length=length,
                                      block_length=len(block)):
                        with self.assertRaises(ValueError):
                            function(block, key)

    def test_non_bytes_are_rejected(self):
        from aes128 import decrypt_block, encrypt_block

        for function in (encrypt_block, decrypt_block):
            for invalid in (None, "x" * 16, bytearray(16), list(range(16))):
                for block, key in ((invalid, bytes(16)), (bytes(16), invalid)):
                    with self.subTest(function=function.__name__, invalid=type(invalid),
                                      invalid_block=block is invalid):
                        with self.assertRaises(TypeError):
                            function(block, key)

    def test_fips_key_expansion(self):
        from aes128 import _expand_key

        words = _expand_key(bytes.fromhex("000102030405060708090a0b0c0d0e0f"))
        self.assertEqual(len(words), 44)
        self.assertTrue(all(len(word) == 4 for word in words))
        self.assertEqual(bytes(sum(words[4:8], [])),
                         bytes.fromhex("d6aa74fdd2af72fadaa678f1d6ab76fe"))
        self.assertEqual(bytes(sum(words[40:44], [])),
                         bytes.fromhex("13111d7fe3944a17f307a78b4d2b30c5"))

    def test_fips_first_round_intermediate_states(self):
        from aes128 import _add_round_key, _expand_key, _mix_columns, _shift_rows, _sub_bytes

        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        state = list(bytes.fromhex("00112233445566778899aabbccddeeff"))
        state = _add_round_key(state, _expand_key(key), 0)
        self.assertEqual(bytes(state).hex(), "00102030405060708090a0b0c0d0e0f0")
        state = _sub_bytes(state)
        self.assertEqual(bytes(state).hex(), "63cab7040953d051cd60e0e7ba70e18c")
        state = _shift_rows(state)
        self.assertEqual(bytes(state).hex(), "6353e08c0960e104cd70b751bacad0e7")
        state = _mix_columns(state)
        self.assertEqual(bytes(state).hex(), "5f72641557f5bc92f7be3b291db9f91a")
        state = _add_round_key(state, _expand_key(key), 1)
        self.assertEqual(bytes(state).hex(), "89d810e8855ace682d1843d8cb128fe4")

    def test_fips_field_multiplication(self):
        from aes128 import _multiply

        self.assertEqual(_multiply(0x57, 0x13), 0xfe)


if __name__ == "__main__":
    unittest.main()
