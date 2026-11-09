# -*- coding: utf-8 -*-
"""
Лабораторная работа №2, вариант 15.
Часть 1: избыточное кодирование, код Хэмминга (d_min = 3 и d_min = 4).
Часть 2: линейные итеративные (многомерные) коды.

В табл. 5.2 методички всего 5 вариантов, поэтому номер варианта берётся
по кругу: ((15 - 1) mod 5) + 1 = 5  ->  k = 40 бит и формы записи слова:
    5 x 8      (группы паритетов 2; 3)
    4 x 10     (группы паритетов 2; 3)
    5 x 4 x 2  (группы паритетов 2; 3; 4; 5)
    2 x 10 x 2 (группы паритетов 2; 3; 4; 5)
"""
import math
import secrets
from fractions import Fraction
import time

import matplotlib.pyplot as plt

VARIANT = 15
TABLE_VARIANT = (VARIANT - 1) % 5 + 1          # = 5
K_ITER = 40                                    # длина информационного слова, бит
ITER_FORMS = [                                 # (k1, k2, z, допустимые числа групп)
    (5, 8, 1, (2, 3)),
    (4, 10, 1, (2, 3)),
    (5, 4, 2, (2, 3, 4, 5)),
    (2, 10, 2, (2, 3, 4, 5)),
]
DEFAULT_MESSAGE = "Вариант 15"
RNG = secrets.SystemRandom()


# ======================================================================
#                     ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ======================================================================
def text_to_bits(text):
    """Текст -> двоичная последовательность (кодировка cp1251, 8 бит на символ,
    подходит и для русского, и для английского алфавитов)."""
    data = text.encode("cp1251", errors="replace")
    return [int(b) for byte in data for b in f"{byte:08b}"]


def bits_to_text(bits):
    usable = len(bits) // 8 * 8
    data = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, usable, 8))
    return data.decode("cp1251", errors="replace")


def bstr(bits):
    return "".join(map(str, bits))


def random_positions(n, count):
    """count различных случайных позиций из [0, n)."""
    return sorted(RNG.sample(range(n), count))


def marks(n, positions, ch="^"):
    """Строка-указатель под позициями ошибок."""
    line = [" "] * n
    for p in positions:
        line[p] = ch
    return "".join(line)


def ask_int(prompt, default, lo=None, hi=None):
    s = input(f"{prompt} [{default}]: ").strip()
    if not s:
        return default
    v = int(s)
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ValueError(f"значение должно быть в диапазоне [{lo}, {hi}]")
    return v


# ======================================================================
#                     ЧАСТЬ 1. КОД ХЭММИНГА
# ======================================================================
def hamming_r(k):
    """Минимальное число проверочных бит r для d_min = 3:
    столбцов веса >= 2 должно хватить на k информационных бит,
    т.е. 2^r - r - 1 >= k (эквивалентно 2^r >= k + r + 1)."""
    r = 2
    while (1 << r) - r - 1 < k:
        r += 1
    return r


def binom(r, wt):
    """Бином Ньютона C(r, wt) — число столбцов веса wt (листинг 4.1)."""
    return math.factorial(r) // (math.factorial(wt) * math.factorial(r - wt))


def build_P(k, r):
    """Подматрица P' (r x k), листинг 4.2: двоичные записи натуральных чисел,
    начиная с 3, дополненные нулями до r позиций; сначала берутся все числа
    веса wt = 2 (их C(r, 2)), затем веса 3 и т.д., пока не наберётся k столбцов."""
    cols, wt = [], 2
    while len(cols) < k:
        count, num = 0, 3
        while num < (1 << r) and count < binom(r, wt) and len(cols) < k:
            if bin(num).count("1") == wt:
                cols.append([int(c) for c in format(num, f"0{r}b")])
                count += 1
            num += 1
        wt += 1
    return [[cols[j][i] for j in range(k)] for i in range(r)]


