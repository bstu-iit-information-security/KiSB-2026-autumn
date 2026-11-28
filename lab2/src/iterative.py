import random

K1 = 5
K2 = 4
Z = 2
PARITY_GROUPS = 5
ERROR_COUNTS = (1, 2, 3)
TRIALS = 1000
INFORMATION_WORD = "1011001010010110110001011100101001101010"

DIMENSIONS = 3 if Z else 2
K = K1 * K2 * (Z if DIMENSIONS == 3 else 1)
DIAGONALS = max(K1, K2)


def parity(bits):
    return sum(bits) % 2


def create_data(bits):
    data = []
    pos = 0
    layers = Z if DIMENSIONS == 3 else 1
    for _ in range(layers):
        plane = []
        for _ in range(K1):
            row = [int(bits[pos + c]) for c in range(K2)]
            pos += K2
            plane.append(row)
        data.append(plane)
    return data


def data_to_bits(data):
    return [bit for plane in data for row in plane for bit in row]


def group_names():
    names = ["Horizontal", "Vertical"]
    if DIMENSIONS == 2:
        if PARITY_GROUPS >= 3:
            names.append("Xhv")
    else:
        if PARITY_GROUPS >= 3:
            names.append("Diagonal_1")
        if PARITY_GROUPS >= 4:
            names.append("Diagonal_2")
        if PARITY_GROUPS >= 5:
            names.append("Depth")
    return names[:PARITY_GROUPS]


def calculate_parities(data):
    names = group_names()
    groups = []

    horizontal = [parity(data[layer][row])
                  for layer in range(len(data)) for row in range(K1)]
    groups.append(horizontal)

    vertical = [parity([data[layer][row][col] for row in range(K1)])
                for layer in range(len(data)) for col in range(K2)]
    groups.append(vertical)

    if DIMENSIONS == 2 and PARITY_GROUPS >= 3:
        bits = data_to_bits(data)
        for group in groups:
            bits.extend(group)
        groups.append([parity(bits)])

    if DIMENSIONS == 3 and PARITY_GROUPS >= 3:
        diagonal_1 = []
        for layer in range(Z):
            for d in range(DIAGONALS):
                bits = [data[layer][r][c] for r in range(K1) for c in range(K2)
                        if (r + c) % DIAGONALS == d]
                diagonal_1.append(parity(bits))
        groups.append(diagonal_1)

    if DIMENSIONS == 3 and PARITY_GROUPS >= 4:
        diagonal_2 = []
        for layer in range(Z):
            for d in range(DIAGONALS):
                bits = [data[layer][r][c] for r in range(K1) for c in range(K2)
                        if (r - c) % DIAGONALS == d]
                diagonal_2.append(parity(bits))
        groups.append(diagonal_2)

    if DIMENSIONS == 3 and PARITY_GROUPS >= 5:
        depth = [parity([data[layer][r][c] for layer in range(Z)])
                 for r in range(K1) for c in range(K2)]
        groups.append(depth)

    return names, groups[:PARITY_GROUPS]


def make_codeword(data):
    names, groups = calculate_parities(data)
    word = data_to_bits(data)
    for group in groups:
        word.extend(group)
    return names, groups, word


def split_word(word, names, group_lengths):
    data = create_data("".join(str(b) for b in word[:K]))
    received = []
    pos = K
    for length in group_lengths:
        received.append(word[pos:pos + length])
        pos += length
    return data, received


def calculate_syndrome(data, received):
    names, expected = calculate_parities(data)
    return [[(expected[g][i] + received[g][i]) % 2
             for i in range(len(expected[g]))] for g in range(len(names))]


def syndrome_is_zero(s):
    return all(bit == 0 for group in s for bit in group)


def index_in_group(name, layer, row, col):
    if name == "Horizontal":
        return layer * K1 + row
    if name == "Vertical":
        return layer * K2 + col
    if name == "Diagonal_1":
        return layer * DIAGONALS + (row + col) % DIAGONALS
    if name == "Diagonal_2":
        return layer * DIAGONALS + (row - col) % DIAGONALS
    if name == "Depth":
        return row * K2 + col
    return 0


