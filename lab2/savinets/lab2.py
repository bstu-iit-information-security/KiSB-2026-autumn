#!/usr/bin/env python3
"""Лабораторная №2, вариант 11. Самостоятельный файл; только стандартная библиотека."""

# Алгоритмы
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


# Эксперименты
import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ['family', 'k', 'r', 'n', 'rows', 'cols', 'planes', 'groups', 'distance',
          'errors', 'trials', 'detected', 'restored', 'rejected', 'miscorrected', 'seed']


def configurations(table_variant=1):
    integer(table_variant, 1, 5, 'вариант таблицы')
    shapes = SHAPES[table_variant - 1]
    for distance in (3, 4):
        yield 'hamming', hamming(shapes[0][0] * shapes[0][1], distance), (0, 0, 0), 0, distance
    for shape in shapes:
        for groups in range(2, 4 if shape[2] == 1 else 6):
            yield 'iterative', iterative(*shape, groups), shape, groups, 0


def experiment_rows(trials=3000, seed=11, table_variant=1):
    integer(trials, 1, 1000000, 'число испытаний')
    for family, code, shape, groups, distance in configurations(table_variant):
        rng = Random(seed)
        message = sum((rng.next() & 1) << i for i in range(code.k))
        original = code.encode(message)
        for errors in range(6):
            detected = restored = rejected = miscorrected = 0
            for _ in range(trials):
                received = inject(original, code.n, errors, rng)
                decoded = code.decode(received)
                detected += decoded.syndrome != 0
                restored += decoded.word == original
                rejected += decoded.syndrome != 0 and decoded.matches != 1
                miscorrected += decoded.matches == 1 and decoded.word != original
            yield dict(zip(FIELDS, [family, code.k, code.r, code.n, *shape, groups, distance,
                                   errors, trials, detected, restored, rejected, miscorrected, seed]))


