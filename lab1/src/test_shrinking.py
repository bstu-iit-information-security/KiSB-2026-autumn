from lfsr import LFSR
from shrinking import ShrinkingGenerator

# Создаем два LFSR
g1 = LFSR(taps_mask=0b00101, n=5, seed=0b10101) # f1
g2 = LFSR(taps_mask=0b11101, n=5, seed=0b11011) # f2

# Создаем SG-генератор
sg = ShrinkingGenerator(g1, g2)

# Генерируем 50 бит
seq = sg.generate(50)

print("Первые 50 бит SG-последовательности:")
print(''.join(map(str, seq)))
print(f"\nПотрачено тактов (бит из G1): {sg.total_consumed}")