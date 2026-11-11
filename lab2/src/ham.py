import random

MIN_DISTANCE = 3
ERROR_COUNT = 1

G_3 = [
    [1, 0, 0, 0, 0, 1, 1],
    [0, 1, 0, 0, 1, 0, 1],
    [0, 0, 1, 0, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1]
]

H_3 = [
    [0, 1, 1, 1, 1, 0, 0],
    [1, 0, 1, 1, 0, 1, 0],
    [1, 1, 0, 1, 0, 0, 1]
]

G_4 = [
    [1, 0, 0, 0, 0, 1, 1, 1],
    [0, 1, 0, 0, 1, 0, 1, 1],
    [0, 0, 1, 0, 1, 1, 0, 1],
    [0, 0, 0, 1, 1, 1, 1, 0]
]

H_4 = [
    [0, 1, 1, 1, 1, 0, 0, 0],
    [1, 0, 1, 1, 0, 1, 0, 0],
    [1, 1, 0, 1, 0, 0, 1, 0],
    [1, 1, 1, 1, 1, 1, 1, 1]
]

K = 4

if MIN_DISTANCE == 3:
    G = G_3
    H = H_3
elif MIN_DISTANCE == 4:
    G = G_4
    H = H_4

R = len(H)
N = len(G[0])


def encode_block(Xk):
    Xn = []
    for column in range(N):
        total = 0
        for row in range(K):
            total += Xk[row] * G[row][column]
        Xn.append(total % 2)
    return Xn


def calculate_syndrome(Yn):
    S = []
    for row in H:
        total = 0
        for i in range(N):
            total += Yn[i] * row[i]
        S.append(total % 2)
    return S


def add_modulo_2(first_vector, second_vector):
    result = []
    for i in range(N):
        result.append((first_vector[i] + second_vector[i]) % 2)
    return result


def create_error_vector():
    En = [0] * N
    positions = random.sample(range(N), ERROR_COUNT)
    for position in positions:
        En[position] = 1
    return En


def find_error_position(S):
    for column in range(N):
        H_column = []
        for row in range(R):
            H_column.append(H[row][column])
        if H_column == S:
            return column
    return None


def correct_word(Yn, S):
    Y_prime = Yn[:]
    position = find_error_position(S)

    if S == [0] * R:
        return Y_prime, position, "No errors detected"

    if MIN_DISTANCE == 3:
        if ERROR_COUNT == 1 and position is not None:
            Y_prime[position] = (Y_prime[position] + 1) % 2
            return Y_prime, position, "Single error corrected"
        return Y_prime, position, "Two errors cannot be detected or corrected"

    if S[-1] == 1 and position is not None:
        Y_prime[position] = (Y_prime[position] + 1) % 2
        return Y_prime, position, "Single error corrected"

    return Y_prime, position, "Two errors detected by the additional parity check and not corrected"


def bits_to_text(bits):
    result = ""
    for i in range(0, len(bits), 7):
        result += chr(int(bits[i:i + 7], 2))
    return result


with open("text.txt", "r", encoding="ascii") as file:
    text = file.read().rstrip("\n")

bits = ""
for symbol in text:
    bits += format(ord(symbol), "07b")

message_length = len(bits)
padding = (-message_length) % K
bits_with_padding = bits + "0" * padding

Xk_blocks = []
Xn_words = []
En_vectors = []
Yn_words = []
S_vectors = []
Y_prime_words = []
error_positions = []
statuses = []

for i in range(0, len(bits_with_padding), K):
    Xk = []
    for bit in bits_with_padding[i:i + K]:
        Xk.append(int(bit))

    Xn = encode_block(Xk)
    En = create_error_vector()
    Yn = add_modulo_2(Xn, En)
    S = calculate_syndrome(Yn)
    Y_prime, position, status = correct_word(Yn, S)

    Xk_blocks.append(Xk)
    Xn_words.append(Xn)
    En_vectors.append(En)
    Yn_words.append(Yn)
    S_vectors.append(S)
    Y_prime_words.append(Y_prime)
    error_positions.append(position)
    statuses.append(status)

decoded_bits = ""
for Y_prime in Y_prime_words:
    for bit in Y_prime[:K]:
        decoded_bits += str(bit)

decoded_bits = decoded_bits[:message_length]

print("d_min =", MIN_DISTANCE)
print("k =", K)
print("r =", R)
print("n =", N)
print("Number of random errors in each word:", ERROR_COUNT)
print("Source text:", text)
print("ASCII binary form (7 bits):", bits)
print("Source message length in bits:", message_length)
print("Added zero bits:", padding)
print("Bits with padding:", bits_with_padding)
print("Matrix G:")
for row in G:
    print(row)
print("Matrix H:")
for row in H:
    print(row)

for i in range(len(Xk_blocks)):
    print()
    print("Block", i + 1)
    print("Xk:", Xk_blocks[i])
    print("Xn:", Xn_words[i])
    print("Xr:", Xn_words[i][K:])
    print("En:", En_vectors[i])
    print("Yn:", Yn_words[i])
    print("Yr:", Yn_words[i][K:])
    print("S = H * Yn^T:", S_vectors[i])
    print("Status:", statuses[i])
    if error_positions[i] is not None:
        print("Syndrome position:", error_positions[i] + 1)
    print("Y'n:", Y_prime_words[i])
    print("Yr':", Y_prime_words[i][K:])

print()
print("Decoded bits without added zero bits:", decoded_bits)
if MIN_DISTANCE == 3 and ERROR_COUNT == 2:
    print("Decoded text is not guaranteed after two errors")
else:
    print("Decoded text:", bits_to_text(decoded_bits))
