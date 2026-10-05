"""Воспроизводимые испытания Python-кодов с фиксированным seed."""
import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from .core import Random, SHAPES, hamming, iterative, inject, integer

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
