"""Модульные тесты, подтверждающие правильность программ (требование задания)."""
import math
import unittest

from lfsr import LFSR, poly, is_primitive
from shrinking import ShrinkingGenerator, theoretical_period
from stats import chi2_sf, chi_square_uniform, smallest_period
from mihailescu import (Mihailescu, Journal, rabin_miller, is_prime_trial, sieve,
                        pocklington_witness, verify_certificate, SMALL_PRIMES)


def rng():
    return ShrinkingGenerator(poly(31, 3, 0), 0x1234567, poly(32, 22, 2, 1, 0), 0xABCDEF1)


class TestPart1(unittest.TestCase):
    def test_primitivity_variant10(self):
        self.assertTrue(is_primitive(poly(5, 2, 0)))
        self.assertTrue(is_primitive(poly(5, 4, 3, 2, 0)))
        self.assertFalse(is_primitive(poly(5, 0)))  # x^5+1 = (x+1)(x^4+x^3+x^2+x+1)

    def test_primitivity_methodical_list(self):
        for e in [(8, 4, 3, 2, 0), (9, 4, 0), (10, 3, 0), (15, 1, 0), (17, 3, 0), (19, 5, 2, 1, 0)]:
            self.assertTrue(is_primitive(poly(*e)), e)

    def test_lfsr_full_period(self):
        for e in [(5, 2, 0), (7, 3, 0), (4, 1, 0)]:
            f = poly(*e)
            n = f.bit_length() - 1
            r = LFSR(f, 1)
            seen, s0 = 0, r.state
            for i in range(1, 1 << n):
                r.step()
                if r.state == s0:
                    seen = i
                    break
            self.assertEqual(seen, (1 << n) - 1)

    def test_sg_period_matches_theory(self):
        for da, ds, fa, fs in [(5, 4, poly(5, 2, 0), poly(4, 1, 0)),
                               (5, 6, poly(5, 4, 3, 2, 0), poly(6, 1, 0)),
                               (5, 7, poly(5, 2, 0), poly(7, 3, 0))]:
            bits = ShrinkingGenerator(fa, 0b10110, fs, 0b1011).bits(20000)
            p, ok = smallest_period(bits)
            self.assertTrue(ok)
            self.assertEqual(p, theoretical_period(da, ds))

    def test_alphabet_range_and_uniformity(self):
        g = ShrinkingGenerator(poly(5, 2, 0), 0b10110, poly(7, 3, 0), 0b1011)
        seq = g.symbols(300, 10)
        self.assertTrue(all(0 <= x < 10 for x in seq))
        self.assertEqual(len(seq), 300)

    def test_chi2_matches_known_values(self):
        self.assertAlmostEqual(chi2_sf(3.841458820694124, 1), 0.05, places=6)
        self.assertAlmostEqual(chi2_sf(24.99579013972863, 15), 0.05, places=6)
        r = chi_square_uniform([0, 1] * 50, 2)
        self.assertAlmostEqual(r["chi2"], 0.0)
        r = chi_square_uniform([0] * 100, 2)
        self.assertFalse(r["ok"])


class TestPart2(unittest.TestCase):
    def test_sieve(self):
        self.assertEqual(len(SMALL_PRIMES), 303)  # pi(2000) = 303
        self.assertEqual(sieve(30), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])

    def test_rabin_miller_known(self):
        r = rng()
        for p in (2, 3, 97, 7919, 2 ** 31 - 1, 2 ** 61 - 1):
            self.assertTrue(rabin_miller(p, r), p)
        for c in (1, 4, 91, 341, 7917, 2 ** 31 + 1):
            self.assertFalse(rabin_miller(c, r, rounds=10), c)

    def test_carmichael_numbers_detected(self):
        r = rng()
        for c in (561, 1105, 1729, 2465, 2821, 6601, 8911, 10585, 15841, 29341):
            self.assertFalse(rabin_miller(c, r, rounds=10), c)

    def test_fermat_pseudoprime_341(self):
        self.assertEqual(pow(2, 340, 341), 1)  # проходит тест Ферма по основанию 2 ...
        self.assertFalse(rabin_miller(341, rng(), rounds=10))  # ... но не Рабина–Миллера

    def test_pocklington_small(self):
        F = 1009  # простое; n = 2*F*t + 1 > ... F^2 > n
        t = next(t for t in range(2, 400) if is_prime_trial(2 * F * t + 1))
        n = 2 * F * t + 1
        self.assertIsNotNone(pocklington_witness(n, F))
        comp = next(2 * F * t + 1 for t in range(2, 400) if not is_prime_trial(2 * F * t + 1))
        self.assertIsNone(pocklington_witness(comp, F))

    def test_generation_bitlength_primality_certificate(self):
        gen = Mihailescu(rng())
        for m in (24, 32, 64, 128, 256):
            n, cert = gen.generate(m, Journal())
            self.assertEqual(n.bit_length(), m)
            self.assertTrue(n & 1)
            self.assertTrue(verify_certificate(cert))
            self.assertTrue(rabin_miller(n, rng(), rounds=30))
            if m <= 32:
                self.assertTrue(is_prime_trial(n))

    def test_tampered_certificate_rejected(self):
        n, cert = Mihailescu(rng()).generate(128, Journal())
        bad = [dict(c) for c in cert]
        bad[-1]["n"] += 2
        self.assertFalse(verify_certificate(bad))
        bad = [dict(c) for c in cert]
        bad[-1]["a"] = 1  # a = 1 не является свидетелем
        self.assertFalse(verify_certificate(bad))

    def test_F_larger_than_sqrt_n(self):
        _, cert = Mihailescu(rng()).generate(200, Journal())
        for step in cert[1:]:
            self.assertGreater(step["F"] ** 2, step["n"])
            self.assertEqual(math.gcd(step["a"], step["n"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
