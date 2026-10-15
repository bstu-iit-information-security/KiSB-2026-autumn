from math import gcd, isqrt
from secrets import randbelow
from time import perf_counter

N = 15
ROUNDS = 5


class LCG:
    def __init__(self, a=1, c=1, x=1):
        self.a, self.c, self.x = a, c, x

    def next(self):
        self.x = (self.a * self.x + self.c) % N
        return self.x

    def sequence(self, length):
        return [self.next() for _ in range(length)]

    def number(self, bits):
        # Объединяем 4-битовые записи выходов ЛКГ, оставляем bits бит.
        value = 0
        for _ in range((bits + 3) // 4):
            value = (value << 4) | self.next()
        return value & ((1 << bits) - 1)


def cycle(a, c, x):
    seen = {}
    while x not in seen:
        seen[x] = len(seen)
        x = (a * x + c) % N
    return seen[x], len(seen) - seen[x]


def statistics(values):
    counts = [values.count(x) for x in range(N)]
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    expected = len(values) / N
    chi2 = sum((count - expected) ** 2 / expected for count in counts)
    return counts, mean, variance, chi2


def trial_prime(n):
    return n >= 2 and all(n % d for d in range(2, isqrt(n) + 1))


SMALL_PRIMES = [n for n in range(2, 257) if trial_prime(n)]


def lehmann(n, rounds=ROUNDS, choose=randbelow):
    # True: вероятно простое; False: составное; None: все остатки равны 1.
    if n in (2, 3):
        return True
    if n < 2 or n % 2 == 0:
        return False
    minus_one = False
    for _ in range(rounds):
        a = 1 + choose(n - 1)  # 1 <= a < n; независимые основания.
        if gcd(a, n) != 1:
            return False
        t = pow(a, (n - 1) // 2, n)
        if t not in (1, n - 1):
            return False
        minus_one |= t == n - 1
    return True if minus_one else None


def generate_prime(bits, generator):
    n = generator.number(bits) | (1 << (bits - 1)) | 1
    attempts = screened = rejected = uncertain = 0
    start = perf_counter()
    # Перебор от случайного старта разрешён в ч.2, с.54.
    for _ in range(1 << (bits - 2)):
        attempts += 1
        if any(n != p and n % p == 0 for p in SMALL_PRIMES):
            screened += 1
        else:
            result = lehmann(n)
            if result is True:
                return n, attempts, screened, rejected, uncertain, perf_counter() - start
            if result is False:
                rejected += 1
            else:
                uncertain += 1
        n += 2
        if n >= 1 << bits:
            n = (1 << (bits - 1)) | 1
    raise RuntimeError('Весь диапазон проверен; повторите поиск.')


def self_test():
    assert cycle(2, 0, 1) == (0, 4)
    assert cycle(1, 1, 1) == (0, 15)
    assert max(cycle(a, 0, x)[1] for a in range(1, N) for x in range(N)) == 4
    # Сравнение со строгим пробным делением; все основания для n <= 300.
    for n in range(2, 301):
        bases = iter(range(max(1, n - 1)))
        assert lehmann(n, max(1, n - 1), lambda _: next(bases)) == trial_prime(n)
    for n in (341, 561, 1105, 1729, 2465, 2821, 6601):
        bases = iter(range(n - 1))
        assert lehmann(n, n - 1, lambda _: next(bases)) is False
    assert lehmann(7, 5, lambda _: 0) is None
    for bits in (8, 16, 32, 64, 128):
        n = LCG().number(bits) | (1 << (bits - 1)) | 1
        assert n.bit_length() == bits and n % 2 == 1
    print('Самопроверка: OK (периоды, простота 2..300, числа Кармайкла, биты).')


def main():
    self_test()
    length = int(input('Длина последовательности [1500]: ') or 1500)
    bits = int(input('Разрядность кандидата [64]: ') or 64)
    if length < 1 or bits < 3:
        raise ValueError('Длина должна быть >= 1, разрядность >= 3.')
    print('\nЛКГ: x_next = (a*x + c) mod 15; x0 = 1')
    print(' a  c  хвост период    среднее дисперсия   хи-квадрат')
    for a, c in ((2, 0), (4, 0), (1, 1), (1, 3), (2, 1)):
        values = LCG(a, c).sequence(length)
        counts, mean, variance, chi2 = statistics(values)
        tail, period = cycle(a, c, 1)
        print(f'{a:2} {c:2} {tail:6} {period:6} {mean:10.4f} {variance:9.4f} {chi2:12.4f}')
        print('Первые 30:', *values[:30])
        print('Частоты 0..14:', *counts)
        if length >= 75:
            print('Частотный критерий:', 'не отвергает H0' if chi2 <= 23.685 else 'отвергает H0')
        else:
            print('Для критерия нужно не менее 75 значений.')
    print('Для равномерного распределения 0..14: M=7, D=56/3.')
    print('Порог хи-квадрат: 23.685; alpha=0.05; df=14.')
    print('Частотная проверка не доказывает независимость выходов ЛКГ.')
    print('\nПоиск вероятно простых чисел; тест Леманна, 5 раундов.')
    generator = LCG()
    for _ in range(3):
        n, total, sieve, rejected, unknown, elapsed = generate_prime(bits, generator)
        print(f'n={n}; бит={n.bit_length()}; кандидатов={total}; сито={sieve}; '
              f'Леманн отклонил={rejected}; неопределённо={unknown}; время={elapsed:.6f} с')
    print('Результат вероятностный. Граница ошибки теста: 2^-5 = 1/32.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError) as error:
        print('Ошибка:', error)
