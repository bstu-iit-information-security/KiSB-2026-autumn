from lfsr import LFSR
from shrinking import ShrinkingGenerator


def get_sg_period(seed1, seed2, max_bits=5000):
    g1 = LFSR(taps_mask=0b00101, n=5, seed=seed1)
    g2 = LFSR(taps_mask=0b0000011, n=7, seed=seed2)
    sg = ShrinkingGenerator(g1, g2)

    sequence = []
    states = []

    while len(sequence) < max_bits:
        state_pair = (g1.state, g2.state)
        if state_pair in states:
            first_occurrence = states.index(state_pair)
            return len(sequence) - first_occurrence
        states.append(state_pair)
        sequence.append(sg.next_bit())
    return -1


# Проверяем конкретные сиды, которые дают максимальный период
s1 = 0b00001  # 1
s2 = 0b0000001  # 1

print(f"Проверяем SG-генератор с seed1={s1:05b} и seed2={s2:07b}...")
p = get_sg_period(s1, s2)
print(f"Период выходной последовательности: {p}")
print(f"Теоретический максимум T = (2^5 - 1) * 2^(7-1) = 31 * 64 = 1984")