"""Комбинирование двух LFSR методом псевдослучайного прореживания (SG-генератор).

G1 (LFSR-A) порождает элементарную последовательность {a_t},
G2 (LFSR-S) - селектирующую {s_t}. В выход попадает a_t только если s_t = 1.
Теоретический период при взаимно простых периодах (примитивные многочлены
степеней n и m, НОД(2^n-1, 2^m-1) = 1):  T = (2^n - 1) * 2^(m-1).
"""
from lfsr import LFSR


class ShrinkingGenerator:
    def __init__(self, poly_a, seed_a, poly_s, seed_s):
        self.a = LFSR(poly_a, seed_a)
        self.s = LFSR(poly_s, seed_s)

    def next_bit(self):
        for _ in range(1 << 22):  # защита от вырожденного селектора из одних нулей
            a = self.a.step()
            if self.s.step():
                return a
        raise RuntimeError("селектор не выдаёт единиц - вырожденный многочлен/состояние")

    def bits(self, count):
        return [self.next_bit() for _ in range(count)]

    def symbols(self, count, alphabet):
        """Равномерная последовательность из `count` символов алфавита {0..N-1}.

        Берём k = ceil(log2 N) бит; если получилось число >= N, оно отбрасывается
        (метод исключения - иначе равномерность нарушилась бы при N != 2^k).
        """
        k = (alphabet - 1).bit_length()
        out = []
        while len(out) < count:
            v = 0
            for _ in range(k):
                v = (v << 1) | self.next_bit()
            if v < alphabet:
                out.append(v)
        return out

    # интерфейс для генератора простых чисел (этап 2)
    def getrandbits(self, k):
        v = 0
        for _ in range(k):
            v = (v << 1) | self.next_bit()
        return v

    def randbelow(self, n):
        """Равномерное целое из [0, n)."""
        if n <= 1:
            return 0
        k = (n - 1).bit_length()
        while True:
            v = self.getrandbits(k)
            if v < n:
                return v


def theoretical_period(deg_a, deg_s):
    return ((1 << deg_a) - 1) * (1 << (deg_s - 1))
