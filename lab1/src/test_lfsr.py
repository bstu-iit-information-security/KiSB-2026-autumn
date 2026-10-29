from lfsr import LFSR

# Наш многочлен f1: x^5 + x^2 + 1.
# В коде выше мы сдвигаем вправо, поэтому маска отводов:
# бит 0 (x^0) и бит 2 (x^2) -> 0b00101 = 5
MASK_F1 = 0b00101

print("Тестируем LFSR на основе f1 (x^5 + x^2 + 1)")
for seed in [1, 5, 0b10101]:
    lfsr = LFSR(taps_mask=MASK_F1, n=5, seed=seed)
    period = lfsr.get_period()
    print(f"seed = {seed:05b} (bin) | Период = {period}")

print("\nТестируем LFSR на основе f2 (x^5 + x^4 + x^3 + x^2 + 1)")
# f2: отводы на битах 0, 2, 3, 4 -> 0b11101 = 29
MASK_F2 = 0b11101
lfsr2 = LFSR(taps_mask=MASK_F2, n=5, seed=1)
print(f"seed = 00001 (bin) | Период = {lfsr2.get_period()}")