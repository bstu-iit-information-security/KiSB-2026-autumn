from belthash import BELT_SBOX, belt_block, belt_hash
from curve import A, B, GX, GY, P, Q, Curve, GENERATOR
from protection import FixedWindow, PointBlinding
from protocols import Protocols

MESSAGE_HEX = "B194BAC80A08F53B366D008E58"
CHANGED_MESSAGE_HEX = "B094BAC80A08F53B366D008E58"
TEST_PRIVATE = int.from_bytes(bytes.fromhex("1F66B5B84B7339674533F0329C74F21834281FED0732429E0C79235FC273E269"), "little")
TEST_NONCE = int.from_bytes(bytes.fromhex("4C0E74B2CD5811AD21F23DE7E0FA742C3ED6EC483C461CE15C33A77AA308B7D2"), "little")
TEST_SIGNATURE_HEX = "E36B7F0377AE4C524027C387FADF1B20CE72F1530B71F2B5FD3A8C584FE2E1AED20082E30C8AF65011F4FB54649DFD3D"
EXPECTED_PUBLIC_HEX = "BD1A5650179D79E03FCEE49D4C2BD5DDF54CE46D0CF11E4FF87BF7A890857FD07AC6A60361E8C8173491686D461B2826190C2EDA5909054A9AB84D2AB9D99A90"


def show_point(label, curve, point):
    if point.is_infinity:
        print(f"{label}: O")
    else:
        print(f"{label}.x = {point.x:064x}")
        print(f"{label}.y = {point.y:064x}")


def main():
    curve = Curve(P, A, B, GENERATOR, Q)
    protocols = Protocols(curve)
    message = bytes.fromhex(MESSAGE_HEX)
    changed_message = bytes.fromhex(CHANGED_MESSAGE_HEX)

    print("=== Lab 4, variant 5: СТБ 34.101.45, affine coordinates, point blinding ===\n")

    block_ct = belt_block(BELT_SBOX[:16], BELT_SBOX[128:160]).hex()
    digest = belt_hash(message).hex()
    print("belt-block KAT:", block_ct,
          "->", "OK" if block_ct == "69cca1c93557c9e3d66bc3e0fa88fa6e" else "FAILED")
    print("belt-hash  KAT:", digest,
          "->", "OK" if digest == "abef9725d4c5a83597a367d14494cc2542f20f659ddfecc961a3ec550cba8c75" else "FAILED")
    assert block_ct == "69cca1c93557c9e3d66bc3e0fa88fa6e"
    assert digest == "abef9725d4c5a83597a367d14494cc2542f20f659ddfecc961a3ec550cba8c75"

    print("\nq*G == O:", curve.multiply_classic(Q, GENERATOR).is_infinity)
    assert curve.multiply_classic(Q, GENERATOR).is_infinity
    for scalar in (0, 1, 2, 15, 16, Q - 1):
        expected = curve.multiply_classic(scalar, GENERATOR)
        actual = FixedWindow(curve, GENERATOR).multiply(scalar)
        assert actual == expected, scalar
    print("Fixed-window == double-and-add for 0,1,2,15,16,q-1: OK")

    blinding = PointBlinding(curve)
    for scalar in (1, 2, 7, Q - 1):
        assert blinding.secure_multiply(scalar, GENERATOR) == curve.multiply_classic(scalar, GENERATOR)
    print("Point blinding d*(G+R)-d*R == d*G: OK")

    test_public = curve.multiply_classic(TEST_PRIVATE, GENERATOR)
    public_hex = curve.encode_point(test_public).hex().upper()
    print("Test public key:", public_hex)
    print("KAT public key matches:", public_hex == EXPECTED_PUBLIC_HEX)
    assert public_hex == EXPECTED_PUBLIC_HEX
    test_signature = protocols.sign(message, TEST_PRIVATE, TEST_NONCE)
    print("Test signature:", test_signature.hex().upper())
    print("KAT signature matches:", test_signature.hex().upper() == TEST_SIGNATURE_HEX)
    assert test_signature.hex().upper() == TEST_SIGNATURE_HEX
    assert protocols.verify(message, test_signature, test_public)
    print("KAT signature verified: True")

    print("\n--- ECDH ---")
    alice_private, alice_public = protocols.key_pair()
    bob_private, bob_public = protocols.key_pair()
    show_point("Q_A", curve, alice_public)
    show_point("Q_B", curve, bob_public)
    alice_secret = protocols.shared_secret(alice_private, bob_public)
    bob_secret = protocols.shared_secret(bob_private, alice_public)
    print("Alice shared secret:", alice_secret.hex())
    print("Bob   shared secret:", bob_secret.hex())
    print("Secrets equal:", alice_secret == bob_secret)
    assert alice_secret == bob_secret

    print("\n--- Signature ---")
    print("Message (hex):", MESSAGE_HEX)
    signature = protocols.sign(message, alice_private)
    print("S0 =", signature[:16].hex())
    print("S1 =", signature[16:].hex())
    valid = protocols.verify(message, signature, alice_public)
    damaged_signature = signature[:16] + bytes([signature[16] ^ 1]) + signature[17:]
    damaged_valid = protocols.verify(message, damaged_signature, alice_public)
    changed_message_valid = protocols.verify(changed_message, signature, alice_public)
    print("Verify valid signature:", valid)
    print("Verify after flipping one byte of s:", damaged_valid)
    print("Verify after changing the message:", changed_message_valid)
    assert valid and not damaged_valid and not changed_message_valid
    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    main()
