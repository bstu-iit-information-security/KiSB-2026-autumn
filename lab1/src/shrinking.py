class ShrinkingGenerator:
    """SG-генератор (псевдослучайное прореживание).
    G1 — источник данных, G2 — селектор.
    """
    def __init__(self, g1, g2):
        self.g1 = g1
        self.g2 = g2
        self.total_consumed = 0  # счётчик "потраченных" бит G1 (для статистики)

    def next_bit(self):
        while True:
            a = self.g1.next_bit()
            s = self.g2.next_bit()
            self.total_consumed += 1
            if s == 1:
                return a

    def generate(self, n_bits):
        """Генерирует последовательность из n_bits бит."""
        return [self.next_bit() for _ in range(n_bits)]