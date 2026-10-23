import random
import sys
from itertools import product

s = lambda v: ''.join(map(str, v))


# ============================================================ p1
def text_to_bits(text):
    return [int(b) for byte in text.encode('utf-8') for b in format(byte, '08b')]

def hamming_h(k):
    r = 1
    while 2 ** r < k + r + 1:
        r += 1

    n = k + r

    H = [[(j >> i) & 1 for j in range(1, n + 1)] for i in range(r)]

    return r, n, H

def parity(H, word):
    return [sum(h & w for h, w in zip(row, word)) % 2 for row in H]

def part1(path):
    bits = text_to_bits(open(path, encoding='utf-8').read().strip('\n'))

    k = len(bits)
    if k < 16:
        sys.exit('Сообщение в бинарном виде должно быть не менее 16 бит')

    r, n, H = hamming_h(k)
    par_pos = [2 ** i - 1 for i in range(r)]

    xn = [0] * n
    it = iter(bits)
    for j in range(n):
        if j not in par_pos:
            xn[j] = next(it)

    xr = parity(H, xn)
    for i, p in enumerate(par_pos):
        xn[p] = xr[i]

    print(f'Сообщение Xk: {s(bits)}')
    print(f'k={k} r={r} n={n}')
    print('Матрица H:')
    for row in H:
        print(' ', s(row))
    print(f'Xn: {s(xn)}\nXr: {s(xr)}')

    for t in (0, 1, 2):
        en = [0] * n
        for p in random.sample(range(n), t):
            en[p] = 1
        yn = [a ^ b for a, b in zip(xn, en)]
        yr = [yn[p] for p in par_pos]
        tmp = yn[:]
        for p in par_pos:
            tmp[p] = 0
        yr2 = parity(H, tmp)
        syn = [a ^ b for a, b in zip(yr, yr2)]
        pos = sum(b << i for i, b in enumerate(syn))
        fixed = yn[:]
        if pos:
            if pos <= n:
                fixed[pos - 1] ^= 1
            ev = [0] * n
            if pos <= n:
                ev[pos - 1] = 1
        else:
            ev = [0] * n
        print(f'\n--------- ошибок: {t}')
        print(f'Yn: {s(yn)}\nYr: {s(yr)}\nYr\': {s(yr2)}')
        print(f'Синдром S: {s(syn)} (pos {pos})')
        print(f'Вектор ошибки En: {s(ev)}')
        print(f'Исправлено: {s(fixed)}; совпало с Xn: {fixed == xn}')


# ============================================================ p2
DIRS2 = [(0, 1), (1, 0), (1, 1), (1, -1)]
DIRS3 = [(0, 1, 0), (1, 0, 0), (0, 0, 1), (1, 1, 1), (1, -1, 1)]


def build_lines(dims, dirs):
    cells = list(product(*[range(d) for d in dims]))
    idx = {c: i for i, c in enumerate(cells)}
    lines = []
    for d in dirs:
        for c in cells:
            prev = tuple(a - b for a, b in zip(c, d))
            if prev in idx:
                continue
            line, cur = [], c
            while cur in idx:
                line.append(idx[cur])
                cur = tuple(a + b for a, b in zip(cur, d))
            lines.append(line)
    return lines


def encode(info, lines):
    return info + [sum(info[i] for i in l) % 2 for l in lines]


def decode(y, k, lines, cl):
    y = y[:]
    det = False
    for _ in range(len(y)):
        bad = {j for j, l in enumerate(lines) if (y[k + j] + sum(y[i] for i in l)) % 2}
        if not bad:
            break
        det = True
        if len(bad) == 1:
            y[k + next(iter(bad))] ^= 1
            continue
        cand = [i for i in range(k) if cl[i] <= bad]
        if len(cand) != 1:
            break
        y[cand[0]] ^= 1

    return y, det


def part2(k=20, trials=10000, max_err=6):
    variants = [((4, 5), (2, 3)), ((2, 10), (2, 3)), ((2, 5, 2), (2, 3, 4, 5)), ((2, 2, 5), (2, 3, 4, 5))]
    for dims, groups in variants:
        for g in groups:
            dirs = (DIRS2 if len(dims) == 2 else DIRS3)[:g]
            lines = build_lines(dims, dirs)
            cl = [{j for j, l in enumerate(lines) if i in l} for i in range(k)]
            xk = [random.randint(0, 1) for _ in range(k)]
            xn = encode(xk, lines)
            n = len(xn)
            print(f'\nМатрица {"x".join(map(str, dims))}, групп паритетов: {g}, n={n}')

            for i in range(1, min(max_err, n) + 1):
                det = cor = 0
                for _ in range(trials):
                    y = xn[:]
                    for p in random.sample(range(n), i):
                        y[p] ^= 1

                    fixed, d = decode(y, k, lines, cl)
                    det += d
                    cor += fixed == xn
                print(f'  ошибок {i}: всего {trials}, обнаружено {det} ({det / trials:.3f}), исправлено {cor} ({cor / trials:.3f})')


if __name__ == '__main__':
    print('============================================================ p1')
    part1(sys.argv[1] if len(sys.argv) > 1 else 'input.txt')

    print('\n============================================================ p2')
    part2()