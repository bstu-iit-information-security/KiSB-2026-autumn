import secrets
from dataclasses import dataclass


P = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF43", 16)
A = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF40", 16)
B = int("77CE6C1515F3A8EDD2C13AABE4D8FBBE4CF55069978B9253B22E7D6BD69C03F1", 16)
Q = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFD95C8ED60DFB4DFC7E5ABF99263D6607", 16)
GX = int("00", 16)
GY = int("6BF7FC3CFB16D69F5CE4C9A351D6835D78913966C408F6521E29CF1804516A93", 16)
OID_BELT_HASH = bytes.fromhex("06092A7000020022651F51")
MESSAGE_HEX = "B194BAC80A08F53B366D008E58"
CHANGED_MESSAGE_HEX = "B094BAC80A08F53B366D008E58"
TEST_PRIVATE = int.from_bytes(bytes.fromhex("1F66B5B84B7339674533F0329C74F21834281FED0732429E0C79235FC273E269"), "little")
TEST_NONCE = int.from_bytes(bytes.fromhex("4C0E74B2CD5811AD21F23DE7E0FA742C3ED6EC483C461CE15C33A77AA308B7D2"), "little")
TEST_SIGNATURE_HEX = "E36B7F0377AE4C524027C387FADF1B20CE72F1530B71F2B5FD3A8C584FE2E1AED20082E30C8AF65011F4FB54649DFD3D"

BELT_SBOX = bytes.fromhex(
    "B194BAC80A08F53B366D008E584A5DE4"
    "8504FA9D1BB6C7AC252E72C202FDCE0D"
    "5BE3D61217B96181FE6786AD716B890B"
    "5CB0C0FF33C356B835C405AED8E07F99"
    "E12BDC1AE28257EC703FCCF095EE8DF1"
    "C1AB76389FE678CAF7C6F860D5BB9C4F"
    "F33C657B637C306ADD4EA7799EB23D31"
    "3E98B56E27D3BCCF591E181F4C5AB793"
    "E9DEE72C8F0C0FA62DDB49F46F739647"
    "06075316ED247A3739CBA38303A98BF6"
    "92BD9B1CE5D141015445FBC95E4D0EF2"
    "682080AA227D642F2687F93490405511"
    "BE32971343FC9A48A02A885F194B09A1"
    "7ECDA4D01544AF8CA58450BF66D2E88A"
    "A2D7465242A8DFB36974C551EB232921"
    "D4EFD9B43A622875911410EA776CDA1D"
)


def belt_g(value, shift):
    encoded = value.to_bytes(4, "little")
    substituted = int.from_bytes(bytes(BELT_SBOX[byte] for byte in encoded), "little")
    return ((substituted << shift) | (substituted >> (32 - shift))) & 0xFFFFFFFF


def belt_block(block, key):
    words = [int.from_bytes(block[index:index + 4], "little") for index in range(0, 16, 4)]
    a, b, c, d = words
    key_words = [int.from_bytes(key[index:index + 4], "little") for index in range(0, 32, 4)]
    for round_number in range(1, 9):
        offset = 7 * (round_number - 1)
        b ^= belt_g((a + key_words[offset % 8]) & 0xFFFFFFFF, 5)
        c ^= belt_g((d + key_words[(offset + 1) % 8]) & 0xFFFFFFFF, 21)
        a = (a - belt_g((b + key_words[(offset + 2) % 8]) & 0xFFFFFFFF, 13)) & 0xFFFFFFFF
        e = belt_g((b + c + key_words[(offset + 3) % 8]) & 0xFFFFFFFF, 21) ^ round_number
        b = (b + e) & 0xFFFFFFFF
        c = (c - e) & 0xFFFFFFFF
        d = (d + belt_g((c + key_words[(offset + 4) % 8]) & 0xFFFFFFFF, 13)) & 0xFFFFFFFF
        b ^= belt_g((a + key_words[(offset + 5) % 8]) & 0xFFFFFFFF, 21)
        c ^= belt_g((d + key_words[(offset + 6) % 8]) & 0xFFFFFFFF, 5)
        a, b = b, a
        c, d = d, c
        b, c = c, b
    return b.to_bytes(4, "little") + d.to_bytes(4, "little") + a.to_bytes(4, "little") + c.to_bytes(4, "little")


