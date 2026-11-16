from __future__ import annotations
from module1_ec_algebra import EllipticCurveAlgebra
from module3_constant_time import StaticPointArena


class CryptoProtocols:
    """
    МОДУЛЬ 2: Реализация протокола согласования ключей ECDH и стандарта ЭЦП ГОСТ Р 34.10-2012
    на базе защищенного математического ядра Модуля 1 и статической арены Модуля 3.
    Все входные и выходные параметры передаются в виде сырых Hex-строк.
    """

    def __init__(self, curve: EllipticCurveAlgebra):
        self.curve = curve

    def generate_keypair(self, d_hex: str | None = None) -> tuple[str, str, str]:
        """
        Генерация ключевой пары (d, Qx, Qy).
        Если секретный ключ d_hex не передан, он генерируется в Constant-time режиме.
        """
        if d_hex is None:
            d = self.curve.arena.ct_generate_scalar(self.curve.q)
        else:
            d = int(d_hex, 16)

        qx, qy = self.curve.secure_scalar_mul(d, self.curve.gx, self.curve.gy)
        return f"{d:064X}", f"{qx:064X}", f"{qy:064X}"

    def ecdh_shared_secret(self, own_d_hex: str, peer_qx_hex: str, peer_qy_hex: str) -> tuple[str, str]:
        """
        Вычисление общего разделяемого секрета K = d * Q_peer по протоколу ECDH.
        Возвращает сырые Hex-координаты (Kx, Ky).
        """
        d = int(own_d_hex, 16)
        peer_qx = int(peer_qx_hex, 16)
        peer_qy = int(peer_qy_hex, 16)

        if not self.curve.is_on_curve_affine(peer_qx, peer_qy):
            raise ValueError("Открытый ключ партнера не принадлежит эллиптической кривой!")

        kx, ky = self.curve.secure_scalar_mul(d, peer_qx, peer_qy)
        return f"{kx:064X}", f"{ky:064X}"

    def sign_gost_2012(self, d_hex: str, msg_hash_hex: str, k_hex: str | None = None) -> tuple[str, str]:
        """
        Выработка электронной цифровой подписи по ГОСТ Р 34.10-2012:
            1. e = Hash(M) mod q (если e == 0, то e = 1)
            2. C = k * G
            3. r = x_C mod q
            4. s = (r * d + k * e) mod q
        Возвращает пару (r_hex, s_hex).
        """
        q = self.curve.q
        d = int(d_hex, 16)
        e = int(msg_hash_hex, 16) % q
        if e == 0:
            e = 1

        while True:
            if k_hex is not None:
                k = int(k_hex, 16)
            else:
                k = self.curve.arena.ct_generate_scalar(q)

            cx, _ = self.curve.secure_scalar_mul(k, self.curve.gx, self.curve.gy)
            r = cx % q
            s = (r * d + k * e) % q

            if r != 0 and s != 0:
                return f"{r:064X}", f"{s:064X}"

            if k_hex is not None:
                raise ValueError("Переданный фиксированный эфемерный ключ k дает r=0 или s=0")

    def verify_gost_2012(self, qx_hex: str, qy_hex: str, msg_hash_hex: str, r_hex: str, s_hex: str) -> tuple[bool, str]:
        """
        Проверка электронной цифровой подписи по ГОСТ Р 34.10-2012:
            1. Проверка 0 < r < q и 0 < s < q
            2. e = Hash(M) mod q (если e == 0, то e = 1)
            3. v = e^-1 mod q
            4. z1 = (s * v) mod q,  z2 = (-r * v) mod q
            5. C' = z1 * G + z2 * Q (в проективных координатах Якоби)
            6. R = x_C' mod q. Подпись верна, если R == r.
        Возвращает (is_valid, R_hex).
        """
        q = self.curve.q
        r = int(r_hex, 16)
        s = int(s_hex, 16)
        qx = int(qx_hex, 16)
        qy = int(qy_hex, 16)

        if not (0 < r < q and 0 < s < q):
            return False, f"{0:064X}"

        if not self.curve.is_on_curve_affine(qx, qy):
            return False, f"{0:064X}"

        e = int(msg_hash_hex, 16) % q
        if e == 0:
            e = 1

        v = self.curve.mod_inv_scalar(e, q)
        z1 = (s * v) % q
        z2 = ((q - r) * v) % q

        # Вычисляем P1 = z1 * G -> сохраняется в проективном слоте SLOT_AUX1
        self.curve.secure_scalar_mul(z1, self.curve.gx, self.curve.gy, out_slot=StaticPointArena.SLOT_AUX1)
        # Вычисляем P2 = z2 * Q -> сохраняется в проективном слоте SLOT_AUX2
        self.curve.secure_scalar_mul(z2, qx, qy, out_slot=StaticPointArena.SLOT_AUX2)

        # Складываем C' = P1 + P2 напрямую в проективных координатах Якоби в статической арене
        self.curve.jacobian_add_slot(
            StaticPointArena.SLOT_OUT,
            StaticPointArena.SLOT_AUX1,
            StaticPointArena.SLOT_AUX2
        )
        cx_prime, cy_prime = self.curve.slot_to_affine(StaticPointArena.SLOT_OUT)
        if cx_prime == 0 and cy_prime == 0:
            return False, f"{0:064X}"

        R = cx_prime % q
        is_valid = (self.curve.arena.ct_eq(R, r) == 1)
        return is_valid, f"{R:064X}"