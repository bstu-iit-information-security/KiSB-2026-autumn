import csv
import io
import itertools
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from lab2 import (Code, Random, bits_from_text, bits_text, hamming, iterative,
                      inject, MAX_K, SHAPES)
from lab2 import experiment_rows

ROOT = Path(__file__).resolve().parents[1]


def independent_syndrome(code, word):
    value = 0
    for row in range(code.r):
        parity = 0
        for i, column in enumerate(code.columns):
            parity ^= ((column >> row) & 1) & ((word >> i) & 1)
        value |= parity << row
    return value


class CodeTests(unittest.TestCase):
    def check_code(self, code, secded=False):
        message = sum((i % 3 == 0) << i for i in range(code.k))
        original = code.encode(message)
        self.assertEqual(independent_syndrome(code, original), 0)
        self.assertEqual(code.decode(original).word, original)
        for i in range(code.n):
            decoded = code.decode(original ^ (1 << i))
            self.assertEqual((decoded.matches, decoded.position, decoded.word), (1, i, original))
        for i, j in itertools.combinations(range(code.n), 2):
            received = original ^ (1 << i) ^ (1 << j)
            decoded = code.decode(received)
            self.assertNotEqual(decoded.syndrome, 0)
            if secded:
                self.assertEqual((decoded.matches, decoded.word), (0, received))

    def test_hamming_errors(self):
        for k in (4, 6, 8, 9, 10, 15, 16, 24, 40):
            for distance in (3, 4):
                self.check_code(hamming(k, distance), distance == 4)

    def test_large_blocks(self):
        for k in (256, MAX_K):
            for distance in (3, 4):
                code = hamming(k, distance)
                original = code.encode(1 | (1 << (k - 1)))
                self.assertEqual(independent_syndrome(code, original), 0)
                self.assertEqual(code.decode(original ^ (1 << (k - 1))).word, original)

    def test_exhaustive_minimum_distance(self):
        # Independent row multiplication for every 16-bit message, not the encoder.
        for distance in (3, 4):
            code = hamming(16, distance)
            minimum = code.n
            for message in range(65536):
                word = code.encode(message)
                self.assertEqual(independent_syndrome(code, word), 0)
                if message:
                    minimum = min(minimum, word.bit_count())
            self.assertEqual(minimum, distance)

    def test_iterative_errors(self):
        for shape in (*SHAPES[0], (2, 2, 5), (3, 3, 4), (4, 4, 2), (2, 10, 2)):
            for groups in range(2, 4 if shape[2] == 1 else 6):
                self.check_code(iterative(*shape, groups), shape[2] == 1 and groups == 3)

    def test_rectangle_and_ambiguity(self):
        code = iterative(4, 4, 1, 2)
        rectangle = sum(1 << i for i in (0, 1, 4, 5))
        self.assertEqual(code.syndrome(rectangle), 0)
        self.assertEqual(code.decode(rectangle).word, rectangle)
        duplicate = Code(2, 2, (3, 3))
        self.assertEqual(duplicate.decode(1).matches, 2)
        self.assertEqual(duplicate.decode(1).word, 1)

    def test_injection_and_rng(self):
        self.assertEqual(Random(11).next(), 5833679380957638813)
        for errors in range(23):
            first = inject(0, 22, errors, Random(11))
            self.assertEqual(first.bit_count(), errors)
            self.assertEqual(first, inject(0, 22, errors, Random(11)))

    def test_validation(self):
        for args in ((0, 3), (4097, 4), (16, 5), (True, 3)):
            with self.assertRaises(ValueError):
                hamming(*args)
        for args in ((0, 4, 1, 2), (4, 4, 1, 5), (16, 16, 5, 5)):
            with self.assertRaises(ValueError):
                iterative(*args)
        for value in ('', '01x', '0' * 4353):
            with self.assertRaises(ValueError):
                bits_from_text(value)
        for text in ('0', '1', '00101100'):
            self.assertEqual(bits_text(bits_from_text(text), len(text)), text)
        for word in (-1, 1 << 22):
            with self.assertRaises(ValueError):
                inject(word, 22, 1, Random(11))
        for args in ((0, 22, 23), (0, 0, 0)):
            with self.assertRaises(ValueError):
                inject(*args, Random(11))

    def test_experiments(self):
        for variant in range(1, 6):
            rows = list(experiment_rows(3, 11, variant))
            self.assertEqual(len(rows), 84)
            for row in rows:
                if row['errors'] <= 1:
                    self.assertEqual(row['restored'], 3)
                if row['family'] == 'hamming' and row['distance'] == 4 and row['errors'] == 2:
                    self.assertEqual((row['detected'], row['rejected'], row['miscorrected']), (3, 3, 0))


class CliTests(unittest.TestCase):
    def run_cli(self, *args, good=True):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'lab2.py'), *map(str, args)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode == 0, good, result.stderr)
        return result.stdout

    def test_hamming_cli(self):
        for distance in (3, 4):
            for errors in (0, 1, 2):
                output = self.run_cli('hamming', '1011010010110100', distance, errors, 11)
                self.assertIn('S=', output)
                if errors < 2:
                    self.assertIn('restored=1', output)
                elif distance == 4:
                    self.assertIn('status=detected_uncorrectable', output)
            clean = self.run_cli('hamming', '1011010010110100', distance, 0, 11)
            word = next(line[3:] for line in clean.splitlines() if line.startswith('Xn='))
            self.assertIn('data_decoded=1011010010110100', self.run_cli('hamming-decode', 16, distance, word))

    def test_iterative_cli(self):
        for shape in SHAPES[0]:
            for groups in range(2, 4 if shape[2] == 1 else 6):
                output = self.run_cli('iterative', '1011010010110100', *shape, groups, 1, 11)
                self.assertIn('restored=1', output)
                word = next(line[3:] for line in output.splitlines() if line.startswith('Xn='))
                self.assertIn('data_decoded=1011010010110100', self.run_cli('iterative-decode', *shape, groups, word))

    def test_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'message.txt'
            path.write_bytes(('Русский English 0123!\n' * 80).encode())
            output = self.run_cli('hamming-file', path, 4, 1, 11)
            self.assertGreater(output.count('block='), 1)
            self.assertNotIn('restored=0', output)
            path.write_bytes(b'')
            self.run_cli('hamming-file', path, 4, 1, 11, good=False)

    def test_invalid_cli(self):
        for args in (('hamming', '01x', 4, 1, 11), ('hamming', '1010', 5, 1, 11),
                     ('hamming', '1010', 4, 100, 11), ('hamming', '1010', 4, -1, 11),
                     ('hamming', '1010', 4, 0, -1), ('hamming-decode', 16, 4, '0'),
                     ('iterative', '1010', 2, 2, 1, 5, 1, 11), ('experiments', 0),
                     ('experiments', 2, 11, 6), ('unknown',)):
            self.run_cli(*args, good=False)


if __name__ == '__main__':
    unittest.main()