def xor_bytes(first, second):
    return bytes(left ^ right for left, right in zip(first, second))


def belt_compress(data):
    x1, x2, x3, x4 = (data[index:index + 16] for index in range(0, 64, 16))
    x34 = xor_bytes(x3, x4)
    state = xor_bytes(belt_block(x34, x1 + x2), x34)
    y1 = xor_bytes(belt_block(x1, state + x4), x1)
    y2 = xor_bytes(belt_block(x2, xor_bytes(state, bytes([255] * 16)) + x3), x2)
    return state, y1 + y2


def belt_hash(data):
    length = (8 * len(data)).to_bytes(16, "little")
    state = bytes(16)
    digest = BELT_SBOX[:32]
    for offset in range(0, len(data), 32):
        block = data[offset:offset + 32].ljust(32, b"\x00")
        contribution, digest = belt_compress(block + digest)
        state = xor_bytes(state, contribution)
    return belt_compress(length + state + digest)[1]


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int
    z: int = 1


INFINITY = Point(1, 1, 0)
GENERATOR = Point(GX, GY)


class Curve:
    def __init__(self, p, a, b, generator, order):
        self.p = p
        self.a = a
        self.b = b
        self.generator = generator
        self.order = order
        if (4 * a**3 + 27 * b**2) % p == 0:
            raise ValueError("Особая кривая")
        if not self.on_curve(generator):
            raise ValueError("Базовая точка не принадлежит кривой")

    def inverse(self, value):
        return pow(value, -1, self.p)

    def to_affine(self, point):
        if point.z == 0:
            return None
        inverse_z = self.inverse(point.z)
        inverse_z2 = inverse_z * inverse_z % self.p
        return point.x * inverse_z2 % self.p, point.y * inverse_z2 * inverse_z % self.p

    def on_curve(self, point):
        coordinates = self.to_affine(point)
        if coordinates is None:
            return True
        x, y = coordinates
        return (y * y - x * x * x - self.a * x - self.b) % self.p == 0

    def double(self, point):
        if point.z == 0 or point.y == 0:
            return INFINITY
        x, y, z = point.x, point.y, point.z
        y2 = y * y % self.p
        s = 4 * x * y2 % self.p
        m = (3 * x * x + self.a * pow(z, 4, self.p)) % self.p
        x3 = (m * m - 2 * s) % self.p
        y3 = (m * (s - x3) - 8 * y2 * y2) % self.p
        z3 = 2 * y * z % self.p
        return Point(x3, y3, z3)

    def add(self, first, second):
        if first.z == 0:
            return second
        if second.z == 0:
            return first
        z1_squared = first.z * first.z % self.p
        z2_squared = second.z * second.z % self.p
        u1 = first.x * z2_squared % self.p
        u2 = second.x * z1_squared % self.p
        s1 = first.y * z2_squared * second.z % self.p
        s2 = second.y * z1_squared * first.z % self.p
        h = (u2 - u1) % self.p
        r = (s2 - s1) % self.p
        if h == 0:
            return self.double(first) if r == 0 else INFINITY
        h2 = h * h % self.p
        h3 = h2 * h % self.p
        x3 = (r * r - h3 - 2 * u1 * h2) % self.p
        y3 = (r * (u1 * h2 - x3) - s1 * h3) % self.p
        z3 = h * first.z * second.z % self.p
        return Point(x3, y3, z3)

    def multiply_classic(self, scalar, point):
        if scalar < 0:
            raise ValueError("Отрицательный скаляр")
        result = INFINITY
        current = point
        while scalar:
            if scalar & 1:
                result = self.add(result, current)
            current = self.double(current)
            scalar >>= 1
        return result

    def valid_public_key(self, point):
        return point.z != 0 and self.on_curve(point) and self.multiply_classic(self.order, point).z == 0