def write_csv(stream, trials=3000, seed=11, table_variant=1):
    writer = csv.DictWriter(stream, FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(experiment_rows(trials, seed, table_variant))


def save(directory, trials=3000, seed=11, table_variant=1):
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    with (target / 'experiments.csv').open('w', newline='', encoding='utf-8') as stream:
        write_csv(stream, trials, seed, table_variant)
    metadata = dict(implementation='Python', python=sys.version, platform=platform.platform(),
                    timestamp_utc=datetime.now(timezone.utc).isoformat(), trials=trials,
                    seed=seed, table_variant=table_variant)
    (target / 'environment.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


# Консольный интерфейс
import io
DEFAULT_MESSAGE = bytes([208,155,208,176,208,177,208,190,209,128,208,176,209,130,208,190,209,128,208,189,208,176,209,143,32,209,128,208,176,208,177,208,190,209,130,208,176,32,50,46,32,72,97,109,109,105,110,103,32,99,111,100,101,44,32,48,49,50,51,52,53,54,55,56,57,33,32,208,158,209,136,208,184,208,177,208,186,208,184,32,208,191,208,181,209,128,208,181,208,180,208,176,209,135,208,184,32,208,184,32,208,178,208,190,209,129,209,129,209,130,208,176,208,189,208,190,208,178,208,187,208,181,208,189,208,184,208,181,32,208,180,208,176,208,189,208,189,209,139,209,133,46,10])

import argparse
import sys
from pathlib import Path


def matrix(code, stream):
    print(f'k={code.k} r={code.r} n={code.n}\nH=[P|I] (row order: low syndrome bit first)', file=stream)
    columns = code.columns
    for row in range(code.r):
        line = ''.join(str((column >> row) & 1) for column in columns)
        print(line[:code.k] + '|' + line[code.k:], file=stream)


def print_decoded(code, received, stream):
    decoded = code.decode(received)
    print('Yn=' + bits_text(received, code.n), file=stream)
    print('Yr=' + bits_text(received >> code.k, code.r), file=stream)
    recalculated = code.encode(received & ((1 << code.k) - 1)) >> code.k
    print('Yr_recomputed=' + bits_text(recalculated, code.r), file=stream)
    status = ('no_error_detected' if decoded.syndrome == 0 else
              'corrected_single_candidate' if decoded.matches == 1 else 'detected_uncorrectable')
    print('S=' + bits_text(decoded.syndrome, code.r), file=stream)
    print('status=' + status, file=stream)
    print('En_estimated=' + bits_text(received ^ decoded.word, code.n), file=stream)
    print('Yn_corrected=' + bits_text(decoded.word, code.n), file=stream)
    print('data_decoded=' + bits_text(decoded.word & ((1 << code.k) - 1), code.k), file=stream)


def demonstrate(code, message, errors, seed, stream):
    original = code.encode(message)
    received = inject(original, code.n, errors, Random(seed))
    matrix(code, stream)
    print('Xk=' + bits_text(message, code.k), file=stream)
    print('Xr=' + bits_text(original >> code.k, code.r), file=stream)
    print('Xn=' + bits_text(original, code.n), file=stream)
    print('En_actual=' + bits_text(original ^ received, code.n), file=stream)
    print(f'errors={errors} seed={seed}', file=stream)
    print_decoded(code, received, stream)
    print(f'restored={int(code.decode(received).word == original)}', file=stream)


def file_demo(path, distance, errors, seed, stream):
    block = 0
    with (io.BytesIO(DEFAULT_MESSAGE) if path is None else Path(path).open('rb')) as source:
        while True:
            data = source.read(MAX_K // 8)
            if not data:
                break
            message = bits_from_text(''.join(format(byte, '08b') for byte in data))
            code = hamming(len(data) * 8, distance)
            print(f'block={block} bytes={len(data)} encoding=UTF-8/raw-bytes', file=stream)
            demonstrate(code, message, errors, (seed + block) & ((1 << 64) - 1), stream)
            block += 1
    if block == 0:
        raise ValueError('Входной файл пуст.')


def parser():
    result = argparse.ArgumentParser(description='Lab2: Хэмминг и итеративные коды на Python; вариант 11, таблица 1.')
    commands = result.add_subparsers(dest='command', required=True)
    for command in ('hamming', 'hamming-file'):
        p = commands.add_parser(command)
        p.add_argument('input')
        p.add_argument('distance', type=int, choices=(3, 4))
        p.add_argument('errors', type=int)
        p.add_argument('seed', type=int)
    p = commands.add_parser('hamming-decode')
    p.add_argument('k', type=int)
    p.add_argument('distance', type=int, choices=(3, 4))
    p.add_argument('received')
    for command in ('iterative', 'iterative-decode'):
        p = commands.add_parser(command)
        if command == 'iterative':
            p.add_argument('input')
        for name in ('rows', 'cols', 'planes', 'groups'):
            p.add_argument(name, type=int)
        if command == 'iterative':
            p.add_argument('errors', type=int)
            p.add_argument('seed', type=int)
        else:
            p.add_argument('received')
    p = commands.add_parser('experiments')
    p.add_argument('trials', nargs='?', type=int, default=3000)
    p.add_argument('seed', nargs='?', type=int, default=11)
    p.add_argument('table_variant', nargs='?', type=int, default=1)
    p.add_argument('--directory', help='Сохранить CSV, среду и протоколы примеров в каталог')
    return result


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    try:
        if args.command == 'experiments':
            if args.directory:
                save(args.directory, args.trials, args.seed, args.table_variant)
                target = Path(args.directory)
                for name, distance, errors in [('hamming-double-d3.txt', 3, 2), ('hamming-double-d4.txt', 4, 2)]:
                    with (target / name).open('w', encoding='utf-8') as stream:
                        demonstrate(hamming(16, distance), bits_from_text('1011010010110100'), errors, args.seed, stream)
                with (target / 'iterative-example.txt').open('w', encoding='utf-8') as stream:
                    print('layout: planes=1 rows=4 cols=4 groups=3\nplane=0\n1011\n0100\n1011\n0100', file=stream)
                    demonstrate(iterative(4, 4, 1, 3), bits_from_text('1011010010110100'), 1, args.seed, stream)
                with (target / 'hamming-file.txt').open('w', encoding='utf-8') as stream:
                    file_demo(None, 4, 1, args.seed, stream)
                print(f'Результаты Python сохранены в {target}.')
            else:
                write_csv(sys.stdout, args.trials, args.seed, args.table_variant)
        elif args.command == 'hamming-file':
            # Validate even an empty file's seed and error count before opening it.
            Random(args.seed)
            if args.errors < 0:
                raise ValueError('Число ошибок не может быть отрицательным.')
            file_demo(args.input, args.distance, args.errors, args.seed, sys.stdout)
        elif args.command in ('hamming', 'hamming-decode'):
            if args.command == 'hamming':
                message = bits_from_text(args.input)
                code = hamming(len(args.input), args.distance)
                demonstrate(code, message, args.errors, args.seed, sys.stdout)
            else:
                code = hamming(args.k, args.distance)
                received = bits_from_text(args.received)
                if len(args.received) != code.n:
                    raise ValueError('Длина принятого слова не совпадает с n.')
                matrix(code, sys.stdout)
                print_decoded(code, received, sys.stdout)
        else:
            code = iterative(args.rows, args.cols, args.planes, args.groups)
            if args.command == 'iterative-decode':
                received = bits_from_text(args.received)
                if len(args.received) != code.n:
                    raise ValueError('Длина принятого слова не совпадает с n.')
                matrix(code, sys.stdout)
                print_decoded(code, received, sys.stdout)
            else:
                message = bits_from_text(args.input)
                if len(args.input) != code.k:
                    raise ValueError('Длина сообщения не совпадает с произведением размеров.')
                print(f'layout: planes={args.planes} rows={args.rows} cols={args.cols} groups={args.groups}')
                for z in range(args.planes):
                    print(f'plane={z}')
                    for row in range(args.rows):
                        offset = (z * args.rows + row) * args.cols
                        print(args.input[offset:offset + args.cols])
                demonstrate(code, message, args.errors, args.seed, sys.stdout)
        sys.stdout.flush()
        return 0
    except ValueError as error:
        argument_parser.error(str(error))
    except OSError as error:
        print(f'Ошибка ввода/вывода: {error}', file=sys.stderr)
        return 3


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