class Hamming:
    """Систематический код Хэмминга: H = [P' | I_r], X_n = X_k, X_r.
    d_min = 4: добавляется общая проверка на чётность (выражение 4.8):
    к H дописывается нулевой столбец и строка из одних единиц."""

    def __init__(self, k, dmin=3):
        if dmin not in (3, 4):
            raise ValueError("d_min должно быть 3 или 4")
        self.k, self.dmin = k, dmin
        self.rh = hamming_r(k)                       # проверочных бит в H
        self.P = build_P(k, self.rh)
        self.H = [self.P[i] + [1 if j == i else 0 for j in range(self.rh)]
                  for i in range(self.rh)]
        if dmin == 4:
            self.H = [row + [0] for row in self.H] + [[1] * (k + self.rh + 1)]
        self.r = len(self.H)
        self.n = k + self.r
        self.columns = [[self.H[i][j] for i in range(self.r)] for j in range(self.n)]

    def parity(self, xk):
        """X_r[i] = сумма по модулю 2 пар (1; 1) в X_k и i-й строке P'."""
        return [sum(p & x for p, x in zip(row, xk)) % 2 for row in self.P]

    def encode(self, xk):
        xr = self.parity(xk)
        if self.dmin == 4:
            xr.append((sum(xk) + sum(xr)) % 2)       # общий бит чётности
        return xk + xr, xr

    def decode(self, yn):
        """Возвращает Yr', S, E_n, исправленное слово, признак «обнаружена
        неисправимая ошибка» и текстовое заключение."""
        k = self.k
        yk, yr = yn[:k], yn[k:]
        yr2 = self.parity(yk)                        # Y_r' по выражению (4.6)
        if self.dmin == 4:
            # последняя строка H' — сплошные единицы: проверочный бит
            # пересчитывается по принятым Y_k и Y_r
            yr2.append((sum(yk) + sum(yr[:self.rh])) % 2)
        s = [a ^ b for a, b in zip(yr, yr2)]        # синдром, листинг 4.4
        e = [0] * self.n
        uncorrectable = False
        if not any(s):
            status = "синдром нулевой — ошибок не обнаружено"
        elif self.dmin == 4 and s[-1] == 0:
            uncorrectable = True
            status = "обнаружена ошибка чётной кратности (2) — исправление невозможно"
        elif s in self.columns:
            mist = self.columns.index(s)             # позиция ошибки
            e[mist] = 1                              # унарный вектор, листинг 4.5
            status = f"одиночная ошибка в позиции {mist + 1} — исправлена"
        else:
            uncorrectable = True
            status = "синдром не совпадает ни с одним столбцом H — исправление невозможно"
        corrected = [a ^ b for a, b in zip(yn, e)]  # выражение (4.7)
        return yr2, s, e, corrected, uncorrectable, status

    def syndrome_by_matrix(self, yn):
        return [sum(h & y for h, y in zip(row, yn)) % 2 for row in self.H]


def print_matrix(H, k, extended=False, indent="    "):
    n = len(H[0])
    sep = " " if n <= 48 else ""
    for i, row in enumerate(H):
        if extended and i == len(H) - 1:
            print(indent + "-" * len(sep.join("0" * n) + " | "))
        left = sep.join(map(str, row[:k]))
        if extended:
            mid, last = sep.join(map(str, row[k:-1])), str(row[-1])
            print(f"{indent}{left} | {mid} | {last}")
        else:
            print(f"{indent}{left} | {sep.join(map(str, row[k:]))}")


def read_message():
    print("Источник сообщения: Enter — по умолчанию, 1 — ввести с клавиатуры, "
          "2 — прочитать из текстового файла")
    ch = input("Выбор: ").strip()
    if ch == "1":
        text = input("Сообщение: ")
    elif ch == "2":
        path = input("Путь к файлу: ").strip()
        with open(path, encoding="utf-8") as f:
            text = f.read().rstrip("\n")
    else:
        text = DEFAULT_MESSAGE
    if len(text_to_bits(text)) < 16:
        raise ValueError("длина сообщения в двоичном виде должна быть не менее 16 бит")
    return text


