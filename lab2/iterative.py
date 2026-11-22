import argparse
import random
from collections import Counter

VARIANTS = {
    1: [(4, 4, 1), (8, 2, 1), (4, 2, 2), (2, 4, 2)],
    2: [(4, 5, 1), (2, 10, 1), (2, 5, 2), (2, 2, 5)],
    3: [(4, 6, 1), (3, 8, 1), (3, 2, 4), (6, 2, 2)],
    4: [(4, 8, 1), (2, 16, 1), (8, 2, 2), (4, 4, 2)],
    5: [(5, 8, 1), (4, 10, 1), (5, 4, 2), (2, 10, 2)],
}
GROUP_NAMES = ["горизонтальные", "вертикальные", "диагональные", "обратные диагональные", "по оси z"]


class Code:
    def __init__(self, k1, k2, z, groups):
        self.k1, self.k2, self.z, self.groups = k1, k2, z, groups
        self.k = k1 * k2 * z
        self.checks = []
        self.names = []
        for g in range(groups):
            for cells in self.group_checks(g):
                self.checks.append(cells)
                self.names.append(g)
        self.r = len(self.checks)
        self.n = self.k + self.r
        self.cover = [[] for _ in range(self.k)]
        for c, cells in enumerate(self.checks):
            for x in cells:
                self.cover[x].append(c)

    def idx(self, p, i, j):
        return p * self.k1 * self.k2 + i * self.k2 + j

    def group_checks(self, g):
        k1, k2, z = self.k1, self.k2, self.z
        res = []
        if g == 0:
            for p in range(z):
                for i in range(k1):
                    res.append([self.idx(p, i, j) for j in range(k2)])
        elif g == 1:
            for p in range(z):
                for j in range(k2):
                    res.append([self.idx(p, i, j) for i in range(k1)])
        elif g == 2:
            for p in range(z):
                for d in range(k1 + k2 - 1):
                    res.append([self.idx(p, i, j) for i in range(k1) for j in range(k2)
                                if i - j + k2 - 1 == d])
        elif g == 3:
            for p in range(z):
                for s in range(k1 + k2 - 1):
                    res.append([self.idx(p, i, j) for i in range(k1) for j in range(k2)
                                if i + j == s])
        else:
            for i in range(k1):
                for j in range(k2):
                    res.append([self.idx(p, i, j) for p in range(z)])
        return res

    def encode(self, xk):
        return xk + [sum(xk[x] for x in cells) % 2 for cells in self.checks]

    def failed(self, y):
        return {c for c, cells in enumerate(self.checks)
                if (sum(y[x] for x in cells) + y[self.k + c]) % 2}

    def decode(self, y):
        y = y[:]
        flips = []
        while len(flips) <= self.n:
            f = self.failed(y)
            if not f:
                return y, flips, True
            cand = [x for x in range(self.k) if f.issuperset(self.cover[x])]
            cnt = Counter(c for x in cand for c in self.cover[x])
            sure = [x for x in cand if all(cnt[c] == 1 for c in self.cover[x])]
            if sure:
                pos = sure
            elif not cand and len(f) == 1:
                pos = [self.k + next(iter(f))]
            else:
                break
            for p in pos:
                y[p] ^= 1
            flips += pos
        return y, flips, False


def bstr(v):
    return "".join(map(str, v))


def show(code, xk, errors, seed=None):
    xn = code.encode(xk)
    yn = xn[:]
    for p in errors:
        yn[p] ^= 1
    f = code.failed(yn)
    y2, flips, ok = code.decode(yn)
    lines = [f"k1 = {code.k1}, k2 = {code.k2}, z = {code.z}, групп паритетов: {code.groups}",
             f"k = {code.k}, r = {code.r}, n = {code.n}",
             f"Информационное слово X_k: {bstr(xk)}"]
    pos = 0
    for g in range(code.groups):
        cnt = sum(1 for x in code.names if x == g)
        lines.append(f"  паритеты ({GROUP_NAMES[g]}): {bstr(xn[code.k + pos:code.k + pos + cnt])}")
        pos += cnt
    lines += [f"Кодовое слово X_n: {bstr(xn)}",
              f"Позиции ошибок (с 1): {[p + 1 for p in errors] or 'нет'}",
              f"Принятое слово Y_n: {bstr(yn)}",
              f"Нарушенные проверки: {sorted(c + 1 for c in f) or 'нет'}"]
    if ok:
        lines.append(f"Исправлены позиции: {[p + 1 for p in flips] or 'нет'}")
        lines.append(f"Слово после исправления Y_n': {bstr(y2)}")
        lines.append("Результат: " + ("слово восстановлено" if y2 == xn else "слово восстановлено неверно"))
    else:
        lines.append("Ошибки обнаружены, однозначно исправить не удалось")
    return "\n".join(lines)


def group_options(z):
    return [2, 3] if z == 1 else [2, 3, 4, 5]


def run_stat(variant, trials, mult, seed):
    rng = random.Random(seed)
    rows = []
    for cfg in VARIANTS[variant]:
        for g in group_options(cfg[2]):
            code = Code(*cfg, g)
            row = {"cfg": cfg, "groups": g, "r": code.r, "n": code.n}
            for i in mult:
                n2 = n3 = 0
                for _ in range(trials):
                    xk = [rng.randint(0, 1) for _ in range(code.k)]
                    xn = code.encode(xk)
                    yn = xn[:]
                    for p in rng.sample(range(code.n), i):
                        yn[p] ^= 1
                    y2, flips, ok = code.decode(yn)
                    if ok and len(flips) == i:
                        n2 += 1
                    if y2 == xn:
                        n3 += 1
                row[i] = (n2 / trials, n3 / trials)
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--variant", type=int, choices=VARIANTS, default=5)
    ap.add_argument("-c", "--config", type=int, default=1)
    ap.add_argument("-g", "--groups", type=int, default=2)
    ap.add_argument("-e", "--errors", type=int, default=1)
    ap.add_argument("-b", "--bits")
    ap.add_argument("-s", "--seed", type=int)
    ap.add_argument("-n", type=int, default=2000)
    ap.add_argument("--stat", action="store_true")
    a = ap.parse_args()
    if a.stat:
        for row in run_stat(a.variant, a.n, [1, 2, 3, 4], a.seed):
            print(row)
        return
    cfg = VARIANTS[a.variant][a.config - 1]
    if a.groups not in group_options(cfg[2]):
        raise SystemExit(f"для этой конфигурации допустимы группы {group_options(cfg[2])}")
    code = Code(*cfg, a.groups)
    rng = random.Random(a.seed)
    if a.bits:
        xk = [int(c) for c in a.bits]
        if len(xk) != code.k:
            raise SystemExit(f"длина слова должна быть {code.k}")
    else:
        xk = [rng.randint(0, 1) for _ in range(code.k)]
    errors = sorted(rng.sample(range(code.n), a.errors))
    print(show(code, xk, errors))


if __name__ == "__main__":
    main()
