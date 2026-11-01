from .lfsr import LFSR, is_primitive

class SGGenerator:

    __slots__ = ("_g1", "_g2", "_n", "_m")

    def __init__(self, poly1: int, seed1: int, poly2: int, seed2: int):
        if not is_primitive(poly1):
            raise ValueError(f"G1: многочлен 0b{poly1:b} не примитивен")
        if not is_primitive(poly2):
            raise ValueError(f"G2: многочлен 0b{poly2:b} не примитивен")
        self._g1 = LFSR(poly1, seed1)
        self._g2 = LFSR(poly2, seed2)
        self._n = self._g1.period   # 2^n − 1
        self._m = self._g2.period   # 2^m − 1

    def next_bit(self) -> int:
        while True:
            a = self._g1.next_bit()
            s = self._g2.next_bit()
            mask = -s
            if mask & 1:
                return a

    def next_bits(self, count: int) -> list[int]:
        out = []
        append = out.append
        g1_next = self._g1.next_bit
        g2_next = self._g2.next_bit
        while len(out) < count:
            a = g1_next()
            s = g2_next()
            if s:
                append(a)
        return out

    @property
    def theoretical_period(self) -> int:
        from math import gcd
        if gcd(self._n, self._m) != 1:
            raise ValueError(
                f"Периоды {self._n} и {self._m} не взаимно просты — "
                f"теорема о периоде SG не применима"
            )
        return self._n * (1 << (self._m.bit_length() - 1))