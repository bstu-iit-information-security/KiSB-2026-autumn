import argparse
import random


def text_to_bits(text):
    return [int(c) for b in text.encode("cp1251", "replace") for c in format(b, "08b")]


def calc_r(k):
    r = 1
    while 2 ** r < k + r + 1:
        r += 1
    return r


def build_matrix(k, d=3):
    r = calc_r(k)
    nums = sorted((n for n in range(3, 2 ** r) if n & (n - 1)),
                  key=lambda n: (bin(n).count("1"), n))
    cols = [[(n >> (r - 1 - i)) & 1 for i in range(r)] for n in nums[:k]]
    if d == 4:
        cols = [c + [1 - sum(c) % 2] for c in cols]
        r += 1
    return [[c[i] for c in cols] + [int(i == j) for j in range(r)] for i in range(r)]


def syndrome_table(H):
    return {tuple(row[j] for row in H): j for j in range(len(H[0]))}


def encode(xk, H):
    k = len(xk)
    return [sum(h & x for h, x in zip(row[:k], xk)) % 2 for row in H]


def decode(y, H, k, table=None):
    table = table or syndrome_table(H)
    yr = y[k:]
    yr2 = encode(y[:k], H)
    s = [a ^ b for a, b in zip(yr, yr2)]
    res = {"yr": yr, "yr2": yr2, "s": s, "pos": None, "e": [0] * len(y), "y": y[:]}
    if not any(s):
        res["status"] = "none"
        return res
    pos = table.get(tuple(s))
    if pos is None:
        res["status"] = "detected"
        return res
    res["status"] = "corrected"
    res["pos"] = pos
    res["e"][pos] = 1
    res["y"][pos] ^= 1
    return res


def bstr(v):
    return "".join(map(str, v))


def make_report(text, bits, d, positions, seed):
    k = len(bits)
    H = build_matrix(k, d)
    r = len(H)
    n = k + r
    xr = encode(bits, H)
    xn = bits + xr
    yn = xn[:]
    for p in positions:
        yn[p] ^= 1
    res = decode(yn, H, k)
    lines = [f"Сообщение: {text}",
             f"Информационное слово X_k: {bstr(bits)}",
             f"k = {k}, r = {r}, n = {n}, d_min = {d}",
             "Проверочная матрица H:"]
    lines += ["  " + bstr(row) for row in H]
    lines += [f"Избыточные символы X_r: {bstr(xr)}",
              f"Кодовое слово X_n: {bstr(xn)}",
              f"Позиции ошибок (с 1): {[p + 1 for p in positions] or 'нет'}",
              f"Принятое слово Y_n: {bstr(yn)}",
              f"Y_r: {bstr(res['yr'])}",
              f"Y_r': {bstr(res['yr2'])}",
              f"Синдром S: {bstr(res['s'])}"]
    if res["status"] == "none":
        lines.append("Синдром нулевой, ошибок не обнаружено")
    elif res["status"] == "detected":
        lines.append("Синдром не совпадает ни с одним столбцом H: обнаружена ошибка, "
                     "исправление невозможно")
    else:
        lines.append(f"Синдром совпал со столбцом {res['pos'] + 1}")
        lines.append(f"Вектор ошибки E_n: {bstr(res['e'])}")
        lines.append(f"Исправленное слово: {bstr(res['y'])}")
        lines.append("Результат: " + ("слово восстановлено" if res["y"] == xn
                                      else "слово восстановлено неверно"))
    return "\n".join(lines)


def run_stat(bits, ks, trials, seed):
    rng = random.Random(seed)
    rows = []
    for k in ks:
        xk = bits[:k]
        for d in (3, 4):
            H = build_matrix(k, d)
            table = syndrome_table(H)
            xn = xk + encode(xk, H)
            row = {"k": k, "r": len(H), "n": len(xn), "d": d}
            for e in (1, 2):
                good = bad = det = 0
                for _ in range(trials):
                    yn = xn[:]
                    for p in rng.sample(range(len(xn)), e):
                        yn[p] ^= 1
                    res = decode(yn, H, k, table)
                    if res["status"] == "detected":
                        det += 1
                    elif res["y"] == xn:
                        good += 1
                    else:
                        bad += 1
                row[e] = (good, bad, det)
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("-d", type=int, choices=(3, 4), default=3)
    ap.add_argument("-e", type=int, choices=(0, 1, 2), default=1)
    ap.add_argument("-k", type=int)
    ap.add_argument("-s", "--seed", type=int)
    ap.add_argument("-o", "--out")
    ap.add_argument("--stat", action="store_true")
    ap.add_argument("-n", type=int, default=2000)
    a = ap.parse_args()
    text = open(a.file, encoding="utf-8").read().strip()
    bits = text_to_bits(text)
    if a.stat:
        for r in run_stat(bits, [16, 24, 64, 256, 1024], a.n, a.seed):
            print(r)
        return
    if a.k:
        bits = bits[:a.k]
        text = text[:(a.k + 7) // 8]
    if len(bits) < 16:
        raise SystemExit("длина сообщения должна быть не менее 16 бит")
    rng = random.Random(a.seed)
    k = len(bits)
    n = k + len(build_matrix(k, a.d))
    positions = sorted(rng.sample(range(n), a.e))
    out = make_report(text, bits, a.d, positions, a.seed)
    print(out)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(out + "\n")


if __name__ == "__main__":
    main()
