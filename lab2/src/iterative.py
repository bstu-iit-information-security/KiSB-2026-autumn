import random

CONFIGURATION = 4
PARITY_GROUPS = 5
ERROR_COUNT = 2
TRIALS = 100

INFORMATION_WORD = "10110010100101101100010111001010"

if CONFIGURATION == 1:
    K1 = 4
    K2 = 8
    Z = 0
elif CONFIGURATION == 2:
    K1 = 2
    K2 = 16
    Z = 0
elif CONFIGURATION == 3:
    K1 = 8
    K2 = 2
    Z = 2
else:
    K1 = 4
    K2 = 4
    Z = 2

if Z == 0:
    DIMENSIONS = 2
else:
    DIMENSIONS = 3

K = K1 * K2
if DIMENSIONS == 3:
    K = K * Z

DIAGONAL_COUNT = max(K1, K2)


def parity(bits):
    total = 0
    for bit in bits:
        total += bit
    return total % 2


def create_data(bits):
    data = []
    position = 0

    if DIMENSIONS == 2:
        plane = []
        for row in range(K1):
            line = []
            for column in range(K2):
                line.append(int(bits[position]))
                position += 1
            plane.append(line)
        data.append(plane)
    else:
        for layer in range(Z):
            plane = []
            for row in range(K1):
                line = []
                for column in range(K2):
                    line.append(int(bits[position]))
                    position += 1
                plane.append(line)
            data.append(plane)

    return data


def data_to_bits(data):
    bits = []
    for layer in data:
        for row in layer:
            for bit in row:
                bits.append(bit)
    return bits


def group_names():
    names = ["Horizontal", "Vertical"]

    if DIMENSIONS == 2:
        if PARITY_GROUPS == 3:
            names.append("Xhv")
    else:
        if PARITY_GROUPS >= 3:
            names.append("Diagonal_1")
        if PARITY_GROUPS >= 4:
            names.append("Diagonal_2")
        if PARITY_GROUPS >= 5:
            names.append("Depth")

    return names


def calculate_parities(data):
    names = group_names()
    groups = []

    horizontal = []
    for layer in range(len(data)):
        for row in range(K1):
            horizontal.append(parity(data[layer][row]))
    groups.append(horizontal)

    vertical = []
    for layer in range(len(data)):
        for column in range(K2):
            bits = []
            for row in range(K1):
                bits.append(data[layer][row][column])
            vertical.append(parity(bits))
    groups.append(vertical)

    if DIMENSIONS == 2 and PARITY_GROUPS == 3:
        all_bits = data_to_bits(data)
        for group in groups:
            for bit in group:
                all_bits.append(bit)
        groups.append([parity(all_bits)])

    if DIMENSIONS == 3 and PARITY_GROUPS >= 3:
        diagonal_1 = []
        for layer in range(Z):
            for diagonal in range(DIAGONAL_COUNT):
                bits = []
                for row in range(K1):
                    for column in range(K2):
                        if (row + column) % DIAGONAL_COUNT == diagonal:
                            bits.append(data[layer][row][column])
                diagonal_1.append(parity(bits))
        groups.append(diagonal_1)

    if DIMENSIONS == 3 and PARITY_GROUPS >= 4:
        diagonal_2 = []
        for layer in range(Z):
            for diagonal in range(DIAGONAL_COUNT):
                bits = []
                for row in range(K1):
                    for column in range(K2):
                        if (row - column) % DIAGONAL_COUNT == diagonal:
                            bits.append(data[layer][row][column])
                diagonal_2.append(parity(bits))
        groups.append(diagonal_2)

    if DIMENSIONS == 3 and PARITY_GROUPS >= 5:
        depth = []
        for row in range(K1):
            for column in range(K2):
                bits = []
                for layer in range(Z):
                    bits.append(data[layer][row][column])
                depth.append(parity(bits))
        groups.append(depth)

    return names, groups


def make_codeword(data):
    names, groups = calculate_parities(data)
    Xn = data_to_bits(data)
    for group in groups:
        for bit in group:
            Xn.append(bit)
    return names, groups, Xn


def split_codeword(word, names, group_lengths):
    data_bits = word[:K]
    data = create_data("".join(str(bit) for bit in data_bits))
    received_groups = []
    position = K

    for length in group_lengths:
        group = []
        for i in range(length):
            group.append(word[position])
            position += 1
        received_groups.append(group)

    return data, received_groups


def calculate_syndrome(data, received_groups):
    names, calculated_groups = calculate_parities(data)
    S = []

    for group_number in range(len(names)):
        group_syndrome = []
        for i in range(len(calculated_groups[group_number])):
            group_syndrome.append(
                (calculated_groups[group_number][i] + received_groups[group_number][i]) % 2
            )
        S.append(group_syndrome)

    return S


def syndrome_is_zero(S):
    for group in S:
        for bit in group:
            if bit == 1:
                return False
    return True


def index_in_group(group_name, layer, row, column):
    if group_name == "Horizontal":
        return layer * K1 + row
    if group_name == "Vertical":
        return layer * K2 + column
    if group_name == "Diagonal_1":
        return layer * DIAGONAL_COUNT + (row + column) % DIAGONAL_COUNT
    if group_name == "Diagonal_2":
        return layer * DIAGONAL_COUNT + (row - column) % DIAGONAL_COUNT
    if group_name == "Depth":
        return row * K2 + column
    return 0


