import argparse
import csv
import random
from itertools import combinations
 
K = 32
VARIANT_4 = [
    ((4, 8), (2, 3)),
    ((2, 16), (2, 3)),
    ((8, 2, 2), (2, 3, 4, 5)),
    ((4, 4, 2), (2, 3, 4, 5)),
]
GROUP_NAME = {
    "h": "горизонтальные", "v": "вертикальные", "z": "по оси Z",
    "d1": "диагональные (1)", "d2": "диагональные (2)",
}
 
 
def fmt(bits):
    return "".join(map(str, bits))
 
 
class IterCode:
    def __init__(self, dims, ngroups):
        self.k1, self.k2 = dims[0], dims[1]
        self.z = dims[2] if len(dims) > 2 else 1
        self.k = self.k1 * self.k2 * self.z
        order = ["h", "v", "z", "d1", "d2"] if self.z > 1 else ["h", "v", "d1"]
        self.groups = order[:ngroups]
        M = max(self.k1, self.k2)         
 
        def key(g, i, j, p):
            return {"h": (p, i), "v": (p, j), "z": (i, j),
                    "d1": (p, (j - i) % M), "d2": (p, (i + j) % M)}[g]
 
        self.cell = []
        for t in range(self.k):
            p, rem = divmod(t, self.k1 * self.k2)
            self.cell.append((rem // self.k2, rem % self.k2, p))
 
        self.checks, self.check_group = [], []      
        for g in self.groups:
            lines = {}
            for t, (i, j, p) in enumerate(self.cell):
                lines.setdefault(key(g, i, j, p), []).append(t)
            for kk in sorted(lines):
                self.checks.append(lines[kk])
                self.check_group.append(g)
        self.r = len(self.checks)
        self.n = self.k + self.r
 
    def title(self):
        d = "x".join(map(str, (self.k1, self.k2) + ((self.z,) if self.z > 1 else ())))
        return f"{d}, групп паритетов: {len(self.groups)} ({', '.join(self.groups)})"
 
    def encode(self, xk):
        xr = [sum(xk[t] for t in idx) % 2 for idx in self.checks]
        return xk + xr
 
    def syndrome(self, y):
        return [(sum(y[t] for t in idx) + y[self.k + c]) % 2 for c, idx in enumerate(self.checks)]
 
    def _tables(self):
        if hasattr(self, "_col"):
            return
        col = [0] * self.n
        for c, idx in enumerate(self.checks):
            for t in idx:
                col[t] |= 1 << c
            col[self.k + c] |= 1 << c
        self._col = col
        self._single, self._pairs = {}, {}
        for a in range(self.n):
            self._single.setdefault(col[a], []).append(a)
            for b in range(a + 1, self.n):
                self._pairs.setdefault(col[a] ^ col[b], []).append((a, b))
 
    def decode(self, y):
        self._tables()
        col = self._col
        y = y[:]
        s = 0
        for b in range(self.n):
            if y[b]:
                s ^= col[b]
        if s == 0:
            return y, 0, True
        found = self._single.get(s, [])
        if found:
            cands = [(a,) for a in found]
        else:
            cands = self._pairs.get(s, [])
            if not cands:
                cs = set()
                for b in range(self.n):
                    for (a, c) in self._pairs.get(s ^ col[b], []):
                        if b != a and b != c:
                            cs.add(tuple(sorted((a, b, c))))
                cands = list(cs)
        if len(cands) != 1:
            return y, 0, False
        for q in cands[0]:
            y[q] ^= 1
        return y, len(cands[0]), True
 
    def dmin(self, max_w=7):
        col = [0] * self.n
        for c, idx in enumerate(self.checks):
            for t in idx:
                col[t] |= 1 << c
            col[self.k + c] |= 1 << c
        for w in range(1, max_w + 1):
            a = w // 2
            if w == 1:
                if any(c == 0 for c in col):
                    return 1
                continue
            seen = set()
            if w % 2 == 0:
                for sub in combinations(range(self.n), a):
                    x = 0
                    for b in sub:
                        x ^= col[b]
                    if x in seen:
                        return w
                    seen.add(x)
            else:
                for sub in combinations(range(self.n), a):
                    x = 0
                    for b in sub:
                        x ^= col[b]
                    seen.add(x)
                for sub in combinations(range(self.n), a + 1):
                    x = 0
                    for b in sub:
                        x ^= col[b]
                    if x in seen:
                        return w
        return None
 
 
def demo(code, xk, nerr, rng, out):
    w = out.append
    w("=" * 70)
    w(f"Код: {code.title()}")
    w(f"k = {code.k}, r = {code.r}, n = {code.n}, относительная избыточность r/k = {code.r / code.k:.3f}, "
      f"скорость k/n = {code.k / code.n:.3f}")
    w(f"X_k = {fmt(xk)}")
    for p in range(code.z):
        w(f"\nИнформационная матрица{' (плоскость %d)' % (p + 1) if code.z > 1 else ''} {code.k1}x{code.k2}:")
        for i in range(code.k1):
            base = p * code.k1 * code.k2 + i * code.k2
            w("  " + " ".join(map(str, xk[base:base + code.k2])))
    xn = code.encode(xk)
    w("\nИзбыточные символы по группам:")
    pos = code.k
    for g in code.groups:
        cnt = code.check_group.count(g)
        w(f"  {GROUP_NAME[g]:<18}({cnt:>2} бит): {fmt(xn[pos:pos + cnt])}")
        pos += cnt
    w(f"\nX_n = {fmt(xn)}")
 
    err = sorted(rng.sample(range(code.n), nerr))
    yn = xn[:]
    for q in err:
        yn[q] ^= 1
    s = code.syndrome(yn)
    w(f"\nОшибок: {nerr}, позиции (с 1): {[q + 1 for q in err]}")
    w(f"Y_n = {fmt(yn)}")
    w(f"Синдром (нарушены проверки №): {[c + 1 for c, v in enumerate(s) if v] or 'нет'}")
    yfix, flips, ok = code.decode(yn)
    changed = [q + 1 for q in range(code.n) if yfix[q] != yn[q]]
    w(f"Исправлены позиции: {changed or 'нет'}")
    w(f"Y_n' = {fmt(yfix)}")
    if yfix == xn:
        w("Итог: Y_n' = X_n, слово восстановлено верно." if nerr else "Итог: ошибок не было.")
    elif not ok:
        w("Итог: ошибка обнаружена, исправить однозначно нельзя.")
    else:
        w("Итог: слово исправлено неверно / ошибка не обнаружена.")
 
 
def experiment(code, n1, imax, rng):
    rows = []
    for i in range(1, imax + 1):
        n_det = n2 = n3 = 0
        for _ in range(n1):
            xk = [rng.randint(0, 1) for _ in range(code.k)]
            xn = code.encode(xk)
            yn = xn[:]
            for q in rng.sample(range(code.n), i):
                yn[q] ^= 1
            if any(code.syndrome(yn)):
                n_det += 1
            yfix, flips, ok = code.decode(yn)
            if ok and flips == i:
                n2 += 1                     
            if yfix == xn:
                n3 += 1                     
        rows.append((i, n1, n_det, n2, n3))
    return rows
 
 
def main():
    ap = argparse.ArgumentParser(description="Итеративные коды, вариант 4 (k = 32)")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--experiment", action="store_true")
    ap.add_argument("--word", help="информационное слово из 32 бит (по умолчанию случайное)")
    ap.add_argument("--errors", type=int, default=1, help="кратность ошибки в демонстрации")
    ap.add_argument("--n1", type=int, default=3000, help="число слов N1 на каждую кратность")
    ap.add_argument("--imax", type=int, default=6, help="максимальная кратность ошибки")
    ap.add_argument("--seed", type=int, default=4)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    if not (a.demo or a.experiment):
        a.demo = a.experiment = True
 
    if a.demo:
        out = []
        for dims, gs in VARIANT_4:
            for g in gs:
                xk = [int(c) for c in a.word] if a.word else [rng.randint(0, 1) for _ in range(K)]
                if len(xk) != K:
                    raise SystemExit("--word должно содержать ровно 32 бита")
                demo(IterCode(dims, g), xk, a.errors, rng, out)
        text = "\n".join(out)
        print(text)
        with open("iterative_demo.txt", "w", encoding="utf-8") as f:
            f.write(text + "\n")
 
    if a.experiment:
        lines = [f"Эксперимент: N1 = {a.n1} слов на каждую кратность i, seed = {a.seed}",
                 "N2/N1 - кратность ошибки определена верно, N3/N1 - все ошибки исправлены, Nобн/N1 - ошибка обнаружена", ""]
        csv_rows = []
        for dims, gs in VARIANT_4:
            for g in gs:
                code = IterCode(dims, g)
                d = code.dmin()
                lines.append(f"--- {code.title()} | k={code.k}, r={code.r}, n={code.n}, "
                             f"r/k={code.r / code.k:.3f}, k/n={code.k / code.n:.3f}, d_min={d if d else '>7'}")
                lines.append(f"{'i':>3} {'N1':>7} {'Nобн/N1':>9} {'N2/N1':>8} {'N3/N1':>8}")
                for i, n1, nd, n2, n3 in experiment(code, a.n1, a.imax, rng):
                    lines.append(f"{i:>3} {n1:>7} {nd / n1:>9.4f} {n2 / n1:>8.4f} {n3 / n1:>8.4f}")
                    csv_rows.append([code.title(), code.r, f"{code.r / code.k:.3f}", d, i, n1,
                                     f"{nd / n1:.4f}", f"{n2 / n1:.4f}", f"{n3 / n1:.4f}"])
                lines.append("")
        text = "\n".join(lines)
        print(text)
        with open("iterative_experiment.txt", "w", encoding="utf-8") as f:
            f.write(text + "\n")
        with open("iterative_experiment.csv", "w", encoding="utf-8", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["код", "r", "r/k", "d_min", "i", "N1", "Nобн/N1", "N2/N1", "N3/N1"])
            wr.writerows(csv_rows)
 
 
if __name__ == "__main__":
    main()
