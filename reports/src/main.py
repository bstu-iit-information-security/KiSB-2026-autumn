
from aes128 import BLOCK_SIZE, encrypt_block, decrypt_block
from modes import encrypt_ecb, decrypt_ecb, encrypt_cbc, decrypt_cbc

def hamming_distance_bits(b1: bytes, b2: bytes) -> int:
    return sum(bin(x ^ y).count("1") for x, y in zip(b1, b2))


def flip_single_bit(data: bytes, byte_index: int, bit_index: int = 0) -> bytes:
    mutable = bytearray(data)
    mutable[byte_index] ^= (1 << bit_index)
    return bytes(mutable)


def test_nist_fips197_vector() -> None:
    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    pt = bytes.fromhex("00112233445566778899aabbccddeeff")
    expected_ct = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")

    ct = encrypt_block(pt, key)
    decrypted_pt = decrypt_block(ct, key)

    print("=== 1. Проверка эталонного вектора NIST FIPS-197 ===")
    print(f"Ключ (Hex):             {key.hex()}")
    print(f"Открытый блок (Hex):    {pt.hex()}")
    print(f"Шифроблок (Hex):        {ct.hex()}")
    print(f"Ожидаемый блок (Hex):   {expected_ct.hex()}")
    assert ct == expected_ct, "Ошибка: шифроблок не совпадает с эталоном FIPS-197!"
    assert decrypted_pt == pt, "Ошибка: расшифрованный блок не совпадает с исходным!"
    print("Статус: УСПЕШНО (100% совпадение со стандартом FIPS-197)\n")


def analyze_diffusion_variant_13() -> None:
    print("=== 2. Анализ диффузии (Вариант 13: изменение 1 бита в середине сообщения) ===")

    key = b"AES128SecretKey!"  # 16 байт (128 бит)
    iv = b"InitVector128Bit"   # 16 байт (128 бит)

    pt_original = (
        b"Block_0_Data_AAA"
        b"Block_1_Data_BBB"
        b"Block_2_Data_CCC"
        b"Block_3_Data_DDD"
    )

    target_byte_idx = 24
    pt_modified = flip_single_bit(pt_original, byte_index=target_byte_idx, bit_index=0)

    diff_input_bits = hamming_distance_bits(pt_original, pt_modified)
    print(f"Длина открытого текста: {len(pt_original)} байт (4 блока по 16 байт)")
    print(f"Точка модификации:      Байт #{target_byte_idx} (Блок #{target_byte_idx // BLOCK_SIZE}), инвертирован 1 бит")
    print(f"Разница во входных текстах: {diff_input_bits} бит\n")

    ct_ecb_1 = encrypt_ecb(pt_original, key)
    ct_ecb_2 = encrypt_ecb(pt_modified, key)

    ct_cbc_1 = encrypt_cbc(pt_original, key, iv)
    ct_cbc_2 = encrypt_cbc(pt_modified, key, iv)

    assert decrypt_ecb(ct_ecb_1, key) == pt_original
    assert decrypt_cbc(ct_cbc_1, key, iv) == pt_original

    num_blocks = len(ct_ecb_1) // BLOCK_SIZE

    print(f"{'Блок':<8} | {'ECB: изменено бит (%)':<28} | {'CBC: изменено бит (%)':<28}")
    print("-" * 70)

    for b in range(num_blocks):
        start, end = b * BLOCK_SIZE, (b + 1) * BLOCK_SIZE

        ecb_diff = hamming_distance_bits(ct_ecb_1[start:end], ct_ecb_2[start:end])
        cbc_diff = hamming_distance_bits(ct_cbc_1[start:end], ct_cbc_2[start:end])

        ecb_pct = (ecb_diff / 128) * 100
        cbc_pct = (cbc_diff / 128) * 100

        block_label = f"#{b}" + (" *" if b == target_byte_idx // BLOCK_SIZE else "")
        print(
            f"{block_label:<8} | "
            f"{ecb_diff:>3}/128 бит ({ecb_pct:>5.1f}%)        | "
            f"{cbc_diff:>3}/128 бит ({cbc_pct:>5.1f}%)"
        )

    print("-" * 70)
    total_bits = len(ct_ecb_1) * 8
    total_ecb_diff = hamming_distance_bits(ct_ecb_1, ct_ecb_2)
    total_cbc_diff = hamming_distance_bits(ct_cbc_1, ct_cbc_2)
    print(f"ИТОГО    | {total_ecb_diff:>3}/{total_bits} бит ({total_ecb_diff/total_bits*100:>5.1f}%)        | "
          f"{total_cbc_diff:>3}/{total_bits} бит ({total_cbc_diff/total_bits*100:>5.1f}%)")
    print("(* — блок, в котором был изменен 1 бит открытого текста)")


if __name__ == "__main__":
    test_nist_fips197_vector()
    analyze_diffusion_variant_13()