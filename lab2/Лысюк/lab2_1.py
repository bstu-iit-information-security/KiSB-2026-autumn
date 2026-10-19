import sys
import random

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def hamming_r(k):
    r = 1
    while (1 << r) < k + r + 1:
        r += 1
    return r


def build_h(k, r):
    n = k + r
    cols = []
    used = set()
    wt = 1
    while len(cols) < k:
        for v in range(1, 1 << r):
            if v in used:
                continue
            if bin(v).count("1") == wt:
                cols.append(v)
                used.add(v)
                if len(cols) == k:
                    break
        wt += 1
    for i in range(r):
        cols.append(1 << i)
    H = [[(cols[c] >> i) & 1 for c in range(n)] for i in range(r)]
    return H, n


def encode_h(X, H, extended):
    Xr = []
    for row in H:
        s = 0
        for j in range(len(X)):
            s ^= X[j] & row[j]
        Xr.append(s)
    Xn = X + Xr
    if extended:
        Xn = Xn + [sum(Xn) % 2]
    return Xn


def syndrome(Y, H):
    return [sum(Y[j] & row[j] for j in range(len(Y))) % 2 for row in H]


def decode_h(Y, H, k, n, extended):
    if extended:
        body = Y[:n]
        total = sum(body) % 2
        S = syndrome(body, H)
        if all(s == 0 for s in S) and total == 0:
            return Y[:k], S, None
        if all(s == 0 for s in S) and total == 1:
            # ошибка в самом проверочном бите чётности
            Y2 = Y[:]
            Y2[-1] ^= 1
            return Y2[:k], S, n
        for c in range(n):
            col = [H[i][c] for i in range(len(H))]
            if col == S:
                Y2 = Y[:]
                Y2[c] ^= 1
                return Y2[:k], S, c
        return Y[:k], S, None
    else:
        S = syndrome(Y, H)
        if all(s == 0 for s in S):
            return Y[:k], S, None
        for c in range(n):
            col = [H[i][c] for i in range(len(H))]
            if col == S:
                Y2 = Y[:]
                Y2[c] ^= 1
                return Y2[:k], S, c
        return Y[:k], S, None


def run():
    print("=== LAB 2.1. Hamming code ===")
    k = 16
    for dmin in (3, 4):
        r = hamming_r(k)
        H, n = build_h(k, r)
        extended = (dmin == 4)
        info = [random.randint(0, 1) for _ in range(k)]
        Xn = encode_h(info, H, extended)
        print(f"\nk={k} r={r} n={len(Xn)} dmin={dmin}")
        print(f"  Xk = {''.join(map(str, info))}")
        print(f"  Xn = {''.join(map(str, Xn))}")
        for err in (0, 1, 2):
            Y = Xn[:]
            pos = random.sample(range(len(Xn)), err)
            for p in pos:
                Y[p] ^= 1
            dec, S, fixed = decode_h(Y, H, k, n, extended)
            ok = dec == info
            print(f"  err={err} pos={pos} S={''.join(map(str, S))} "
                  f"fixed={fixed} decoded_ok={ok}")


if __name__ == "__main__":
    random.seed(20241018)
    run()