def position_name(position, names, group_lengths):
    if position < K:
        if DIMENSIONS == 2:
            row = position // K2
            column = position % K2
            return "Xk[" + str(row + 1) + "][" + str(column + 1) + "]"

        layer = position // (K1 * K2)
        remainder = position % (K1 * K2)
        row = remainder // K2
        column = remainder % K2
        return (
            "Xk["
            + str(layer + 1)
            + "]["
            + str(row + 1)
            + "]["
            + str(column + 1)
            + "]"
        )

    position -= K
    for group_number in range(len(names)):
        if position < group_lengths[group_number]:
            return names[group_number] + "[" + str(position + 1) + "]"
        position -= group_lengths[group_number]

    return ""


def find_data_candidates(S, names):
    candidates = []

    for layer in range(len_data_layers):
        for row in range(K1):
            for column in range(K2):
                is_candidate = True
                for group_number in range(len(names)):
                    group_index = index_in_group(names[group_number], layer, row, column)
                    if S[group_number][group_index] != 1:
                        is_candidate = False
                if is_candidate:
                    candidates.append((layer, row, column))

    return candidates


def correct_codeword(Yn, names, group_lengths):
    data, received_groups = split_codeword(Yn, names, group_lengths)
    corrected_positions = []

    for step in range(ERROR_COUNT * 2):
        S = calculate_syndrome(data, received_groups)

        if syndrome_is_zero(S):
            break

        candidates = find_data_candidates(S, names)

        if len(candidates) == 1:
            layer, row, column = candidates[0]
            data[layer][row][column] = (data[layer][row][column] + 1) % 2
            data_position = layer * K1 * K2 + row * K2 + column
            corrected_positions.append(
                position_name(data_position, names, group_lengths)
            )
        else:
            parity_position_count = 0
            parity_group = 0
            parity_index = 0

            for group_number in range(len(S)):
                for i in range(len(S[group_number])):
                    if S[group_number][i] == 1:
                        parity_position_count += 1
                        parity_group = group_number
                        parity_index = i

            if parity_position_count == 1:
                received_groups[parity_group][parity_index] = (
                    received_groups[parity_group][parity_index] + 1
                ) % 2
                offset = K
                for i in range(parity_group):
                    offset += group_lengths[i]
                corrected_positions.append(
                    position_name(offset + parity_index, names, group_lengths)
                )
            else:
                break

    Y_prime = data_to_bits(data)
    for group in received_groups:
        for bit in group:
            Y_prime.append(bit)

    S_final = calculate_syndrome(data, received_groups)
    return Y_prime, S_final, corrected_positions


def create_received_word(Xn):
    En = [0] * len(Xn)
    positions = random.sample(range(len(Xn)), ERROR_COUNT)

    for position in positions:
        En[position] = 1

    Yn = []
    for i in range(len(Xn)):
        Yn.append((Xn[i] + En[i]) % 2)

    return En, Yn, positions


def print_data(data):
    for layer in range(len(data)):
        if DIMENSIONS == 3:
            print("Layer", layer + 1)
        for row in data[layer]:
            print(row)


data = create_data(INFORMATION_WORD)
names, Xr_groups, Xn = make_codeword(data)
group_lengths = []
for group in Xr_groups:
    group_lengths.append(len(group))

len_data_layers = len(data)

En, Yn, error_positions = create_received_word(Xn)
received_data, received_groups = split_codeword(Yn, names, group_lengths)
S = calculate_syndrome(received_data, received_groups)
Y_prime, S_prime, corrected_positions = correct_codeword(Yn, names, group_lengths)

print("Configuration:", CONFIGURATION)
print("Dimensions:", DIMENSIONS)
print("k1 =", K1)
print("k2 =", K2)
print("z =", Z)
print("k =", K)
print("r =", len(Xn) - K)
print("n =", len(Xn))
print("Parity groups:", PARITY_GROUPS)
print("Error count:", ERROR_COUNT)
print("Source information word Xk:", INFORMATION_WORD)
print("Information matrix:")
print_data(data)
print("Parity groups Xr:")
for i in range(len(names)):
    print(names[i] + ":", Xr_groups[i])
print("Codeword Xn:", "".join(str(bit) for bit in Xn))
print("Error vector En:", "".join(str(bit) for bit in En))
print("Injected error positions:")
for position in error_positions:
    print(position_name(position, names, group_lengths))
print("Received word Yn:", "".join(str(bit) for bit in Yn))
print("Received information matrix:")
print_data(received_data)
print("Syndrome groups:")
for i in range(len(names)):
    print(names[i] + ":", S[i])
print("Corrected positions:")
for position in corrected_positions:
    print(position)
print("Corrected word Y'n:", "".join(str(bit) for bit in Y_prime))
print("Final syndrome:")
for i in range(len(names)):
    print(names[i] + ":", S_prime[i])
print("Xn == Y'n:", Xn == Y_prime)

N1 = TRIALS
N2 = 0
N3 = 0

for trial in range(TRIALS):
    En_trial, Yn_trial, error_positions_trial = create_received_word(Xn)
    Y_prime_trial, S_prime_trial, corrected_positions_trial = correct_codeword(
        Yn_trial, names, group_lengths
    )

    actual_positions = []
    for position in error_positions_trial:
        actual_positions.append(position_name(position, names, group_lengths))

    if sorted(actual_positions) == sorted(corrected_positions_trial):
        N2 += 1

    if Xn == Y_prime_trial:
        N3 += 1

print("Analysis for", ERROR_COUNT, "random errors:")
print("N1 =", N1)
print("N2 =", N2)
print("N3 =", N3)
print("N2/N1 =", N2 / N1)
print("N3/N1 =", N3 / N1)