class FixedWindow:
    def __init__(self, curve, point, width=4):
        if width != 4:
            raise ValueError("В этой реализации окно равно четырем битам")
        self.curve = curve
        self.width = width
        self.coordinate_size = (curve.p.bit_length() + 7) // 8
        self.point_size = 3 * self.coordinate_size
        self.table = bytearray(16 * self.point_size)
        current = INFINITY
        for index in range(16):
            self._store(index, current)
            current = curve.add(current, point)

    def _store(self, index, point):
        offset = index * self.point_size
        for coordinate in (point.x, point.y, point.z):
            encoded = coordinate.to_bytes(self.coordinate_size, "big")
            self.table[offset:offset + self.coordinate_size] = encoded
            offset += self.coordinate_size

    def select(self, digit):
        selected = bytearray(self.point_size)
        for index in range(16):
            mask = -int(index == digit) & 255
            offset = index * self.point_size
            for position in range(self.point_size):
                selected[position] |= self.table[offset + position] & mask
        size = self.coordinate_size
        return Point(
            int.from_bytes(selected[:size], "big"),
            int.from_bytes(selected[size:2 * size], "big"),
            int.from_bytes(selected[2 * size:], "big"),
        )

    def multiply(self, scalar):
        if not 0 <= scalar < self.curve.order:
            raise ValueError("Скаляр вне диапазона")
        result = INFINITY
        windows = (self.curve.order.bit_length() + self.width - 1) // self.width
        for window in range(windows - 1, -1, -1):
            for _ in range(self.width):
                result = self.curve.double(result)
            digit = (scalar >> (window * self.width)) & 15
            result = self.curve.add(result, self.select(digit))
        return result


class Protocols:
    def __init__(self, curve):
        self.curve = curve
        self.base_window = FixedWindow(curve, curve.generator)

    def key_pair(self):
        private = secrets.randbelow(self.curve.order - 1) + 1
        return private, self.base_window.multiply(private)

    def shared_secret(self, private, peer_public):
        if not 1 <= private < self.curve.order or not self.curve.valid_public_key(peer_public):
            raise ValueError("Некорректный ключ ECDH")
        shared = FixedWindow(self.curve, peer_public).multiply(private)
        if shared.z == 0:
            raise ValueError("Общий секрет равен бесконечности")
        return self.curve.to_affine(shared)[0].to_bytes(32, "little")

    def message_hash(self, message):
        return belt_hash(message)

    def sign(self, message, private, nonce=None):
        if not 1 <= private < self.curve.order:
            raise ValueError("Некорректный закрытый ключ")
        if nonce is None:
            nonce = secrets.randbelow(self.curve.order - 1) + 1
        if not 1 <= nonce < self.curve.order:
            raise ValueError("Некорректный одноразовый ключ")
        message_digest = self.message_hash(message)
        point = self.base_window.multiply(nonce)
        x = self.curve.to_affine(point)[0].to_bytes(32, "little")
        s0 = belt_hash(OID_BELT_HASH + x + message_digest)[:16]
        s0_value = int.from_bytes(s0, "little")
        digest_value = int.from_bytes(message_digest, "little")
        s1_value = (nonce - digest_value - (s0_value + (1 << 128)) * private) % self.curve.order
        return s0 + s1_value.to_bytes(32, "little")

    def verify(self, message, signature, public):
        if len(signature) != 48:
            return False
        if not self.curve.valid_public_key(public):
            return False
        s0 = signature[:16]
        s1 = int.from_bytes(signature[16:], "little")
        if s1 >= self.curve.order:
            return False
        message_digest = self.message_hash(message)
        digest_value = int.from_bytes(message_digest, "little")
        factor = int.from_bytes(s0, "little") + (1 << 128)
        first = self.curve.multiply_classic((s1 + digest_value) % self.curve.order, self.curve.generator)
        second = self.curve.multiply_classic(factor, public)
        point = self.curve.add(first, second)
        if point.z == 0:
            return False
        x = self.curve.to_affine(point)[0].to_bytes(32, "little")
        expected_s0 = belt_hash(OID_BELT_HASH + x + message_digest)[:16]
        return secrets.compare_digest(s0, expected_s0)


