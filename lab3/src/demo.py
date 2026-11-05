import os
from aes_block import encrypt_block, decrypt_block
from modes import (ecb_encrypt, ecb_decrypt, cfb_encrypt, cfb_decrypt,
                   pkcs7_pad, pkcs7_unpad)

KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
IV  = bytes.fromhex("101112131415161718191a1b1c1d1e1f")

# --- Вектор NIST FIPS-197 (AES-128) ---
pt = bytes.fromhex("00112233445566778899aabbccddeeff")
ct = encrypt_block(pt, KEY)
print("AES-128 NIST  ct =", ct.hex())
assert ct.hex() == "69c4e0d86a7b0430d8cdb78070b4c55a"
assert decrypt_block(ct, KEY) == pt
print("AES-128 round-trip OK\n")

# --- PKCS#7 ---
for L in (0, 5, 16, 17, 32):
    msg = os.urandom(L)
    padded = pkcs7_pad(msg)
    assert len(padded) % 16 == 0
    assert pkcs7_unpad(padded) == msg
    print(f"PKCS#7 len={L:2d} -> padded={len(padded):2d}, last={padded[-1]:02x}")
print("PKCS#7 OK\n")

# --- ECB ---
for L in (0, 7, 16, 33):
    msg = os.urandom(L)
    c = ecb_encrypt(msg, KEY)
    assert ecb_decrypt(c, KEY) == msg
print("ECB round-trip OK\n")

# --- CFB (без паддинга, длина сохраняется) ---
for L in (0, 1, 7, 16, 17, 33):
    msg = os.urandom(L)
    c = cfb_encrypt(msg, KEY, IV)
    assert len(c) == len(msg), "CFB не должен менять длину"
    assert cfb_decrypt(c, KEY, IV) == msg
print("CFB round-trip OK (padding не нужен)\n")

# --- Демонстрация: ECB vs CFB на повторяющихся паттернах ---
pattern = b"A" * 16 + b"B" * 16 + b"A" * 16 + b"B" * 16
print("ECB:", ecb_encrypt(pattern, KEY).hex())
print("CFB:", cfb_encrypt(pattern, KEY, IV).hex())
# В ECB блоки 'A'*16 повторяются -> одинаковый шифротекст (уязвимость)
# В CFB одинаковые блоки дают разный шифротекст

# --- Демонстрация: только E_K в CFB-расшифровании ---
# Проверим, что cfb_decrypt не вызывает decrypt_block: подменим его
import modes
_orig = modes.decrypt_block
modes.decrypt_block = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("D_K вызвана!"))
msg = b"CFB decrypt must not call D_K. " * 3
c = cfb_encrypt(msg, KEY, IV)
assert cfb_decrypt(c, KEY, IV) == msg   # исключение не выброшено
modes.decrypt_block = _orig
print("\nCFB-расшифрование использует только E_K — подтверждено")