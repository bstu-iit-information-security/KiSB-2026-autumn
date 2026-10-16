from math import gcd, isqrt
from secrets import randbelow
from time import perf_counter

N, K, ROUNDS = 10, 5, 5


class LCG:
    def __init__(self, a, c, m, x):
        self.a, self.c, self.m, self.x = a, c, m, x

    def next(self):
        result = self.x
        self.x = (self.a * self.x + self.c) % self.m
        return result


class MacLarenMarsaglia:
    def __init__(self, a=1, c=1, b=1, d=1, x=0, y=1):
        self.g1 = LCG(a, c, N, x)
        self.g2 = LCG(b, d, K, y)
        self.table = [self.g1.next() for _ in range(K)]

    def next(self):
        s = self.g2.next()
        result = self.table[s]
        self.table[s] = self.g1.next()
        return result

    def state(self):
        return self.g1.x, self.g2.x, tuple(self.table)

    def number(self, bits):
        value = 0
        for _ in range((bits + 3) // 4):
            value = (value << 4) | self.next()
        return (value & ((1 << bits) - 1)) | (1 << (bits - 1)) | 1


def cycle(generator):
    seen, values = {}, []
    while generator.state() not in seen:
        seen[generator.state()] = len(values)
        values.append(generator.next())
    tail = seen[generator.state()]
    block = values[tail:]
    # Период полного состояния и минимальный период выходов могут отличаться.
    for period in range(1, len(block) + 1):
        if len(block) % period == 0 and all(v == block[i % period] for i, v in enumerate(block)):
            return tail, len(block), period


def statistics(generator, length):
    counts = [0] * N
    for _ in range(length):
        counts[generator.next()] += 1
    mean = sum(x * f for x, f in enumerate(counts)) / length
    variance = sum((x - mean) ** 2 * f for x, f in enumerate(counts)) / length
    chi2 = sum((f - length / N) ** 2 / (length / N) for f in counts)
    return counts, mean, variance, chi2


def jacobi(a, n):
    result = 1
    a %= n
    while a:
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        a, n = n, a
        if a % 4 == n % 4 == 3:
            result = -result
        a %= n
    return result if n == 1 else 0


def solovay_strassen(n, rounds=ROUNDS, choose=randbelow):
    if n in (2, 3):
        return True
    if n < 2 or n % 2 == 0:
        return False
    for _ in range(rounds):
        a = 1 + choose(n - 1)
        if gcd(a, n) != 1 or pow(a, (n - 1) // 2, n) != jacobi(a, n) % n:
            return False
    return True


def trial_prime(n):
    return n >= 2 and all(n % d for d in range(2, isqrt(n) + 1))


SMALL_PRIMES = [n for n in range(2, 257) if trial_prime(n)]
CASES = ((1, 1, 2, 0), (1, 1, 1, 1), (1, 2, 2, 0), (2, 0, 2, 0))


def generate_prime(bits, generator):
    n = generator.number(bits)
    total = screened = rejected = 0
    start = perf_counter()
    # Перебор от начального кандидата разрешён методичкой (с.54).
    for _ in range(1 << (bits - 2)):
        total += 1
        if any(n != p and n % p == 0 for p in SMALL_PRIMES):
            screened += 1
        elif solovay_strassen(n):
            return n, total, screened, rejected, perf_counter() - start
        else:
            rejected += 1
        n += 2
        if n >= 1 << bits:
            n = (1 << (bits - 1)) | 1
    raise RuntimeError('Поиск не дал результата; повторите запуск.')


def self_test():
    g = MacLarenMarsaglia()
    assert [g.next() for _ in range(8)] == [1, 2, 3, 4, 0, 5, 6, 7]
    assert cycle(MacLarenMarsaglia())[2] == 10
    for n in range(2, 301):
        bases = iter(range(n - 1))
        assert solovay_strassen(n, n - 1, lambda _: next(bases)) == trial_prime(n)
    for n in (341, 561, 1105, 1729, 2465, 2821, 6601):
        bases = iter(range(n - 1))
        assert not solovay_strassen(n, n - 1, lambda _: next(bases))
    for p in (3, 5, 7, 11, 13, 17, 19):
        for a in range(p):
            assert jacobi(a, p) % p == pow(a, (p - 1) // 2, p)
    for bits in (3, 8, 16, 64, 128):
        n = MacLarenMarsaglia().number(bits)
        assert n.bit_length() == bits and n % 2 == 1
    print('Самопроверка: OK')


def main():
    self_test()
    length = int(input('Длина последовательности [1000]: ') or 1000)
    bits = int(input('Разрядность кандидата [64]: ') or 64)
    if length < 1 or bits < 3:
        raise ValueError('Длина >= 1, разрядность >= 3.')
    print('\nМакларен—Марсалья: N=10, K=5; x0=0, y0=1.')
    for a, c, b, d in CASES:
        tail, state_period, period = cycle(MacLarenMarsaglia(a, c, b, d))
        counts, mean, variance, chi2 = statistics(MacLarenMarsaglia(a, c, b, d), length)
        print(f'a={a} c={c} b={b} d={d}: хвост состояния={tail}, '
              f'период состояния={state_period}, период выходов={period}')
        print(f'M={mean:.4f}; D={variance:.4f}; chi2={chi2:.4f}; частоты: {counts}')
        if length >= 50:
            print('H0 не отвергается' if chi2 <= 16.919 else 'H0 отвергается')
        else:
            print('Для критерия нужно не менее 50 значений.')
    print('Теория: M=4.5, D=8.25. Порог chi2=16.919; alpha=0.05; df=9.')
    print('\nТест Соловея—Штрассена: 5 раундов; вероятно простые числа.')
    generator = MacLarenMarsaglia()
    for _ in range(3):
        n, total, screened, rejected, elapsed = generate_prime(bits, generator)
        print(f'n={n}; бит={n.bit_length()}; кандидатов={total}; '
              f'сито={screened}; тест отклонил={rejected}; время={elapsed:.6f} с')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError) as error:
        print('Ошибка:', error)