def show_point(label, curve, point):
    coordinates = curve.to_affine(point)
    if coordinates is None:
        print(f"{label}: O")
    else:
        print(f"{label}.x = {coordinates[0]:064x}")
        print(f"{label}.y = {coordinates[1]:064x}")


def main():
    curve = Curve(P, A, B, GENERATOR, Q)
    protocols = Protocols(curve)
    message = bytes.fromhex(MESSAGE_HEX)
    changed_message = bytes.fromhex(CHANGED_MESSAGE_HEX)

    assert belt_block(BELT_SBOX[:16], BELT_SBOX[128:160]).hex() == "69cca1c93557c9e3d66bc3e0fa88fa6e"
    assert belt_hash(message).hex() == "abef9725d4c5a83597a367d14494cc2542f20f659ddfecc961a3ec550cba8c75"
    assert curve.multiply_classic(Q, GENERATOR).z == 0
    for scalar in (0, 1, 2, 15, 16, Q - 1):
        expected = curve.to_affine(curve.multiply_classic(scalar, GENERATOR))
        actual = curve.to_affine(protocols.base_window.multiply(scalar))
        assert actual == expected

    test_public = protocols.base_window.multiply(TEST_PRIVATE)
    test_x, test_y = curve.to_affine(test_public)
    expected_public_hex = "BD1A5650179D79E03FCEE49D4C2BD5DDF54CE46D0CF11E4FF87BF7A890857FD07AC6A60361E8C8173491686D461B2826190C2EDA5909054A9AB84D2AB9D99A90"
    assert (test_x.to_bytes(32, "little") + test_y.to_bytes(32, "little")).hex().upper() == expected_public_hex
    test_signature = protocols.sign(message, TEST_PRIVATE, TEST_NONCE)
    assert test_signature.hex().upper() == TEST_SIGNATURE_HEX
    assert protocols.verify(message, test_signature, test_public)

    alice_private, alice_public = protocols.key_pair()
    bob_private, bob_public = protocols.key_pair()
    alice_secret = protocols.shared_secret(alice_private, bob_public)
    bob_secret = protocols.shared_secret(bob_private, alice_public)
    assert alice_secret == bob_secret

    signature = protocols.sign(message, alice_private)
    valid = protocols.verify(message, signature, alice_public)
    damaged_signature = signature[:16] + bytes([signature[16] ^ 1]) + signature[17:]
    damaged_valid = protocols.verify(message, damaged_signature, alice_public)
    changed_message_valid = protocols.verify(changed_message, signature, alice_public)
    assert valid and not damaged_valid and not changed_message_valid

    print(f"Сообщение (hex): {MESSAGE_HEX}")
    show_point("Q_A", curve, alice_public)
    show_point("Q_B", curve, bob_public)
    print(f"Секрет Алисы: {alice_secret.hex()}")
    print(f"Секрет Боба:   {bob_secret.hex()}")
    print(f"Секреты совпали: {alice_secret == bob_secret}")
    print(f"Хэш belt-hash: {protocols.message_hash(message).hex()}")
    print(f"S0 = {signature[:16].hex()}")
    print(f"S1 = {signature[16:].hex()}")
    print(f"Проверка подписи: {valid}")
    print(f"Проверка после изменения байта s: {damaged_valid}")
    print(f"Проверка после изменения сообщения: {changed_message_valid}")
    

if __name__ == "__main__":
    main()
