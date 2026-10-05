#!/usr/bin/env python3
"""Лабораторная №2, вариант 11: единое консольное приложение на Python."""
import argparse
import sys
from pathlib import Path
from lab.core import Random, bits_from_text, bits_text, hamming, iterative, inject, MAX_K
from lab.experiments import write_csv, save


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
    with Path(path).open('rb') as source:
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
                    file_demo(Path(__file__).parent / 'examples/message.txt', 4, 1, args.seed, stream)
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
