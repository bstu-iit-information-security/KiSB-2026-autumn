"""Систематические двоичные коды H=[P|I]. Только стандартная библиотека.

Бит i целого числа соответствует позиции i кодового слова; при печати
позиции идут от 0 к n-1, информационные биты первыми.
Python использует динамическую память; constant-time не гарантируется.
"""
from dataclasses import dataclass

MAX_K = 4096
MAX_R = 256
MASK64 = (1 << 64) - 1


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{label}: требуется целое число {low}..{high}.')
    return value


def bits_from_text(text):
    if not isinstance(text, str) or not text or any(c not in '01' for c in text):
        raise ValueError('Сообщение должно содержать только 0 и 1 и не быть пустым.')
    if len(text) > MAX_K + MAX_R:
        raise ValueError('Превышена ёмкость блока.')
    return int(text[::-1], 2)


def bits_text(value, length):
    return format(value, f'0{length}b')[::-1]


class Random:
    """SplitMix64 с явным сокращением до 64 бит; как в контрольной версии."""
    def __init__(self, seed):
        self.state = integer(seed, 0, MASK64, 'seed')

    def next(self):
        self.state = (self.state + 0x9e3779b97f4a7c15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xbf58476d1ce4e5b9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94d049bb133111eb) & MASK64
        return z ^ (z >> 31)

    def bounded(self, bound):
        integer(bound, 1, MASK64, 'bound')
        threshold = (1 << 64) % bound
        while True:
            value = self.next()
            if value >= threshold:
                return value % bound


@dataclass(frozen=True)
class Decoded:
    word: int
    syndrome: int
    matches: int
    position: int | None


@dataclass(frozen=True)
class Code:
    k: int
    r: int
    data: tuple

    def __post_init__(self):
        integer(self.k, 1, MAX_K, 'k')
        integer(self.r, 1, MAX_R, 'r')
        if len(self.data) != self.k or any(type(c) is not int or not 0 < c < (1 << self.r) for c in self.data):
            raise ValueError('Некорректные информационные столбцы матрицы.')

    @property
    def n(self):
        return self.k + self.r

    @property
    def columns(self):
        return self.data + tuple(1 << row for row in range(self.r))

    def check_word(self, word, length):
        integer(word, 0, (1 << length) - 1, 'двоичное слово')

    def encode(self, message):
        self.check_word(message, self.k)
        parity = 0
        for i, column in enumerate(self.data):
            parity ^= column * ((message >> i) & 1)
        return message | (parity << self.k)

    def syndrome(self, received):
        self.check_word(received, self.n)
        syndrome = received >> self.k
        for i, column in enumerate(self.data):
            syndrome ^= column * ((received >> i) & 1)
        return syndrome

    def decode(self, received):
        syndrome = self.syndrome(received)
        # Scan all columns, not an early-return lookup by the syndrome.
        matches, position = 0, None
        for i, column in enumerate(self.columns):
            if column == syndrome:
                matches += 1
                position = i
        corrected = received ^ (1 << position) if matches == 1 else received
        return Decoded(corrected, syndrome, matches, position if matches == 1 else None)


def hamming(k, distance):
    integer(k, 1, MAX_K, 'k')
    if type(distance) is not int or distance not in (3, 4):
        raise ValueError('Минимальное расстояние должно быть 3 или 4.')
    r = 2
    while (1 << r) < k + r + 1:
        r += 1
    data = sorted((v for v in range(1, 1 << r) if v.bit_count() >= 2),
                  key=lambda v: (v.bit_count(), v))[:k]
    if distance == 4:
        data = [v | ((1 ^ (v.bit_count() & 1)) << r) for v in data]
    return Code(k, r + (distance == 4), tuple(data))


def iterative(rows, cols, planes, groups):
    integer(rows, 1, 16, 'rows')
    integer(cols, 1, 16, 'cols')
    integer(planes, 1, 5, 'planes')
    integer(groups, 2, 3 if planes == 1 else 5, 'groups')
    diagonal = rows + cols - 1
    per_plane = rows + cols
    if planes == 1:
        per_plane += groups == 3
    else:
        per_plane += diagonal * ((groups >= 3) + (groups >= 4))
    r = per_plane * planes + (rows * cols if groups == 5 else 0)
    integer(r, 1, MAX_R, 'число проверок')
    data = []
    for z in range(planes):
        for row in range(rows):
            for col in range(cols):
                base = z * per_plane
                mask = (1 << (base + row)) | (1 << (base + rows + col))
                if planes == 1 and groups == 3:
                    mask |= 1 << (base + rows + cols)
                if planes > 1 and groups >= 3:
                    mask |= 1 << (base + rows + cols + row + col)
                if planes > 1 and groups >= 4:
                    mask |= 1 << (base + rows + cols + diagonal + row + cols - 1 - col)
                if planes > 1 and groups == 5:
                    mask |= 1 << (per_plane * planes + row * cols + col)
                data.append(mask)
    return Code(rows * cols * planes, r, tuple(data))


def inject(word, n, errors, rng):
    integer(n, 1, MAX_K + MAX_R, 'n')
    integer(word, 0, (1 << n) - 1, 'word')
    integer(errors, 0, n, 'число ошибок')
    positions = list(range(n))
    for i in range(errors):
        j = i + rng.bounded(n - i)
        positions[i], positions[j] = positions[j], positions[i]
        word ^= 1 << positions[i]
    return word


SHAPES = (
    ((4, 4, 1), (8, 2, 1), (4, 2, 2), (2, 4, 2)),
    ((4, 5, 1), (2, 10, 1), (2, 5, 2), (2, 2, 5)),
    ((4, 6, 1), (3, 8, 1), (3, 3, 4), (6, 2, 2)),
    ((4, 8, 1), (2, 16, 1), (8, 2, 2), (4, 4, 2)),
    ((5, 8, 1), (4, 10, 1), (5, 4, 2), (2, 10, 2)),
)
