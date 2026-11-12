
import hashlib
import secrets


class ECDSA:
    def __init__(self, curve):
        self.curve = curve

    def hash_message(self, message: bytes) -> int:
        digest = hashlib.sha256(message).digest()

        return int.from_bytes(digest, "big") % self.curve.q

    def generate_private_key(self):
        """Генерация закрытого ключа."""

        return secrets.randbelow(self.curve.q - 1) + 1

    def generate_public_key(self, private_key):
        """Q = d * G."""

        if not 1 <= private_key < self.curve.q:
            raise ValueError("Некорректный закрытый ключ")

        return self.curve.multiply(
            private_key,
            self.curve.G
        )

    def sign(self, message: bytes, private_key: int):
        """
        Формирование ECDSA-подписи (r, s).
        """

        q = self.curve.q

        if not 1 <= private_key < q:
            raise ValueError("Некорректный закрытый ключ")

        e = self.hash_message(message)

        while True:

            # Эфемерный секретный параметр k.
            k = secrets.randbelow(q - 1) + 1

            # R = k * G
            R = self.curve.multiply(k, self.curve.G)

            r = R.x % q

            if r == 0:
                continue

            # s = k^(-1) * (e + r*d) mod q
            k_inv = pow(k, -1, q)

            s = (
                k_inv * (e + r * private_key)
            ) % q

            if s == 0:
                continue

            return r, s

    def verify(self, message: bytes, signature, public_key):
        """
        Проверка ECDSA-подписи.
        """

        r, s = signature
        q = self.curve.q

        # Проверка диапазона подписи.
        if not (1 <= r < q and 1 <= s < q):
            return False

        # Проверка открытого ключа.
        if public_key.is_infinity:
            return False

        if not self.curve.is_on_curve(public_key):
            return False

        e = self.hash_message(message)

        # w = s^(-1) mod q
        w = pow(s, -1, q)

        u1 = (e * w) % q
        u2 = (r * w) % q

        # C = u1*G + u2*Q
        P1 = self.curve.multiply(u1, self.curve.G)
        P2 = self.curve.multiply(u2, public_key)

        C = self.curve.add(P1, P2)

        if C.is_infinity:
            return False

        return C.x % q == r
