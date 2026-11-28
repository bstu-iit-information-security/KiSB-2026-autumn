import secrets

from belthash import belt_hash
from curve import Curve, Point
from protection import PointBlinding

OID_BELT_HASH = bytes.fromhex("06092A7000020022651F51")


class Protocols:
    def __init__(self, curve: Curve):
        self.curve = curve
        self.protection = PointBlinding(curve)

    def key_pair(self):
        private = secrets.randbelow(self.curve.order - 1) + 1
        public = self.protection.secure_multiply(private, self.curve.generator)
        return private, public

    def shared_secret(self, private, peer_public: Point):
        if not 1 <= private < self.curve.order:
            raise ValueError("Некорректный закрытый ключ")
        if not self.curve.valid_public_key(peer_public):
            raise ValueError("Некорректный открытый ключ")
        shared = self.protection.secure_multiply(private, peer_public)
        if shared.is_infinity:
            raise ValueError("Общий секрет равен точке O")
        return shared.x.to_bytes(self.curve.coordinate_size, "little")

    def message_hash(self, message):
        return belt_hash(message)

    def sign(self, message, private, nonce=None):
        if not 1 <= private < self.curve.order:
            raise ValueError("Некорректный закрытый ключ")
        if nonce is None:
            nonce = secrets.randbelow(self.curve.order - 1) + 1
        if not 1 <= nonce < self.curve.order:
            raise ValueError("Некорректный эфемерный ключ")

        digest = self.message_hash(message)
        point = self.protection.secure_multiply(nonce, self.curve.generator)
        if point.is_infinity:
            raise ValueError("kG = O")
        x = point.x.to_bytes(self.curve.coordinate_size, "little")
        s0 = belt_hash(OID_BELT_HASH + x + digest)[:16]
        s0_value = int.from_bytes(s0, "little")
        digest_value = int.from_bytes(digest, "little")
        s1_value = (nonce - digest_value -
                    (s0_value + (1 << 128)) * private) % self.curve.order
        return s0 + s1_value.to_bytes(32, "little")

    def verify(self, message, signature, public: Point):
        if len(signature) != 48:
            return False
        if not self.curve.valid_public_key(public):
            return False
        s0 = signature[:16]
        s1 = int.from_bytes(signature[16:], "little")
        if s1 >= self.curve.order:
            return False

        digest = self.message_hash(message)
        digest_value = int.from_bytes(digest, "little")
        factor = int.from_bytes(s0, "little") + (1 << 128)
        first = self.curve.multiply_classic((s1 + digest_value) % self.curve.order,
                                            self.curve.generator)
        second = self.curve.multiply_classic(factor, public)
        point = self.curve.add(first, second)
        if point.is_infinity:
            return False
        x = point.x.to_bytes(self.curve.coordinate_size, "little")
        expected_s0 = belt_hash(OID_BELT_HASH + x + digest)[:16]
        return secrets.compare_digest(s0, expected_s0)
