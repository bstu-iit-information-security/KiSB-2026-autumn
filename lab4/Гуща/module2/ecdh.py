
import secrets


class ECDH:
    def __init__(self, curve):
        self.curve = curve

    def generate_private_key(self):
        """Генерация случайного секретного ключа."""
        return secrets.randbelow(self.curve.q - 1) + 1

    def generate_public_key(self, private_key):
        """Вычисление открытого ключа Q = d * G."""

        if not 1 <= private_key < self.curve.q:
            raise ValueError("Некорректный секретный ключ")

        return self.curve.multiply(
            private_key,
            self.curve.G
        )

    def compute_shared_secret(self, private_key, public_key):
        """
        Вычисление общего секрета:
        K = d * Q
        """

        if not 1 <= private_key < self.curve.q:
            raise ValueError("Некорректный секретный ключ")

        if public_key.is_infinity:
            raise ValueError("Открытый ключ не может быть точкой O")

        if not self.curve.is_on_curve(public_key):
            raise ValueError("Открытый ключ не принадлежит кривой")

        shared_point = self.curve.multiply(
            private_key,
            public_key
        )

        if shared_point.is_infinity:
            raise ValueError("Получен недопустимый общий секрет")

        return shared_point.x
