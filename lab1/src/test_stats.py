from lfsr import LFSR
from shrinking import ShrinkingGenerator
from stats import freq_test, chi_square_test

# Будем использовать те самые сиды, которые дают максимальный период
SEED1 = 0b00001
SEED2 = 0b0000001


def generate_sg_seq(n_bits):
    g1 = LFSR(taps_mask=0b00101, n=5, seed=SEED1)  # f1
    g2 = LFSR(taps_mask=0b0000011, n=7, seed=SEED2)  # x^7+x+1
    sg = ShrinkingGenerator(g1, g2)
    return sg.generate(n_bits)


print(
    f"{'Длина (N)':>10} | {'Единиц':>7} | {'Нулей':>6} | {'Доля (p)':>9} | {'z-стат':>7} | {'Равном.?':>8} | {'Хи-квадрат':>10}")
print("-" * 75)

# Проверяем на разных длинах, кратных периоду (1984) и не кратных
lengths = [100, 500, 1000, 1984, 5000, 10000]

for n in lengths:
    seq = generate_sg_seq(n)

    # Частотный тест
    res_freq = freq_test(seq)

    # Хи-квадрат
    chi2 = chi_square_test(seq, alphabet_size=2)

    # Вывод
    print(f"{n:>10} | {res_freq['ones']:>7} | {res_freq['zeros']:>6} | "
          f"{res_freq['p_hat']:>9.4f} | {res_freq['z']:>7.3f} | "
          f"{str(res_freq['uniform']):>8} | {chi2:>10.3f}")

print("\nПримечания к таблице:")
print("- 'Равном.?' = True, если |z| < 1.96 (доверительная вероятность 95%)")
print("- 'Хи-квадрат' должен быть < 3.841 для alpha=0.05 (df=1)")