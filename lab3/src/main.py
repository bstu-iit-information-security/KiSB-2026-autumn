import os
import AES_128
from modes import ecb_encrypt, ecb_decrypt, cfb_encrypt, cfb_decrypt, pad, unpad

key = bytes(range(16))
iv = bytes(range(100, 116))
h = bytes.fromhex


def title(s):
    print(f"\n=== {s} " + "=" * (60 - len(s)))

def check(name, ok):
    assert ok, name
    print(f"  {name:<50}[ OK ]")

def blocks(c):
    return [c[i:i + 16] for i in range(0, len(c), 16)]


print(f"AES-128 | ECB + CFB | key={key.hex()} | iv={iv.hex()}")

# проверка по эталонам
title("1. Эталонные векторы")
k = h("2b7e151628aed2a6abf7158809cf4f3c")
v_iv = h("000102030405060708090a0b0c0d0e0f")
v_pt = h("6bc1bee22e409f96e93d7e117393172aae2d8a571e03ac9c9eb76fac45af8e5130c81c46a35ce411e5fbc1191a0a52eff69f2445df4f9b17ad2b417be66c3710")
v_ecb = h("3ad77bb40d7a3660a89ecaf32466ef97f5d3d58503b9699de785895a96fdbaaf43b1cd7f598ece23881b00e3ed0306887b0c785e27e8ad3f8223207104725dd4")
v_cfb = h("3b3fd92eb72dad20333449f8e83cfb4ac8a64537a0b3a93fcde3cdad9f1ce58b26751f67a3cbb140b1808cf187a4f4dfc04b05357c5d1c0eeac4c66f9ff7f2e6")
fk, fp, fc = h("000102030405060708090a0b0c0d0e0f"), h("00112233445566778899aabbccddeeff"), h("69c4e0d86a7b0430d8cdb78070b4c55a")
check("AES block FIPS-197 (encrypt)", AES_128.encrypt_block(fp, fk) == fc)
check("AES block FIPS-197 (decrypt)", AES_128.decrypt_block(fc, fk) == fp)
check("AES block SP 800-38A ECB, 4 блока", b"".join(AES_128.encrypt_block(b, k) for b in blocks(v_pt)) == v_ecb)
check("CFB-128 SP 800-38A (encrypt)", cfb_encrypt(v_pt, k, v_iv) == v_cfb)
check("CFB-128 SP 800-38A (decrypt)", cfb_decrypt(v_cfb, k, v_iv) == v_pt)
check("CFB неполный хвост = префикс эталона (37 байт)", cfb_encrypt(v_pt[:37], k, v_iv) == v_cfb[:37])

# шифрование / расшифрование
title("2. Тестовая строка")
msg = "Привет, AES! Лаба 3".encode()
ce, cc = ecb_encrypt(msg, key), cfb_encrypt(msg, key, iv)
print(f"  открытый ({len(msg)} Б): {msg.decode()}")
print(f"  ECB ({len(ce)} Б): {ce.hex()}")
print(f"  CFB ({len(cc)} Б): {cc.hex()}")
check("ECB расшифровано верно", ecb_decrypt(ce, key) == msg)
check("CFB расшифровано верно", cfb_decrypt(cc, key, iv) == msg)

# padding
title("3. Padding PKCS#7")
print("  длина | +pad | после pad | ECB ct | CFB ct | расшифровка")
for n in (5, 16, 21):
    m = os.urandom(n)
    c = ecb_encrypt(m, key)
    ok = ecb_decrypt(c, key) == m and unpad(pad(m)) == m
    print(f"  {n:5d} | {len(pad(m)) - n:4d} | {len(pad(m)):9d} | {len(c):6d} | "
          f"{len(cfb_encrypt(m, key, iv)):6d} | {'OK' if ok else 'FAIL'}")
    assert ok
for bad in (b"A" * 15 + b"\x00", b"A" * 14 + b"\x01\x02", b"A" * 16):
    try:
        unpad(bad)
        raise SystemExit("unpad принял неверный padding")
    except ValueError:
        pass
check("unpad отклоняет неверный padding", True)

# CFB
title("4. CFB: неполный последний блок")
print("  длина | полных блоков | хвост, Б | ct, Б | расшифровка")
for n in (1, 15, 16, 17, 31, 33, 100):
    m = os.urandom(n)
    c = cfb_encrypt(m, key, iv)
    full = n - n % 16
    ok = len(c) == n and cfb_decrypt(c, key, iv) == m and c[:full] == cfb_encrypt(m[:full], key, iv)
    print(f"  {n:5d} | {n // 16:13d} | {n % 16:8d} | {len(c):5d} | {'OK' if ok else 'FAIL'}")
    assert ok

# ECB CFB
title("5. ECB vs CFB на повторяющихся блоках")
p = b"QWERTY QWERTY ?!" * 8
be, bc = blocks(ecb_encrypt(p, key)), blocks(cfb_encrypt(p, key, iv))
print("  блок | ECB (первые 8 байт)  | CFB (первые 8 байт)")
for i in range(len(be)):
    cf = bc[i][:8].hex() if i < len(bc) else "-"
    print(f"  {i + 1:4d} | {be[i][:8].hex():<20} | {cf}")

print(f"\n  уникальных блоков: ECB {len(set(be))} из {len(be)}, CFB {len(set(bc))} из {len(bc)}")
print("  (9-й блок ECB — это padding)")
