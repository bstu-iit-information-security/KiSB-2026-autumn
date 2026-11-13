import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lfsr import LFSR, poly_from_exponents as P, is_primitive, is_irreducible
from primes import is_probable_prime, generate_prime, small_primes, DEFAULT_POLY
from stats import chi2_pvalue, monobit


class Lfsr(unittest.TestCase):
    def test_primitivity_variant4(self):
        self.assertTrue(is_primitive(P(7, 1, 0)))
        self.assertFalse(is_irreducible(P(7, 5, 3, 0)))       # f(1) = 0 -> делится на x+1
        self.assertFalse(is_primitive(P(7, 5, 3, 0)))
        self.assertTrue(is_primitive(P(7, 6, 5, 2, 0)))

    def test_max_period(self):
        for p in (P(7, 1, 0), P(7, 6, 5, 2, 0)):
            for seed in (1, 0x55, 0x7F):
                self.assertEqual(LFSR(p, seed).period(), 127)

    def test_reducible_period(self):
        self.assertEqual(LFSR(P(7, 5, 3, 0), 1).period(), 63)
        self.assertEqual(LFSR(P(7, 5, 3, 0), 0x7F).period(), 1)

    def test_recurrence(self):
        # f = x^7 + x + 1  =>  s[t+7] = s[t] xor s[t+1]
        s = LFSR(P(7, 1, 0), 0b0101101).bits(300)
        for t in range(293):
            self.assertEqual(s[t + 7], s[t] ^ s[t + 1])

    def test_balance(self):
        g = LFSR(P(7, 1, 0), 1)
        self.assertEqual(sum(g.bits(127)), 64)

    def test_zero_state_rejected(self):
        with self.assertRaises(ValueError):
            LFSR(P(7, 1, 0), 0)

    def test_degree19_primitive(self):
        self.assertTrue(is_primitive(DEFAULT_POLY))


class Primes(unittest.TestCase):
    def test_against_trial_division(self):
        sp = small_primes(100000)
        s = set(sp) | {2}
        for n in range(2, 100000):
            self.assertEqual(is_probable_prime(n, 5), n in s, n)

    def test_carmichael_and_strong_pseudoprime(self):
        for n in (561, 1105, 1729, 2465, 2821, 6601, 8911, 2047, 3277, 4033):
            self.assertFalse(is_probable_prime(n, 5, LFSR(DEFAULT_POLY, 777)), n)

    def test_mersenne(self):
        self.assertTrue(is_probable_prime(2**127 - 1, 5))
        self.assertFalse(is_probable_prime(2**67 - 1, 5))

    def test_generated_primes(self):
        rng = LFSR(DEFAULT_POLY, 4242)
        for bits in (16, 64, 128, 256):
            for lim in (0, 256, 2000):
                st = generate_prime(bits, rng, 5, lim)
                self.assertEqual(st.prime.bit_length(), bits)
                self.assertEqual(st.prime & 1, 1)
                self.assertEqual(st.candidates, 1 + st.rejected_sieve + st.rejected_mr)
                try:
                    import sympy
                    self.assertTrue(sympy.isprime(st.prime))
                except ImportError:
                    pass


class Stats(unittest.TestCase):
    def test_chi2(self):
        self.assertAlmostEqual(chi2_pvalue(3.841458820694124, 1), 0.05, places=4)
        self.assertAlmostEqual(chi2_pvalue(18.307038053275146, 10), 0.05, places=4)

    def test_monobit(self):
        self.assertGreater(monobit(LFSR(P(7, 1, 0), 1).bits(12700))["p"], 0.05)


if __name__ == "__main__":
    unittest.main()