def stage1(text=DEFAULT_MESSAGE, dmin=4):
    print("=" * 78)
    print(f"ЧАСТЬ 1. Код Хэмминга, d_min = {dmin}")
    print("=" * 78)
    xk = text_to_bits(text)
    code = Hamming(len(xk), dmin)
    k, r, n = code.k, code.r, code.n
    print(f"Сообщение: «{text}» ({len(text)} симв., cp1251)")
    print(f"k = {k}, r = {r}, n = k + r = {n}, избыточность r/n = {r / n:.3f}")
    print(f"Проверочная матрица H{'′' if dmin == 4 else ''}({n},{k}) = [P' | I]"
          f"{' + общая проверка на чётность (4.8)' if dmin == 4 else ''}:")
    print_matrix(code.H, k, extended=(dmin == 4))
    xn, xr = code.encode(xk)
    print(f"\nX_k = {bstr(xk)}")
    print(f"X_r = {bstr(xr)}")
    print(f"X_n = {bstr(xn)}")

    for errors in (0, 1, 2):
        print("\n" + "-" * 78)
        pos = random_positions(n, errors)
        yn = xn[:]
        for p in pos:
            yn[p] ^= 1
        yr2, s, e, corrected, _, status = code.decode(yn)
        print(f"Число ошибок: {errors}; позиции (с 1): {[p + 1 for p in pos] or '—'}")
        print(f"X_n  = {bstr(xn)}")
        print(f"Y_n  = {bstr(yn)}")
        print(f"       {marks(n, pos)}")
        print(f"Y_k  = {bstr(yn[:k])}")
        print(f"Y_r  = {bstr(yn[k:])}")
        print(f"Y_r' = {bstr(yr2)}")
        print(f"S    = {bstr(s)}   (H·Y_n^T = {bstr(code.syndrome_by_matrix(yn))})")
        print(f"E_n  = {bstr(e)}")
        print(f"Y_n ⊕ E_n = {bstr(corrected)}")
        print(f"Итог: {status}")
        ok = corrected == xn
        print(f"Совпадает с X_n: {'да' if ok else 'НЕТ'}; "
              f"восстановленный текст: «{bits_to_text(corrected[:k])}»")
        if errors == 2 and dmin == 3 and not ok:
            print("  (при d_min = 3 двукратная ошибка даёт синдром, равный сумме двух"
                  " столбцов H, и приводит к ложному «исправлению»)")


def hamming_statistics(text=DEFAULT_MESSAGE, trials=2000):
    print("=" * 78)
    print("ЧАСТЬ 1. Анализ кода Хэмминга")
    print("=" * 78)
    xk = text_to_bits(text)
    print(f"Сообщение «{text}», k = {len(xk)}, {trials} испытаний на каждую строку")
    hdr = f"{'d_min':>5}{'ошибок':>8}{'верно':>9}{'обнаруж.':>10}{'ложно':>9}"
    print(hdr + "\n" + "-" * len(hdr))
    for dmin in (3, 4):
        code = Hamming(len(xk), dmin)
        xn, _ = code.encode(xk)
        for errors in (0, 1, 2, 3):
            good = det = bad = 0
            for _ in range(trials):
                yn = xn[:]
                for p in random_positions(code.n, errors):
                    yn[p] ^= 1
                *_, corrected, unc, _ = code.decode(yn)
                if corrected == xn:
                    good += 1
                elif unc:
                    det += 1
                else:
                    bad += 1
            print(f"{dmin:>5}{errors:>8}{good / trials:>9.1%}{det / trials:>10.1%}"
                  f"{bad / trials:>9.1%}")
    print("верно — слово восстановлено; обнаруж. — ошибка обнаружена, но не исправлена;\n"
          "ложно — ошибка пропущена или «исправлена» неверно")

    print("\nЗависимость r от k (контрольные вопросы 2–3):")
    print(f"{'k':>5}{'r (d=3)':>9}{'n':>6}{'r/n':>7}{'n/k':>7}{'r (d=4)':>9}{'n':>6}{'r/n':>7}")
    for k in (4, 6, 8, 9, 10, 15, 16, 32, 64, 128, 256, 1024):
        r3 = hamming_r(k)
        r4 = r3 + 1
        print(f"{k:>5}{r3:>9}{k + r3:>6}{r3 / (k + r3):>7.3f}{(k + r3) / k:>7.3f}"
              f"{r4:>9}{k + r4:>6}{r4 / (k + r4):>7.3f}")
    print("Время передачи пропорционально n = k + r, т.е. растёт в n/k раз.")
    print("\nПроверочная матрица для k = 4, d_min = 3:")
    print_matrix(Hamming(4, 3).H, 4)
    print("Проверочная матрица для k = 4, d_min = 4:")
    print_matrix(Hamming(4, 4).H, 4, extended=True)

    ks = list(range(1, 1025))
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    axes[0].step(ks, [hamming_r(k) for k in ks], where="post", label="d_min = 3")
    axes[0].step(ks, [hamming_r(k) + 1 for k in ks], where="post", label="d_min = 4")
    axes[0].set_xscale("log", base=2)
    axes[0].set_title("Число проверочных бит r(k)")
    axes[0].set_xlabel("k")
    axes[0].legend()
    axes[0].grid(True)
    axes[1].plot(ks, [hamming_r(k) / (k + hamming_r(k)) for k in ks], label="d_min = 3")
    axes[1].plot(ks, [(hamming_r(k) + 1) / (k + hamming_r(k) + 1) for k in ks],
                 label="d_min = 4")
    axes[1].set_xscale("log", base=2)
    axes[1].set_title("Относительная избыточность r / n")
    axes[1].set_xlabel("k")
    axes[1].legend()
    axes[1].grid(True)
    fig.tight_layout()
    fig.savefig("part1_hamming_r.png", dpi=110)
    plt.show()


