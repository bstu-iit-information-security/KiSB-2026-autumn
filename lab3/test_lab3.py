import pytest
from main import AES128, CipherModes

H = bytes.fromhex

KEY = H("2b7e151628aed2a6abf7158809cf4f3c")
IV = H("000102030405060708090a0b0c0d0e0f")
PT = H("6bc1bee22e409f96e93d7e117393172a")


def test_fips197_block():
    k = H("000102030405060708090a0b0c0d0e0f")
    pt = H("00112233445566778899aabbccddeeff")
    ct = H("69c4e0d86a7b0430d8cdb78070b4c55a")

    aes = AES128(k)

    assert aes.encrypt_block(pt) == ct
    assert aes.decrypt_block(ct) == pt


def test_sp800_38a_ecb_cbc_first_block():
    aes = AES128(KEY)

    assert CipherModes.ecb_encrypt(PT, aes)[:16] == H(
        "3ad77bb40d7a3660a89ecaf32466ef97"
    )

    assert CipherModes.cbc_encrypt(PT, aes, IV)[:16] == H(
        "7649abac8119b246cee98e9b12e9197d"
    )


@pytest.mark.parametrize("n", [0, 1, 15, 16, 17, 31, 32, 100])
def test_roundtrip_and_padding(n):
    m = bytes(range(n))
    aes = AES128(KEY)

    assert len(CipherModes.pad(m)) == (n // 16 + 1) * 16
    assert CipherModes.unpad(CipherModes.pad(m)) == m

    assert CipherModes.ecb_decrypt(
        CipherModes.ecb_encrypt(m, aes), aes
    ) == m

    assert CipherModes.cbc_decrypt(
        CipherModes.cbc_encrypt(m, aes, IV), aes, IV
    ) == m


def test_bad_padding_rejected():
    with pytest.raises(ValueError):
        CipherModes.unpad(b"A" * 15 + b"\x00")

    with pytest.raises(ValueError):
        CipherModes.unpad(b"A" * 14 + b"\x01\x02")