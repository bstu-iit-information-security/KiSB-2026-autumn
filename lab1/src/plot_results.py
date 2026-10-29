import os
import matplotlib.pyplot as plt
from lfsr import LFSR
from shrinking import ShrinkingGenerator

# Автоматически создаем папку для графиков, если её нет
os.makedirs('../report/plots', exist_ok=True)

def generate_sg_seq(n_bits, seed1=0b00001, seed2=0b0000001):
    g1 = LFSR(taps_mask=0b00101, n=5, seed=seed1)
    g2 = LFSR(taps_mask=0b0000011, n=7, seed=seed2)
    sg = ShrinkingGenerator(g1, g2)
    return sg.generate(n_bits)

# --- График 1: Сходимость доли единиц к 0.5 ---
lengths = [100, 500, 1000, 1984, 5000, 10000, 19840, 50000]
fractions = []

for N in lengths:
    seq = generate_sg_seq(N)
    fractions.append(sum(seq) / N)

plt.figure(figsize=(8, 5))
plt.plot(lengths, fractions, 'o-', color='blue', label='Доля единиц (p)')
plt.axhline(0.5, color='red', linestyle='--', label='Идеал (0.5)')
plt.xscale('log')
plt.xlabel('Длина последовательности N (лог. шкала)')
plt.ylabel('Доля единиц')
plt.title('Сходимость частоты единиц в SG-генераторе')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig('../report/plots/part1_fraction.png', dpi=150)
print("График 1 сохранен: report/plots/part1_fraction.png")
plt.close()

# --- График 2: Визуализация последовательности (0 и 1) ---
seq_100 = generate_sg_seq(100)
plt.figure(figsize=(10, 2))
plt.eventplot([i for i, bit in enumerate(seq_100) if bit == 1],
              colors='black', linewidths=2)
plt.xlim(0, 100)
plt.yticks([])
plt.xlabel('Номер бита')
plt.title('Расположение единиц в первых 100 битах (SG-генератор)')
plt.tight_layout()
plt.savefig('../report/plots/part1_bits.png', dpi=150)
print("График 2 сохранен: report/plots/part1_bits.png")
plt.close()