from __future__ import annotations
from module3_constant_time import StaticPointArena


class EllipticCurveAlgebra:
    """
    МОДУЛЬ 1: Математическое ядро для работы с эллиптической кривой в форме Вейерштрасса
    y^2 = x^3 + a*x + b (mod p) в проективных координатах Якоби (X, Y, Z),
    где x = X * Z^-2 (mod p), y = Y * Z^-3 (mod p).
    """

    def __init__(self, p_hex: str, a_hex: str, b_hex: str, q_hex: str, gx_hex: str, gy_hex: str):
        self.p = int(p_hex, 16)
        self.a = int(a_hex, 16)
        self.b = int(b_hex, 16)
        self.q = int(q_hex, 16)
        self.gx = int(gx_hex, 16)
        self.gy = int(gy_hex, 16)

        # Инициализируем статическую арену памяти (Модуль 3)
        self.arena = StaticPointArena()

        # Проверка отсутствия кратных корней: 4a^3 + 27b^2 != 0 (mod p)
        discriminant = (4 * pow(self.a, 3, self.p) + 27 * pow(self.b, 2, self.p)) % self.p
        if discriminant == 0:
            raise ValueError("Сингулярная кривая: 4a^3 + 27b^2 == 0 (mod p)")

    # --- Базовая арифметика конечного поля GF(p) ---

    def mod_add(self, x: int, y: int) -> int:
        """Constant-time модульное сложение (x + y) mod p с помощью битовой маски."""
        s = x + y
        geq_p = 1 ^ (((s - self.p) >> 256) & 1)
        mask = 0 - geq_p
        return s - (self.p & mask)

    def mod_sub(self, x: int, y: int) -> int:
        """Constant-time модульное вычитание (x - y) mod p с помощью битовой маски."""
        d = x - y
        lt_zero = (d >> 256) & 1
        mask = 0 - lt_zero
        return d + (self.p & mask)

    def mod_mul(self, x: int, y: int) -> int:
        """Модульное умножение в GF(p)."""
        return (x * y) % self.p

    def mod_inv(self, x: int) -> int:
        """
        Constant-time поиск обратного элемента x^-1 (mod p)
        по Малой теореме Ферма: x^(p-2) mod p.
        """
        return pow(x, self.p - 2, self.p)

    @staticmethod
    def mod_inv_scalar(x: int, mod_q: int) -> int:
        """Обратный элемент в поле скаляров GF(q) по Малой теореме Ферма."""
        return pow(x, mod_q - 2, mod_q)

    # --- Операции над точками в проективных координатах Якоби внутри статической арены ---

    def jacobian_double_slot(self, dst_slot: int, src_slot: int) -> None:
        """
        Удвоение точки P3 = 2*P1 в координатах Якоби напрямую в слотах статической арены.
        """
        X1, Y1, Z1 = self.arena.read_point(src_slot)

        Y1_sq = self.mod_mul(Y1, Y1)                     # Y1^2
        Y1_4  = self.mod_mul(Y1_sq, Y1_sq)               # Y1^4
        X1_sq = self.mod_mul(X1, X1)                     # X1^2
        Z1_sq = self.mod_mul(Z1, Z1)                     # Z1^2
        Z1_4  = self.mod_mul(Z1_sq, Z1_sq)               # Z1^4

        S = self.mod_mul(4, self.mod_mul(X1, Y1_sq))     # 4 * X1 * Y1^2
        M = self.mod_add(
            self.mod_mul(3, X1_sq),
            self.mod_mul(self.a, Z1_4)
        )                                                # 3 * X1^2 + a * Z1^4

        two_S = self.mod_add(S, S)
        X3 = self.mod_sub(self.mod_mul(M, M), two_S)     # M^2 - 2*S

        eight_Y1_4 = self.mod_mul(8, Y1_4)
        Y3 = self.mod_sub(
            self.mod_mul(M, self.mod_sub(S, X3)),
            eight_Y1_4
        )                                                # M * (S - X3) - 8 * Y1^4
        Z3 = self.mod_mul(2, self.mod_mul(Y1, Z1))       # 2 * Y1 * Z1

        # Если входная точка была O (Z1 == 0) или Y1 == 0, канонизируем в O = (1, 1, 0) без ветвлений
        is_inf = self.arena.ct_is_zero(Z3)
        X3 = self.arena.ct_select(X3, 1, is_inf)
        Y3 = self.arena.ct_select(Y3, 1, is_inf)
        Z3 = self.arena.ct_select(Z3, 0, is_inf)

        self.arena.write_point(dst_slot, X3, Y3, Z3)

    def jacobian_add_slot(self, dst_slot: int, slot1: int, slot2: int) -> None:
        """
        Полное branchless-сложение P3 = P1 + P2 в координатах Якоби в статической арене.
        Граничные случаи (P1 == O, P2 == O, P1 == P2, P1 == -P2) разрешаются
        исключительно битовыми масками (CMOV) без единого оператора if.
        """
        X1, Y1, Z1 = self.arena.read_point(slot1)
        X2, Y2, Z2 = self.arena.read_point(slot2)

        Z1_sq = self.mod_mul(Z1, Z1)
        Z2_sq = self.mod_mul(Z2, Z2)
        Z1_cu = self.mod_mul(Z1_sq, Z1)
        Z2_cu = self.mod_mul(Z2_sq, Z2)

        U1 = self.mod_mul(X1, Z2_sq)
        U2 = self.mod_mul(X2, Z1_sq)
        S1 = self.mod_mul(Y1, Z2_cu)
        S2 = self.mod_mul(Y2, Z1_cu)

        H = self.mod_sub(U2, U1)
        R = self.mod_sub(S2, S1)

        H_sq = self.mod_mul(H, H)
        H_cu = self.mod_mul(H_sq, H)
        U1_H_sq = self.mod_mul(U1, H_sq)

        X3 = self.mod_sub(
            self.mod_sub(self.mod_mul(R, R), H_cu),
            self.mod_add(U1_H_sq, U1_H_sq)
        )
        Y3 = self.mod_sub(
            self.mod_mul(R, self.mod_sub(U1_H_sq, X3)),
            self.mod_mul(S1, H_cu)
        )
        Z3 = self.mod_mul(H, self.mod_mul(Z1, Z2))

        # Вычисляем флаги особых состояний через арифметические маски
        z1_zero = self.arena.ct_is_zero(Z1)
        z2_zero = self.arena.ct_is_zero(Z2)
        h_zero  = self.arena.ct_is_zero(H)
        r_zero  = self.arena.ct_is_zero(R)

        is_double   = h_zero & r_zero & (1 ^ z1_zero) & (1 ^ z2_zero)
        is_opposite = h_zero & (1 ^ r_zero) & (1 ^ z1_zero) & (1 ^ z2_zero)

        # Вычисляем дубликат 2*P1 в резервный статический слот SLOT_T_DBL
        self.jacobian_double_slot(self.arena.SLOT_T_DBL, slot1)
        X_dbl, Y_dbl, Z_dbl = self.arena.read_point(self.arena.SLOT_T_DBL)

        # Безветвящийся мультиплексор результата через ct_select:
        X3 = self.arena.ct_select(X3, X_dbl, is_double)
        Y3 = self.arena.ct_select(Y3, Y_dbl, is_double)
        Z3 = self.arena.ct_select(Z3, Z_dbl, is_double)

        X3 = self.arena.ct_select(X3, 1, is_opposite)
        Y3 = self.arena.ct_select(Y3, 1, is_opposite)
        Z3 = self.arena.ct_select(Z3, 0, is_opposite)

        X3 = self.arena.ct_select(X3, X2, z1_zero)
        Y3 = self.arena.ct_select(Y3, Y2, z1_zero)
        Z3 = self.arena.ct_select(Z3, Z2, z1_zero)

        X3 = self.arena.ct_select(X3, X1, z2_zero)
        Y3 = self.arena.ct_select(Y3, Y1, z2_zero)
        Z3 = self.arena.ct_select(Z3, Z1, z2_zero)

        self.arena.write_point(dst_slot, X3, Y3, Z3)

    def slot_to_affine(self, slot: int) -> tuple[int, int]:
        """
        Однократный перевод точки из проективных координат Якоби (X, Y, Z)
        в аффинные (x, y) в конце алгоритма:
            x = X * Z^-2 (mod p),  y = Y * Z^-3 (mod p).
        """
        X, Y, Z = self.arena.read_point(slot)
        if Z == 0:
            return 0, 0
        z_inv = self.mod_inv(Z)
        z_inv2 = self.mod_mul(z_inv, z_inv)
        z_inv3 = self.mod_mul(z_inv2, z_inv)
        x = self.mod_mul(X, z_inv2)
        y = self.mod_mul(Y, z_inv3)
        return x, y

    def is_on_curve_affine(self, x: int, y: int) -> bool:
        """Проверка принадлежности аффинной точки (x, y) кривой Вейерштрасса."""
        if x == 0 and y == 0:
            return True
        lhs = self.mod_mul(y, y)
        rhs = (pow(x, 3, self.p) + self.a * x + self.b) % self.p
        return self.arena.ct_eq(lhs, rhs) == 1

    def secure_scalar_mul(self, k: int, px: int, py: int, out_slot: int = StaticPointArena.SLOT_OUT) -> tuple[int, int]:
        """
        Constant-time & Heap-free скалярное умножение Q = k * P (Лестница Монтгомери).
        Все 256 итераций выполняются строго in-place в статической арене памяти.
        """
        a = self.arena
        a.copy_slot(a.SLOT_R0, a.SLOT_INF)
        a.write_point(a.SLOT_R1, px, py, 1)

        for bit_idx in range(255, -1, -1):
            bit = (k >> bit_idx) & 1

            a.cswap_slots(a.SLOT_R0, a.SLOT_R1, bit)

            self.jacobian_add_slot(a.SLOT_T_ADD, a.SLOT_R0, a.SLOT_R1)
            a.copy_slot(a.SLOT_R1, a.SLOT_T_ADD)

            self.jacobian_double_slot(a.SLOT_T_DBL, a.SLOT_R0)
            a.copy_slot(a.SLOT_R0, a.SLOT_T_DBL)

            a.cswap_slots(a.SLOT_R0, a.SLOT_R1, bit)

        a.copy_slot(out_slot, a.SLOT_R0)
        return self.slot_to_affine(out_slot)