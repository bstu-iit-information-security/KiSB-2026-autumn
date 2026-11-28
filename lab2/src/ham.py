import os
import random
from pathlib import Path

MIN_DISTANCE = int(os.environ.get("MIN_DISTANCE", "3"))
ERROR_COUNTS = (0, 1, 2)
TEXT_FILE = "text.txt"

G_3 = [
    [1, 0, 0, 0, 0, 1, 1],
    [0, 1, 0, 0, 1, 0, 1],
    [0, 0, 1, 0, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1],
]
H_3 = [
    [0, 1, 1, 1, 1, 0, 0],
    [1, 0, 1, 1, 0, 1, 0],
    [1, 1, 0, 1, 0, 0, 1],
]
G_4 = [
    [1, 0, 0, 0, 0, 1, 1, 1],
    [0, 1, 0, 0, 1, 0, 1, 1],
    [0, 0, 1, 0, 1, 1, 0, 1],
    [0, 0, 0, 1, 1, 1, 1, 0],
]
H_4 = [
    [0, 1, 1, 1, 1, 0, 0, 0],
    [1, 0, 1, 1, 0, 1, 0, 0],
    [1, 1, 0, 1, 0, 0, 1, 0],
    [1, 1, 1, 1, 1, 1, 1, 1],
]

if MIN_DISTANCE == 3:
    G, H = G_3, H_3
elif MIN_DISTANCE == 4:
    G, H = G_4, H_4
else:
    raise ValueError("MIN_DISTANCE must be 3 or 4")

K = len(G)
R = len(H)
N = len(G[0])


def encode(x1):
    return [sum(x1[i] * G[i][j] for i in range(K)) % 2 for j in range(N)]


def syndrome(y):
    return [sum(row[j] * y[j] for j in range(N)) % 2 for row in H]


def recompute_redundant(y1):
    return [sum(y1[i] * G[i][j] for i in range(K)) % 2 for j in range(K, N)]


def error_vector(error_count):
    e = [0] * N
    for pos in random.sample(range(N), error_count):
        e[pos] = 1
    return e


def find_position(s):
    for j in range(N):
        if [H[i][j] for i in range(R)] == s:
            return j
    return None


def decode(y, error_count):
    s = syndrome(y)

    if not any(s):
        return y[:], s, "no errors detected", None

    pos = find_position(s)
    if MIN_DISTANCE == 3:
        if error_count == 1 and pos is not None:
            corrected = y[:]
            corrected[pos] ^= 1
            return corrected, s, "single error corrected", pos
        if error_count == 2:
            return y[:], s, "two errors detected but not correctable (d_min = 3)", None
        return y[:], s, "unexpected syndrome", None

    if s[-1] == 1 and pos is not None:
        corrected = y[:]
        corrected[pos] ^= 1
        return corrected, s, "single error corrected", pos
    return y[:], s, "two errors detected by overall parity, not corrected", None


def bits_to_text(bits):
    return "".join(chr(int(bits[i:i + 7], 2)) for i in range(0, len(bits) - 6, 7))


def main():
    random.seed(5)
    text_path = Path(__file__).with_name(TEXT_FILE)
    with open(text_path, "r", encoding="ascii") as f:
        text = f.read().rstrip("\n")

    bits = "".join(format(ord(ch), "07b") for ch in text)
    padding = (-len(bits)) % K
    padded = bits + "0" * padding
    blocks = [[int(bit) for bit in padded[i:i + K]]
              for i in range(0, len(padded), K)]

    print(f"d_min = {MIN_DISTANCE}, k = {K}, r = {R}, n = {N}")
    print("Source text:", text)
    print("Source message length in bits:", len(bits))
    print("Added zero bits:", padding)
    print("Matrix G:")
    for row in G:
        print(" ", row)
    print("Matrix H:")
    for row in H:
        print(" ", row)

    for error_count in ERROR_COUNTS:
        print(f"\n===== errors in each word: {error_count} =====")
        decoded_bits = ""
        corrections = 0
        detections = 0
        for number, x1 in enumerate(blocks, 1):
            x = encode(x1)
            x2 = x[K:]
            e = error_vector(error_count)
            y = [(x[i] + e[i]) % 2 for i in range(N)]
            corrected, s, status, pos = decode(y, error_count)
            if any(s):
                detections += 1
            if pos is not None:
                corrections += 1
            decoded_bits += "".join(str(b) for b in corrected[:K])

            if number == 1:
                print(f"Block {number}:")
                print("  X1 :", "".join(map(str, x1)))
                print("  X2 :", "".join(map(str, x2)))
                print("  X  :", "".join(map(str, x)))
                print("  E  :", "".join(map(str, e)))
                print("  Y1 :", "".join(map(str, y[:K])))
                print("  Y2 :", "".join(map(str, y[K:])))
                print("  Y2':", "".join(map(str, recompute_redundant(y[:K]))))
                print("  S  :", s)
                print("  Status:", status, "| corrected position:", None if pos is None else pos + 1)
                print("  Y' :", "".join(map(str, corrected)))
        print("Blocks:", len(blocks), "| detected:", detections, "| corrected:", corrections)
        print("Decoded bits:", decoded_bits[:len(bits)])
        if error_count == 0 or (error_count == 1) or (error_count == 2 and MIN_DISTANCE == 4):
            print("Decoded text:", bits_to_text(decoded_bits))
        else:
            print("Decoded text is not guaranteed (d_min = 3, two errors)")


if __name__ == "__main__":
    main()
