class LFSR:
    """Линейный регистр сдвига с обратной связью над GF(2).

    Параметры:
      taps_mask — маска отводов (какие биты участвуют в XOR).
      n         — длина регистра (степень многочлена).
      seed      — начальное состояние (не может быть нулём!).
    """
    def __init__(self, taps_mask, n, seed=1):
        self.n = n
        self.taps = taps_mask
        self.state = seed & ((1 << n) - 1)
        if self.state == 0:
            raise ValueError("seed не может быть нулём (регистр зациклится)")

    def next_bit(self):
        # Выходной бит — самый правый (младший)
        out = self.state & 1
        # Обратная связь: XOR тех битов, где в маске стоят 1
        fb = bin(self.state & self.taps).count('1') & 1
        # Сдвигаем вправо, а новый бит ставим в старший разряд
        self.state = (self.state >> 1) | (fb << (self.n - 1))
        return out

    def get_period(self):
        """Вычисляет длину периода (возвращает состояние в исходное)."""
        start_state = self.state
        period = 0
        while True:
            self.next_bit()
            period += 1
            if self.state == start_state:
                return period
            # Защита от бесконечного цикла (если регистр зациклился в 0)
            if period > 2 ** self.n:
                return -1
# Конец файла. Убедитесь, что эта строчка есть!