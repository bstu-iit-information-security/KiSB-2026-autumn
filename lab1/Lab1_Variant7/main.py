import argparse
import csv
import json
from math import gcd, isqrt
from pathlib import Path
from random import Random
from time import perf_counter

POLYNOMIALS = [("x^6+x^3+1", (0, 3)),
               ("x^6+x^2+x+1", (0, 1, 2)),
               ("x^6+x+1", (0, 1))]
ROOT = Path(__file__).resolve().parent


class LFSR:
    def __init__(self, taps=(0, 1), state=1):
        if not 0 <= state < 64:
            raise ValueError("Начальное состояние должно быть от 0 до 63")
        self.taps, self.state = taps, state

    def next_bit(self):
        bit = self.state & 1
        feedback = 0
        for j in self.taps:
            feedback ^= (self.state >> j) & 1
        self.state = (self.state >> 1) | (feedback << 5)
        return bit

    def generate(self, length):
        return [self.next_bit() for _ in range(length)]


def period(taps, seed):
    generator = LFSR(taps, seed)
    seen = {}
    while generator.state not in seen:
        seen[generator.state] = len(seen)
        generator.next_bit()
    return len(seen) - seen[generator.state]


def statistics(length, folder):
    rows = []
    for name, taps in POLYNOMIALS:
        periods = [period(taps, seed) for seed in range(1, 64)]
        for seed in (1, 21, 63, 0):
            bits = LFSR(taps, seed).generate(length)
            ones = sum(bits)
            zeros = length - ones
            mean = ones / length
            chi2 = (zeros - length / 2)**2 / (length / 2)
            chi2 += (ones - length / 2)**2 / (length / 2)
            rows.append(dict(polynomial=name, seed=seed, period=period(taps, seed),
                             max_period=max(periods), primitive=all(t == 63 for t in periods),
                             zeros=zeros, ones=ones, mean=mean,
                             variance=mean * (1 - mean), chi2=chi2,
                             uniform=chi2 <= 3.841459))
    with (folder / 'statistics.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def trial_prime(n):
    if n < 2:
        return False
    return all(n % d for d in range(2, isqrt(n) + 1))


SMALL = [n for n in range(2, 257) if trial_prime(n)]


def miller_rabin(n, rng, rounds=5):
    if n < 4:
        return n in (2, 3)
    if n % 2 == 0:
        return False
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        a = rng.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def sufficient_test(n, F, a):
    # F уже доказан простым; F | n-1. Порядок a mod r кратен F
    # для каждого простого делителя r числа n, следовательно r = kF+1.
    if n < 3 or F < 2 or (n - 1) % F:
        return False
    if pow(a, n - 1, n) != 1:
        return False
    if gcd(pow(a, (n - 1) // F, n) - 1, n) != 1:
        return False
    # Точная проверка оставшихся возможных делителей до sqrt(n).
    return all(n % (k * F + 1) for k in range(1, (isqrt(n) - 1) // F + 1))


def verify_certificate(cert):
    n = cert['n']
    if cert['kind'] == 'trial':
        return n.bit_length() < 16 and trial_prime(n)
    child = cert['child']
    F = child['n']
    return (verify_certificate(child) and F**3 > n
            and sufficient_test(n, F, cert['a']))


def mihailescu(m, rng, log, depth=0):
    start = perf_counter()
    counts = dict(candidates=0, sieve=0, mr=0, proof=0, trial=0, restarts=0)
    def finish(n, cert):
        log.append(dict(bits=m, depth=depth, n=n, **counts,
                        seconds=perf_counter() - start))
        return n, cert
    # B=16: малые простые проверяются полным перебором делителей.
    if m < 16:
        while True:
            n = rng.getrandbits(m) | (1 << (m - 1)) | 1
            counts['candidates'] += 1
            if trial_prime(n):
                return finish(n, dict(kind='trial', n=n))
            counts['trial'] += 1
 
    while True:
        F, child = mihailescu((m + 2) // 3 + 1, rng, log, depth + 1)
        if not (2**m < F**3 < 2**(2 * m)):
            continue
        s = 1
        low = 2**(m - 2) // F + 1
        high = (2**(m - 1) - 1) // F - s * m
        if low > high:
            counts['restarts'] += 1
            continue
        t = rng.randint(low, high)
        for i in range(s + 1):
            n = 2 * F * (t + i) + 1  
            assert n.bit_length() == m
            counts['candidates'] += 1
            if any(n != p and n % p == 0 for p in SMALL):
                counts['sieve'] += 1
                continue
            if not miller_rabin(n, rng):
                counts['mr'] += 1
                continue
            for a in range(2, 66):
                if sufficient_test(n, F, a):
                    return finish(n, dict(kind='recursive', n=n, a=a, child=child))
            counts['proof'] += 1
        counts['restarts'] += 1


def self_test():
    assert LFSR((0, 1), 1).generate(12) == [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    assert [period(t, 1) for _, t in POLYNOMIALS] == [9, 31, 63]
    assert period((0, 1), 0) == 1
    for n in range(2, 1000):
        assert miller_rabin(n, Random(n), 10) == trial_prime(n)
    for F in (2, 3, 5, 7, 11, 13):
        for n in range(2 * F + 1, 2000, 2 * F):
            actual = any(sufficient_test(n, F, a) for a in range(2, min(n, 66)))
            assert actual == trial_prime(n), (n, F)
    for m in (8, 16, 32, 64):
        n, cert = mihailescu(m, Random(7 + m), [])
        assert n.bit_length() == m and verify_certificate(cert)
    print('Самопроверка: OK')


def plots(rows, folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    selected = [r for r in rows if r['seed'] == 1]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
    for ax, row in zip(axes, selected):
        ax.bar(['0', '1'], [row['zeros'], row['ones']], color=['#56748c', '#9badbc'])
        ax.axhline((row['zeros'] + row['ones']) / 2, color='black', linestyle='--')
        ax.set_title(row['polynomial'] + '\nT=' + str(row['period']))
        ax.set_xlabel('Бит'); ax.set_ylabel('Частота')
    fig.tight_layout(); fig.savefig(folder / 'frequencies.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 3.3))
    for name, taps in POLYNOMIALS:
        ax.plot(range(1, 64), [period(taps, s) for s in range(1, 64)], '.', label=name)
    ax.set(xlabel='Начальное состояние', ylabel='Период', ylim=(0, 68))
    ax.legend(); fig.tight_layout(); fig.savefig(folder / 'periods.png', dpi=160); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='ЛР1, вариант 7: LFSR и метод Михалеску')
    parser.add_argument('--length', type=int, default=1000)
    parser.add_argument('--bits', type=int, default=64)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if args.length < 10 or not 8 <= args.bits <= 64:
        parser.error('Длина >=10; разрядность от 8 до 64 (учебный диапазон).')
    folder = ROOT / 'results'; folder.mkdir(exist_ok=True)
    rows = statistics(args.length, folder)
    messages = [f'Вариант 7. Длина={args.length}; разрядность={args.bits}; seed={args.seed}']
    for r in rows:
        messages.append(f"{r['polynomial']}; state={r['seed']}; T={r['period']}; "
                        f"0: {r['zeros']}, 1: {r['ones']}; chi2={r['chi2']:.6f}; "
                        f"H0 {'не отвергается' if r['uniform'] else 'отвергается'}")
    # Собственная схема Михалеску разрешена примечанием таблицы вариантов.
    log = []
    n, cert = mihailescu(args.bits, Random(args.seed), log)
    assert verify_certificate(cert)
    (folder / 'certificate.json').write_text(json.dumps(cert, indent=2), encoding='utf-8')
    with (folder / 'prime_log.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=log[0]); writer.writeheader(); writer.writerows(log)
    messages += [f'Простое число: {n}', f'Битов: {n.bit_length()}', 'Сертификат простоты: OK',
                 f'Последний уровень: {log[-1]}',
                 'Всего кандидатов на всех уровнях: ' + str(sum(r['candidates'] for r in log)),
                 'Время верхнего уровня включает рекурсивные вызовы.']
    if not args.no_plots:
        plots(rows, folder)
    text = '\n'.join(messages)
    print(text)
    (folder / 'run.txt').write_text(text + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