def position_name(position, names, group_lengths):
    if position < K:
        if DIMENSIONS == 2:
            return f"Xk[{position // K2 + 1}][{position % K2 + 1}]"
        layer = position // (K1 * K2)
        rest = position % (K1 * K2)
        return f"Xk[{layer + 1}][{rest // K2 + 1}][{rest % K2 + 1}]"
    position -= K
    for g, length in enumerate(group_lengths):
        if position < length:
            return f"{names[g]}[{position + 1}]"
        position -= length
    return ""


def find_candidates(s, names, layers):
    candidates = []
    for layer in range(layers):
        for row in range(K1):
            for col in range(K2):
                if all(s[g][index_in_group(names[g], layer, row, col)] == 1
                       for g in range(len(names))):
                    candidates.append((layer, row, col))
    return candidates


def correct_word(word, names, group_lengths, max_steps):
    data, received = split_word(word, names, group_lengths)
    layers = len(data)
    flipped = []

    for _ in range(max_steps):
        s = calculate_syndrome(data, received)
        if syndrome_is_zero(s):
            break
        candidates = find_candidates(s, names, layers)
        if len(candidates) == 1:
            layer, row, col = candidates[0]
            data[layer][row][col] ^= 1
            position = layer * K1 * K2 + row * K2 + col
            flipped.append(position_name(position, names, group_lengths))
        else:
            ones = [(g, i) for g in range(len(s)) for i in range(len(s[g])) if s[g][i]]
            if len(ones) == 1:
                g, i = ones[0]
                received[g][i] ^= 1
                offset = K + sum(group_lengths[:g])
                flipped.append(position_name(offset + i, names, group_lengths))
            else:
                break

    corrected = data_to_bits(data)
    for group in received:
        corrected.extend(group)
    return corrected, calculate_syndrome(data, received), flipped


def inject_errors(word, error_count):
    e = [0] * len(word)
    positions = random.sample(range(len(word)), error_count)
    for p in positions:
        e[p] = 1
    return e, [(word[i] + e[i]) % 2 for i in range(len(word))], positions


def main():
    random.seed(5)
    assert len(INFORMATION_WORD) == K, (len(INFORMATION_WORD), K)
    data = create_data(INFORMATION_WORD)
    names, groups, xn = make_codeword(data)
    group_lengths = [len(g) for g in groups]
    n = len(xn)

    print(f"variant 5: k1={K1}, k2={K2}, z={Z}, k={K}, r={n - K}, n={n}")
    print("Parity groups:", ", ".join(names))
    print("Information matrix:")
    for layer in range(len(data)):
        if DIMENSIONS == 3:
            print("  Layer", layer + 1)
        for row in data[layer]:
            print("   ", row)
    print("Parity groups Xr:")
    for name, group in zip(names, groups):
        print("  " + name + ":", "".join(map(str, group)))
    print("Codeword Xn:", "".join(map(str, xn)))

    e, yn, positions = inject_errors(xn, 2)
    yn_prime, s_final, flipped = correct_word(yn, names, group_lengths, 4)
    print("\nExample with 2 errors:")
    print("  E :", "".join(map(str, e)))
    print("  error positions:", [position_name(p, names, group_lengths) for p in positions])
    print("  Yn:", "".join(map(str, yn)))
    print("  corrected positions:", flipped)
    print("  Y'n:", "".join(map(str, yn_prime)))
    print("  final syndrome zero:", syndrome_is_zero(s_final))
    print("  Xn == Y'n:", xn == yn_prime)

    print(f"\nAnalysis ({TRIALS} trials per multiplicity):")
    print(" i |   N1 |   N2 |   N3 | N2/N1 | N3/N1")
    for error_count in ERROR_COUNTS:
        n1 = TRIALS
        n2 = n3 = 0
        for _ in range(TRIALS):
            e_t, yn_t, pos_t = inject_errors(xn, error_count)
            yp_t, _, flipped_t = correct_word(yn_t, names, group_lengths, error_count * 2)
            actual = sorted(position_name(p, names, group_lengths) for p in pos_t)
            if actual == sorted(flipped_t):
                n2 += 1
            if xn == yp_t:
                n3 += 1
        print(f" {error_count} | {n1:5d} | {n2:5d} | {n3:5d} | {n2/n1:5.3f} | {n3/n1:5.3f}")


if __name__ == "__main__":
    main()
