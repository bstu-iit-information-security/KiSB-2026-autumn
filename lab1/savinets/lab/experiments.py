"""Воспроизводимые эксперименты. CSV всегда вычисляются Python-реализацией."""
from pathlib import Path
import csv
import json
import platform
import sys
from datetime import datetime, timezone
from .core import Parameters, cycle, statistics, generate, trial_prime

CASES = [
    ('c0_best', Parameters(5, 2, 0, 1)),
    ('c0_zero_seed', Parameters(5, 2, 0, 0)),
    ('mixed_best', Parameters()),
    ('mixed_seed7', Parameters(seed=7)),
    ('mixed_c2', Parameters(5, 6, 2, 0)),
    ('nonlinear_short', Parameters(1, 1, 1, 0)),
]


def run(directory='results', include_32=False):
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    with (target / 'period_search.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['d', 'a', 'c', 'seed', 'transient', 'period'])
        for d in range(1, 10):
            for a in range(10):
                for c in range(10):
                    for seed in range(10):
                        cy = cycle(Parameters(d, a, c, seed))
                        writer.writerow([d, a, c, seed, cy.transient, cy.period])
    print('Полный перебор 9000 конфигураций завершён.', flush=True)
    with (target / 'statistics.csv').open('w', newline='') as f, (target / 'pairs.csv').open('w', newline='') as pf:
        writer, pair_writer = csv.writer(f), csv.writer(pf)
        writer.writerow(['case', 'd', 'a', 'c', 'seed', 'length', 'transient', 'period', 'chi_square', 'entropy',
                         'serial_correlation', 'pair_chi_square'] + [f'count_{i}' for i in range(10)])
        pair_writer.writerow(['case', 'first', 'second', 'count'])
        for name, params in CASES:
            for length in (100, 1000, 10000):
                s, cy = statistics(params, length), cycle(params)
                writer.writerow([name, params.d, params.a, params.c, params.seed, length, cy.transient, cy.period,
                                 s.chi_square, s.entropy, s.serial_correlation, s.pair_chi_square] + s.counts)
                if length == 10000:
                    pair_writer.writerows([name, x, y, s.pairs[10*x+y]] for x in range(10) for y in range(10))
    with (target / 'prime_generation.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['bits', 'seed', 'sieve_bound', 'start', 'prime', 'candidates', 'sieve_rejected',
                         'aks_rejected', 'aks_calls', 'elapsed_ms'])
        for bits in (8, 10, 12, 16):
            for sieve in (0, 256, 2000):
                with (target / f'candidates_{bits}bit_sieve{sieve}.csv').open('w', newline='') as log:
                    result = generate(Parameters(), bits, sieve, log=log)
                if not result.found or not trial_prime(result.prime):
                    raise RuntimeError('Генерация не завершилась проверенным простым числом.')
                writer.writerow([bits, 0, sieve, result.start, result.prime, result.candidates,
                                 result.sieve_rejected, result.aks_rejected, result.aks_calls, f'{result.elapsed_ms:.6f}'])
                print(f'{bits} бит, просев {sieve}: p={result.prime}, кандидатов={result.candidates}, '
                      f'{result.elapsed_ms:.2f} мс', flush=True)
    if include_32:
        print('Выполняется отдельный 32-битный запуск...', flush=True)
        with (target / 'check_32bit.csv').open('w', newline='') as log:
            result = generate(Parameters(), 32, 256, log=log)
        if not result.found or not trial_prime(result.prime):
            raise RuntimeError('Ошибка 32-битной генерации.')
        # Keep the same plain-text data format as CLI; no dependency on CLI module.
        summary = ' '.join(f'{key}={int(value) if isinstance(value, bool) else value}' for key, value in vars(result).items())
        (target / 'check_32bit_summary.txt').write_text(summary + '\n')
        print(summary, flush=True)
    environment = {'implementation': 'Python', 'python': sys.version, 'platform': platform.platform(),
                   'machine': platform.machine(), 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                   'include_32': include_32}
    (target / 'environment.json').write_text(json.dumps(environment, ensure_ascii=False, indent=2) + '\n')
