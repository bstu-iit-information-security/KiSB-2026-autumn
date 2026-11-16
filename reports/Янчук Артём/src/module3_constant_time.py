from __future__ import annotations
import ctypes
import secrets


class StaticPointArena:
    """
    МОДУЛЬ 3: Непрерывный статический пул памяти (Heap-Free Arena) для хранения точек
    эллиптической кривой в проективных координатах Якоби (X, Y, Z).

    Каждая координата (256 бит) занимает 4 x uint64 (32 байта).
    Каждая точка (X, Y, Z) занимает 12 x uint64 (96 байт) непрерывно.
    Никаких вложенных списков или аллокаций объектов в куче во время работы.
    """
    LIMBS_PER_COORD = 4
    LIMBS_PER_POINT = 12  # X (0..3), Y (4..7), Z (8..11)
    MASK64 = 0xFFFFFFFFFFFFFFFF
    MASK256 = (1 << 256) - 1

    # Именованные регистры (слоты) в статическом буфере
    SLOT_R0     = 0  # Рабочий регистр R0 лестницы Монтгомери
    SLOT_R1     = 1  # Рабочий регистр R1 лестницы Монтгомери
    SLOT_T_ADD  = 2  # Буфер результата сложения
    SLOT_T_DBL  = 3  # Буфер результата удвоения
    SLOT_BASE   = 4  # Входная точка P
    SLOT_OUT    = 5  # Выходная точка Q = k * P
    SLOT_INF    = 6  # Каноническая точка на бесконечности O = (1, 1, 0)
    SLOT_AUX1   = 7  # Вспомогательный регистр для верификации (z1 * G)
    SLOT_AUX2   = 8  # Вспомогательный регистр для верификации (z2 * Q)
    TOTAL_SLOTS = 9

    def __init__(self):
        # Единоразовая статическая аллокация плоского массива C uint64 (108 слов = 864 байта)
        BufferType = ctypes.c_uint64 * (self.TOTAL_SLOTS * self.LIMBS_PER_POINT)
        self._buf = BufferType()
        # Инициализируем слот точки на бесконечности O = (1, 1, 0)
        self.write_point(self.SLOT_INF, 1, 1, 0)

    def write_point(self, slot: int, x: int, y: int, z: int) -> None:
        """Запись 256-битных координат (X, Y, Z) в фиксированный слот арены."""
        base = slot * self.LIMBS_PER_POINT
        for i in range(4):
            self._buf[base + i]     = (x >> (64 * i)) & self.MASK64
            self._buf[base + 4 + i] = (y >> (64 * i)) & self.MASK64
            self._buf[base + 8 + i] = (z >> (64 * i)) & self.MASK64

    def read_point(self, slot: int) -> tuple[int, int, int]:
        """Чтение координат (X, Y, Z) из фиксированного слота арены."""
        base = slot * self.LIMBS_PER_POINT
        x = (self._buf[base] |
             (self._buf[base + 1] << 64) |
             (self._buf[base + 2] << 128) |
             (self._buf[base + 3] << 192))
        y = (self._buf[base + 4] |
             (self._buf[base + 5] << 64) |
             (self._buf[base + 6] << 128) |
             (self._buf[base + 7] << 192))
        z = (self._buf[base + 8] |
             (self._buf[base + 9] << 64) |
             (self._buf[base + 10] << 128) |
             (self._buf[base + 11] << 192))
        return x, y, z

    def copy_slot(self, dst_slot: int, src_slot: int) -> None:
        """Безусловное копирование слота внутри непрерывного буфера."""
        dst_base = dst_slot * self.LIMBS_PER_POINT
        src_base = src_slot * self.LIMBS_PER_POINT
        for i in range(self.LIMBS_PER_POINT):
            self._buf[dst_base + i] = self._buf[src_base + i]

    def cswap_slots(self, slot_a: int, slot_b: int, bit: int) -> None:
        """
        Constant-time условный обмен двух точек в статической памяти (CSWAP).
        Не содержит ветвлений if: mask = 0x00..00 при bit=0, 0xFF..FF при bit=1.
        """
        mask = (0 - (bit & 1)) & self.MASK64
        base_a = slot_a * self.LIMBS_PER_POINT
        base_b = slot_b * self.LIMBS_PER_POINT
        for i in range(self.LIMBS_PER_POINT):
            va = self._buf[base_a + i]
            vb = self._buf[base_b + i]
            dummy = mask & (va ^ vb)
            self._buf[base_a + i] = va ^ dummy
            self._buf[base_b + i] = vb ^ dummy

    def cmov_slots(self, dst_slot: int, src_slot: int, cond_bit: int) -> None:
        """
        Constant-time условное перемещение точки (CMOV) без оператора if.
        Если cond_bit == 1, содержимое src_slot копируется в dst_slot.
        """
        mask = (0 - (cond_bit & 1)) & self.MASK64
        dst_base = dst_slot * self.LIMBS_PER_POINT
        src_base = src_slot * self.LIMBS_PER_POINT
        for i in range(self.LIMBS_PER_POINT):
            vd = self._buf[dst_base + i]
            vs = self._buf[src_base + i]
            self._buf[dst_base + i] = vd ^ (mask & (vd ^ vs))

    @staticmethod
    def ct_is_zero(val: int) -> int:
        """
        Branchless проверка 256-битного числа на равенство нулю.
        Возвращает 1, если val == 0, иначе 0.
        """
        v = val & StaticPointArena.MASK256
        non_zero = ((v | ((~v + 1) & StaticPointArena.MASK256)) >> 255) & 1
        return 1 ^ non_zero

    @staticmethod
    def ct_eq(a: int, b: int) -> int:
        """Constant-time сравнение двух 256-битных чисел (XOR-аккумулятор без early exit)."""
        return StaticPointArena.ct_is_zero(a ^ b)

    @staticmethod
    def ct_select(a: int, b: int, bit: int) -> int:
        """Возвращает b при bit == 1, иначе a (без ветвлений)."""
        mask = (0 - (bit & 1)) & StaticPointArena.MASK256
        return a ^ (mask & (a ^ b))

    @staticmethod
    def ct_generate_scalar(q: int, iterations: int = 64) -> int:
        """
        Constant-time генерация эфемерного ключа k в интервале (0, q)
        методом Rejection Sampling фиксированной длины с защитой через CMOV.
        """
        result = 1
        found = 0
        for _ in range(iterations):
            candidate = secrets.randbits(256)
            is_pos = 1 ^ StaticPointArena.ct_is_zero(candidate)
            is_lt_q = ((candidate - q) >> 256) & 1
            valid = is_pos & is_lt_q
            take = valid & (1 ^ found)
            result = StaticPointArena.ct_select(result, candidate, take)
            found = found | take
        return result