# ======================================================================
#                     ЧАСТЬ 2. ИТЕРАТИВНЫЕ КОДЫ
# ======================================================================
GROUP_NAMES = {
    "h": "горизонтальные (по строкам), X_h",
    "v": "вертикальные (по столбцам), X_v",
    "d": "диагональные ↗ (i + j = const), X_d",
    "a": "диагональные ↘ (i − j = const), X_a",
    "z": "по оси Z (между плоскостями), X_z",
}
GROUP_ORDER = "hvdaz"          # 2 группы = h, v; 3 = + d; 4 = + a; 5 = + z


class IterativeCode:
    """Линейный итеративный код: X_k записывается в z плоскостей k1 x k2
    (бит с номером p*k1*k2 + i*k2 + j -> плоскость p, строка i, столбец j).
    Проверочные биты: сначала для каждой плоскости по группам h, v, d, a,
    затем z-паритеты, в конце (по желанию) X_hv — паритет паритетов,
    равный сумме по модулю 2 всех остальных символов X_n.
    Диагонали по умолчанию нециклические (рис. 5.3: k1 + k2 - 1 штук),
    cyclic=True — циклические, как на рис. 5.4."""

    def __init__(self, k1, k2, z=1, groups="hv", xhv=False, cyclic=False):
        self.k1, self.k2, self.z = k1, k2, z
        self.k = k1 * k2 * z
        self.groups, self.xhv, self.cyclic = groups, xhv, cyclic
        pos = lambda p, i, j: p * k1 * k2 + i * k2 + j
        nd = k2 if cyclic else k1 + k2 - 1
        checks = []                                  # (группа, подпись, биты X_k)
        for p in range(z):
            for g in groups:
                if g == "h":
                    for i in range(k1):
                        checks.append((g, f"пл.{p + 1} строка {i + 1}",
                                       [pos(p, i, j) for j in range(k2)]))
                elif g == "v":
                    for j in range(k2):
                        checks.append((g, f"пл.{p + 1} столбец {j + 1}",
                                       [pos(p, i, j) for i in range(k1)]))
                elif g in "da":
                    for s in range(nd):
                        mem = []
                        for i in range(k1):
                            for j in range(k2):
                                t = i + j if g == "d" else i - j + k2 - 1
                                if (t % k2 if cyclic else t) == s:
                                    mem.append(pos(p, i, j))
                        checks.append((g, f"пл.{p + 1} диаг.{g} {s + 1}", mem))
        if "z" in groups and z > 1:
            for i in range(k1):
                for j in range(k2):
                    checks.append(("z", f"Z ({i + 1},{j + 1})",
                                   [pos(p, i, j) for p in range(z)]))
        self.checks = checks
        self.r = len(checks) + (1 if xhv else 0)
        self.n = self.k + self.r
        self.data_masks = [sum(1 << b for b in mem) for _, _, mem in checks]
        # полные проверки (вместе с проверочным битом) для декодирования
        self.members = [mem + [self.k + c] for c, (_, _, mem) in enumerate(checks)]
        self.labels = [lbl for _, lbl, _ in checks]
        if xhv:
            self.members.append(list(range(self.n)))
            self.labels.append("X_hv")
        self.masks = [sum(1 << b for b in m) for m in self.members]
        self.deg = [0] * self.n                      # число проверок на символ
        for m in self.members:
            for b in m:
                self.deg[b] += 1
        # число «локализующих» проверок (без X_hv) — для мажоритарного голосования
        self.vdeg = [d - (1 if xhv else 0) for d in self.deg]

    def name(self):
        shape = f"{self.k1}x{self.k2}" + (f"x{self.z}" if self.z > 1 else "")
        return f"{shape}, групп {len(self.groups)}, X_hv {'да' if self.xhv else 'нет'}"

    # --- кодирование / декодирование (слова — целые числа, бит p = позиция p)
    def encode(self, xk):
        xn = xk
        for c, m in enumerate(self.data_masks):
            if (xk & m).bit_count() & 1:
                xn |= 1 << (self.k + c)
        if self.xhv and xn.bit_count() & 1:
            xn |= 1 << (self.n - 1)
        return xn

    def syndrome(self, y):
        """Номера нарушенных проверок (Y_r ≠ Y_r')."""
        return [c for c, m in enumerate(self.masks) if (y & m).bit_count() & 1]

    def decode(self, y, max_iter=None):
        """Итеративное декодирование: на каждой итерации для каждого символа
        считается доля нарушенных проверок среди всех проверок, в которые он
        входит; инвертируются символы, у которых нарушено больше половины их
        проверок, а доля (при равенстве — число) нарушенных проверок максимальна. Повторяем, пока синдром не станет
        нулевым. Если процесс зациклился или застрял — ошибка обнаружена,
        но не исправлена (возвращается принятое слово без изменений)."""
        max_iter = max_iter or self.n
        cur, seen = y, set()
        hv = len(self.members) - 1 if self.xhv else None   # номер проверки X_hv
        for it in range(max_iter):
            failed = self.syndrome(cur)
            if not failed:
                return cur, True, it
            if failed == [hv]:                   # нарушена только общая чётность
                return cur ^ (1 << (self.n - 1)), True, it + 1   # ошибка в X_hv
            if cur in seen:
                break
            seen.add(cur)
            # X_hv охватывает все символы сразу и ничего не локализует, поэтому
            # в голосовании не участвует (используется только для обнаружения)
            cnt = {}
            for c in failed:
                if c == hv:
                    continue
                for b in self.members[c]:
                    cnt[b] = cnt.get(b, 0) + 1
            # кандидаты — символы, у которых нарушено больше половины проверок.
            # Ранг кандидата: сначала ДОЛЯ нарушенных проверок, затем их число.
            # Сравнение только по числу (как было раньше) давало сбой при
            # 2 группах + X_hv: ошибка в проверочном бите (2 из 2 проверок)
            # «тянула» за собой все биты строки (2 из 3 проверок).
            score = {b: (Fraction(v, self.vdeg[b]), v) for b, v in cnt.items()
                     if 2 * v > self.vdeg[b]}
            if not score:
                break
            best = max(score.values())
            for b, sc in score.items():
                if sc == best:
                    cur ^= 1 << b
        return y, False, max_iter

    def matrix_H(self):
        """Проверочная матрица: строка = проверка, столбец = символ X_n."""
        return [[(m >> j) & 1 for j in range(self.n)] for m in self.masks]

    # --- отображение
    def to_bits(self, w, length=None):
        return [(w >> i) & 1 for i in range(length or self.n)]

    def show(self, w, title):
        """Вывод слова в виде матриц (как на рис. 5.1, 5.3, 5.4)."""
        b = self.to_bits(w)
        k1, k2 = self.k1, self.k2
        idx = {}
        for c, (g, _, _) in enumerate(self.checks):
            idx.setdefault(g, []).append(self.k + c)
        print(title)
        per_plane = {g: len(v) // (self.z if g != "z" else 1) for g, v in idx.items()}
        for p in range(self.z):
            print(f"  Плоскость {p + 1}:" if self.z > 1 else "")
            hp = idx.get("h", [])[p * k1:(p + 1) * k1] if "h" in idx else []
            for i in range(k1):
                row = " ".join(str(b[p * k1 * k2 + i * k2 + j]) for j in range(k2))
                print(f"    {row}" + (f" | {b[hp[i]]}" if hp else ""))
            if "v" in idx:
                vp = idx["v"][p * k2:(p + 1) * k2]
                print("    " + "-" * (2 * k2 - 1))
                print("    " + " ".join(str(b[q]) for q in vp) + "   X_v")
            for g in "da":
                if g in idx:
                    m = per_plane[g]
                    gp = idx[g][p * m:(p + 1) * m]
                    print(f"    X_{g}: " + " ".join(str(b[q]) for q in gp))
        if "z" in idx:
            print("  X_z (по позициям плоскости):")
            zp = idx["z"]
            for i in range(k1):
                print("    " + " ".join(str(b[zp[i * k2 + j]]) for j in range(k2)))
        if self.xhv:
            print(f"  X_hv = {b[self.n - 1]}")


def make_code(form_index, ngroups, xhv):
    k1, k2, z, allowed = ITER_FORMS[form_index]
    if ngroups not in allowed:
        raise ValueError(f"для формы {k1}x{k2}x{z} допустимо групп: {allowed}")
    return IterativeCode(k1, k2, z, GROUP_ORDER[:ngroups], xhv)


def stage2_demo(form_index=0, ngroups=3, xhv=True, errors=1, xk=None):
    code = make_code(form_index, ngroups, xhv)
    print("=" * 78)
    print(f"ЧАСТЬ 2. Итеративный код: {code.name()}")
    print("=" * 78)
    print("Группы паритетов:")
    for g in code.groups:
        if g != "z" or code.z > 1:
            print(f"  {g}: {GROUP_NAMES[g]}")
    if xk is None:
        xk = secrets.randbits(code.k)
    k, r, n = code.k, code.r, code.n
    print(f"k = {k}, r = {r}, n = {n}, избыточность r/n = {r / n:.3f}, "
          f"скорость k/n = {k / n:.3f}")
    xn = code.encode(xk)
    xb = code.to_bits(xn)
    print(f"X_k = {bstr(xb[:k])}")
    print(f"X_r = {bstr(xb[k:])}")
    print(f"X_n = {bstr(xb)}")
    code.show(xn, "\nЗапись X_n в матрицу:")

    pos = random_positions(n, errors)
    yn = xn
    for p in pos:
        yn ^= 1 << p
    yb = code.to_bits(yn)
    print(f"\nОшибка кратности i = {errors}, позиции (с 1): {[p + 1 for p in pos]}")
    print(f"Y_n  = {bstr(yb)}")
    print(f"       {marks(n, pos)}")
    failed = code.syndrome(yn)
    print(f"Нарушенные проверки ({len(failed)}): "
          + (", ".join(code.labels[c] for c in failed) if failed else "нет"))

    y2, ok, it = code.decode(yn)
    found = [p for p in range(n) if ((y2 ^ yn) >> p) & 1]
    print(f"Y_n' = {bstr(code.to_bits(y2))}")
    if not failed:
        print("Итог: синдром нулевой — ошибка НЕ обнаружена")
    elif ok:
        print(f"Итог: за {it} итерац. найдены ошибки в позициях {[p + 1 for p in found]} "
              f"(кратность {len(found)}) и исправлены")
    else:
        print("Итог: ошибка обнаружена, но исправить её не удалось")
    print(f"X_n и Y_n' совпадают: {'да' if y2 == xn else 'НЕТ'}")


def simulate(code, errors, trials):
    """N1 испытаний: доля обнаруженных, N2/N1 — кратность определена верно,
    N3/N1 — все ошибки исправлены (X_n = Y_n')."""
    det = n2 = n3 = 0
    for _ in range(trials):
        xn = code.encode(secrets.randbits(code.k))
        yn = xn
        for p in RNG.sample(range(code.n), errors):
            yn ^= 1 << p
        if code.syndrome(yn):
            det += 1
        y2, ok, _ = code.decode(yn)
        if ok and (y2 ^ yn).bit_count() == errors:
            n2 += 1
        if y2 == xn:
            n3 += 1
    return det / trials, n2 / trials, n3 / trials


def stage2_statistics(trials=1000, max_errors=6):
    print("=" * 78)
    print(f"ЧАСТЬ 2. Корректирующая способность итеративных кодов, k = {K_ITER} "
          f"(вариант {VARIANT} -> строка {TABLE_VARIANT} табл. 5.2)")
    print("=" * 78)
    print(f"N1 = {trials} случайных слов на каждую кратность ошибки i")
    t0 = time.perf_counter()
    rows = []
    for f, (k1, k2, z, allowed) in enumerate(ITER_FORMS):
        for g in allowed:
            for xhv in (False, True):
                code = make_code(f, g, xhv)
                res = [simulate(code, i, trials) for i in range(1, max_errors + 1)]
                rows.append((f, g, xhv, code, res))
    ii = range(1, max_errors + 1)
    for title, col in (("Доля обнаруженных ошибок (синдром ≠ 0)", 0),
                       ("N2/N1 — кратность ошибки определена верно", 1),
                       ("N3/N1 — все ошибки исправлены (X_n = Y_n')", 2)):
        print(f"\n{title}")
        hdr = (f"{'форма':>8}{'гр.':>4}{'X_hv':>5}{'r':>5}{'n':>5}{'k/n':>6} |"
               + "".join(f"{'i=' + str(i):>7}" for i in ii))
        print(hdr + "\n" + "-" * len(hdr))
        for f, g, xhv, code, res in rows:
            k1, k2, z, _ = ITER_FORMS[f]
            shape = f"{k1}x{k2}" + (f"x{z}" if z > 1 else "")
            print(f"{shape:>8}{g:>4}{'да' if xhv else 'нет':>5}{code.r:>5}{code.n:>5}"
                  f"{code.k / code.n:>6.2f} |" + "".join(f"{x[col]:>7.1%}" for x in res))
    print(f"\nВремя моделирования: {time.perf_counter() - t0:.1f} с")

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    for f, ax in enumerate(axes.flat):
        k1, k2, z, _ = ITER_FORMS[f]
        for ff, g, xhv, code, res in rows:
            if ff != f:
                continue
            ax.plot(list(ii), [x[2] for x in res], marker="o",
                    ls="-" if xhv else "--",
                    label=f"групп {g}, X_hv {'да' if xhv else 'нет'} (r={code.r})")
        ax.set_title(f"{k1}x{k2}" + (f"x{z}" if z > 1 else "") + ": N3/N1")
        ax.set_xlabel("кратность ошибки i")
        ax.set_ylim(-0.03, 1.03)
        ax.grid(True)
        ax.legend(fontsize=8)
    fig.suptitle(f"Доля исправленных слов, k = {K_ITER}")
    fig.tight_layout()
    fig.savefig("part2_correction.png", dpi=110)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    names = [f"{ITER_FORMS[f][0]}x{ITER_FORMS[f][1]}"
             + (f"x{ITER_FORMS[f][2]}" if ITER_FORMS[f][2] > 1 else "")
             + f"\n{g} гр.{'+hv' if xhv else ''}" for f, g, xhv, _, _ in rows]
    ax.bar(range(len(rows)), [c.r / c.n for *_, c, _ in rows], color="steelblue")
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(names, fontsize=7)
    ax.set_title("Относительная избыточность r / n")
    fig.tight_layout()
    fig.savefig("part2_redundancy.png", dpi=110)
    plt.show()


# ======================================================================
#                     САМОПРОВЕРКА ПО ПРИМЕРАМ МЕТОДИЧКИ
# ======================================================================
def self_test():
    print("=" * 78)
    print("САМОПРОВЕРКА")
    print("=" * 78)
    # код Хэмминга: все одиночные ошибки исправляются, двойные при d=4 обнаруживаются
    for dmin in (3, 4):
        for k in (4, 11, 16, 57, 80):
            code = Hamming(k, dmin)
            xk = [secrets.randbelow(2) for _ in range(k)]
            xn, _ = code.encode(xk)
            assert code.syndrome_by_matrix(xn) == [0] * code.r
            for p in range(code.n):
                yn = xn[:]
                yn[p] ^= 1
                yr2, s, *_ = code.decode(yn)
                assert s == code.syndrome_by_matrix(yn)
                assert code.decode(yn)[3] == xn
            if dmin == 4:
                for p in range(code.n):
                    for q in range(p + 1, code.n):
                        yn = xn[:]
                        yn[p] ^= 1
                        yn[q] ^= 1
                        assert code.decode(yn)[4]
    print("Хэмминг: все одиночные ошибки исправлены, при d_min = 4 все двойные обнаружены")
    print("Первые столбцы P' при r = 5:",
          [bstr(c) for c in zip(*build_P(5, 5))][:3], "(00011, 00101, 00110 — как в п. 4.2)")

    # рис. 5.1: X_k = 011101111 -> X_h, X_v, X_hv = 0010011
    code = IterativeCode(3, 3, 1, "hv", xhv=True)
    xk = int("011101111"[::-1], 2)
    xb = bstr(code.to_bits(code.encode(xk)))
    print(f"Рис. 5.1: X_n = {xb[:9]} {xb[9:]} (в методичке 011101111 0010011)")
    assert xb == "0111011110010011"
    H = IterativeCode(3, 3, 1, "hv").matrix_H()
    print("H(15,9) для рис. 5.1 (совпадает с методичкой):")
    print_matrix(H, 9)

    # рис. 5.4 / табл. 5.1: 4 плоскости 4x4, 5 групп, циклические диагонали -> r = 80
    code = IterativeCode(4, 4, 4, "hvdaz", cyclic=True)
    assert code.r == 80
    book = {1: (1, 2, 3, 4), 2: (5, 6, 7, 8), 5: (1, 5, 9, 13), 14: (3, 8, 9, 14),
            16: (1, 6, 11, 16), 17: (17, 18, 19, 20), 37: (33, 37, 41, 45),
            60: (52, 55, 58, 61), 80: (16, 32, 48, 64)}
    for rr, xs in book.items():
        got = tuple(b + 1 for b in code.checks[rr - 1][2])
        assert got == xs, (rr, got, xs)
    print("Рис. 5.4: k = 64, r = 80, формулы x_r1, x_r5, x_r14, x_r16, x_r37, x_r60, "
          "x_r80 совпадают с методичкой")
    for k1, k2, z, allowed in ITER_FORMS:
        for g in allowed:
            for xhv in (False, True):
                c = IterativeCode(k1, k2, z, GROUP_ORDER[:g], xhv)
                xn = c.encode(secrets.randbits(c.k))
                assert not c.syndrome(xn)
                for p in range(c.n):
                    assert c.decode(xn ^ (1 << p))[0] == xn
    print("Итеративные коды варианта: все одиночные ошибки исправляются")
    print("Самопроверка пройдена")


# ======================================================================
def main():
    while True:
        print(f"\nМЕНЮ (лабораторная работа №2, вариант {VARIANT})\n"
              " 1 — Часть 1: код Хэмминга (0, 1, 2 ошибки)\n"
              " 2 — Часть 1: анализ кода Хэмминга (статистика, r(k), графики)\n"
              " 3 — Часть 2: итеративный код для одного слова\n"
              " 4 — Часть 2: оценка корректирующей способности (N2/N1, N3/N1)\n"
              " 5 — Самопроверка по примерам методички\n"
              " 0 — Выполнить всё и выйти")
        ch = input("Выбор: ").strip()
        try:
            if ch == "1":
                text = read_message()
                stage1(text, ask_int("d_min (3 или 4)", 4, 3, 4))
            elif ch == "2":
                hamming_statistics(read_message())
            elif ch == "3":
                for i, (k1, k2, z, allowed) in enumerate(ITER_FORMS, 1):
                    print(f"  {i} — {k1}x{k2}" + (f"x{z}" if z > 1 else "")
                          + f", групп паритетов: {allowed}")
                f = ask_int("Форма", 1, 1, len(ITER_FORMS)) - 1
                allowed = ITER_FORMS[f][3]
                g = ask_int(f"Число групп паритетов {allowed}", allowed[-1])
                xhv = input("Учитывать X_hv (д/н) [д]: ").strip().lower() not in ("н", "n")
                i = ask_int("Кратность ошибки i", 1, 1)
                s = input(f"X_k ({K_ITER} бит, Enter — случайное): ").strip()
                xk = None
                if s:
                    if len(s) != K_ITER or set(s) - {"0", "1"}:
                        raise ValueError(f"нужно ровно {K_ITER} символов 0/1")
                    xk = int(s[::-1], 2)
                stage2_demo(f, g, xhv, i, xk)
            elif ch == "4":
                stage2_statistics(ask_int("N1 (испытаний на кратность)", 1000, 10),
                                  ask_int("Максимальная кратность ошибки", 6, 1, 20))
            elif ch == "5":
                self_test()
            elif ch == "0":
                self_test()
                stage1(DEFAULT_MESSAGE, 3)
                stage1(DEFAULT_MESSAGE, 4)
                hamming_statistics()
                for f, (_, _, _, allowed) in enumerate(ITER_FORMS):
                    stage2_demo(f, allowed[-1], True, 2)
                stage2_statistics()
                break
        except (ValueError, OSError) as e:
            print("Ошибка:", e)


if __name__ == "__main__":
    main()