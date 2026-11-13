import sys
import random

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def build_rect(k, k1, k2):
    grid = [[0] * k2 for _ in range(k1)]
    for i in range(k):
        grid[i // k2][i % k2] = random.randint(0, 1)
    return grid


def encode_rect(grid, groups):
    rows = len(grid)
    cols = len(grid[0])
    rh = [sum(grid[i]) % 2 for i in range(rows)]
    rv = [sum(grid[i][j] for i in range(rows)) % 2 for j in range(cols)]
    rhv = sum(rh) % 2
    extra = rh + rv
    if groups >= 3:
        extra.append(rhv)
    if groups >= 4:
        d1 = [sum(grid[i][(i + t) % cols] for i in range(rows)) % 2 for t in range(cols)]
        extra += d1
    if groups >= 5:
        d2 = [sum(grid[i][(cols - 1 - i + t) % cols] for i in range(rows)) % 2 for t in range(cols)]
        extra += d2
    return grid, rh, rv, rhv, extra


def detect_rect(grid, rh, rv, rhv, groups):
    rows = len(grid)
    cols = len(grid[0])
    rh2 = [sum(grid[i]) % 2 for i in range(rows)]
    rv2 = [sum(grid[i][j] for i in range(rows)) % 2 for j in range(cols)]
    rhv2 = sum(rh2) % 2
    bad_rows = [i for i in range(rows) if rh[i] != rh2[i]]
    bad_cols = [j for j in range(cols) if rv[j] != rv2[j]]
    result = []
    if len(bad_rows) == 1 and len(bad_cols) == 1:
        result.append((bad_rows[0], bad_cols[0]))
    return result, rhv != rhv2, bad_rows, bad_cols


def fix_rect(grid, positions):
    for i, j in positions:
        grid[i][j] ^= 1


def run():
    print("=== LAB 2.2. Iterative (rectangular) code ===")
    k = 32
    for k1, k2 in [(4, 8), (2, 16), (8, 4)]:
        print(f"\nk={k}  k1={k1}  k2={k2}")
        for groups in (2, 3, 4, 5):
            grid = build_rect(k, k1, k2)
            orig = [row[:] for row in grid]
            grid, rh, rv, rhv, extra = encode_rect(grid, groups)
            for err in (1, 2, 3):
                g2 = [row[:] for row in grid]
                pos = random.sample([(i, j) for i in range(k1) for j in range(k2)], err)
                for i, j in pos:
                    g2[i][j] ^= 1
                found, rhv_bad, br, bc = detect_rect(g2, rh, rv, rhv, groups)
                fix_rect(g2, found)
                ok = g2 == orig
                print(f"  groups={groups} err={err} pos={pos} "
                      f"detected={len(found)} bad_rows={br} bad_cols={bc} decoded_ok={ok}")


if __name__ == "__main__":
    random.seed(20241018)
    run()