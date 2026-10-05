#!/usr/bin/env python3
"""Единая точка входа. Пример: python3 lab1.py generate 16."""
import argparse
import sys
from time import perf_counter
from lab.core import Generator, Parameters, aks, cycle, generate, statistics


def parser():
    result = argparse.ArgumentParser(description='ЛР №1, вариант 11: генератор N=10 и тест AKS (Python).')
    commands = result.add_subparsers(dest='command', required=True)
    for name in ('sequence', 'stats'):
        command = commands.add_parser(name, help='Последовательность' if name == 'sequence' else 'Статистика')
        command.add_argument('length', type=int)
        command.add_argument('parameters', nargs='*', type=int, metavar='d a c x0')
    check = commands.add_parser('check', help='Проверка числа на простоту')
    check.add_argument('n', type=int)
    generation = commands.add_parser('generate', help='Поиск простого числа заданной разрядности')
    generation.add_argument('bits', type=int)
    generation.add_argument('seed', nargs='?', type=int, default=0)
    generation.add_argument('sieve', nargs='?', type=int, default=256)
    generation.add_argument('attempts', nargs='?', type=int, default=100000)
    experiment = commands.add_parser('experiments', help='Воспроизвести измерения и CSV')
    experiment.add_argument('directory', nargs='?', default='results')
    experiment.add_argument('--include-32', action='store_true', help='Добавить 32-битный контрольный запуск')
    return result


def main(argv=None):
    command_parser = parser()
    args = command_parser.parse_args(argv)
    try:
        if args.command in ('sequence', 'stats'):
            if args.length < 1 or len(args.parameters) not in (0, 4):
                raise ValueError('Нужна положительная длина и либо 0, либо 4 параметра: d a c x0.')
            p = Parameters(*args.parameters) if args.parameters else Parameters()
            if args.command == 'sequence':
                for i, value in enumerate(Generator(p).sequence(args.length), 1):
                    print(value, end='\n' if i % 40 == 0 or i == args.length else ' ')
            else:
                s, cy = statistics(p, args.length), cycle(p)
                print(f'transient={cy.transient} period={cy.period} chi_square={s.chi_square:.6f} '
                      f'entropy_bits={s.entropy:.6f} pair_chi_square={s.pair_chi_square:.6f}')
                print('serial_correlation=' + ('undefined' if s.serial_correlation is None else f'{s.serial_correlation:.6f}'))
                print('digit,count')
                for digit, count in enumerate(s.counts):
                    print(f'{digit},{count}')
        elif args.command == 'check':
            begin = perf_counter()
            result = aks(args.n)
            print(f'n={args.n} verdict={result.verdict} reason={result.reason} r={result.r} '
                  f'polynomial_checks={result.checks} witness={result.witness} elapsed_ms={(perf_counter()-begin)*1000:.6f}')
            if result.verdict == 'capacity_exceeded':
                return 4
        elif args.command == 'generate':
            result = generate(Parameters(seed=args.seed), args.bits, args.sieve, args.attempts, sys.stdout)
            print(summary(result), file=sys.stderr)
            if not result.found:
                return 4 if result.capacity_error else 5
        else:
            from lab.experiments import run
            run(args.directory, args.include_32)
        sys.stdout.flush()
        return 0
    except ValueError as error:
        command_parser.error(str(error))
    except OSError as error:
        print(f'Ошибка ввода/вывода: {error}', file=sys.stderr)
        return 3
    except RuntimeError as error:
        print(f'Ошибка вычисления: {error}', file=sys.stderr)
        return 4


def summary(result):
    return (f'found={int(result.found)} prime={result.prime} start={result.start} candidates={result.candidates} '
            f'sieve_rejected={result.sieve_rejected} aks_rejected={result.aks_rejected} '
            f'aks_calls={result.aks_calls} elapsed_ms={result.elapsed_ms:.6f}')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nВыполнение остановлено.', file=sys.stderr)
        raise SystemExit(130)
