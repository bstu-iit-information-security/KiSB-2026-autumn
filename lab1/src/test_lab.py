"""Автотесты, подтверждающие корректность программ (для отчёта)."""
import math
import random
import unittest
 
from fibonacci import FibonacciGenerator, find_period
from primes import generate_prime, miller_rabin, mod_pow, sieve
from stats import chi2_sf, frequency_test
 
 
class TestFibonacci(unittest.TestCase):
    def test_recurrence(self):
        g = FibonacciGenerator(5, 2, seed=[1, 0, 1, 1, 0])
        x = [1, 0, 1, 1, 0] + g.sequence(30)
        for t in range(5, len(x)):
            self.assertEqual(x[t], x[t - 5] ^ x[t - 2])
 
    def test_max_period(self):
        for r, s in [(3, 1), (4, 1), (5, 2), (7, 1), (9, 4), (10, 3), (15, 1), (17, 3)]:
            self.assertEqual(find_period(r, s), 2 ** r - 1, (r, s))
 
    def test_non_max_period(self):
        self.assertLess(find_period(10, 5), 2 ** 10 - 1)       # x^10+x^5+1 не примитивен
        self.assertEqual(find_period(10, 3, seed=0), 1)        # нулевое состояние
 
    def test_periodicity_and_balance(self):
        r, s = 10, 3
        T = find_period(r, s)
        seq = FibonacciGenerator(r, s).sequence(2 * T)
        self.assertEqual(seq[:T], seq[T:])
        self.assertEqual(sum(seq[:T]), 2 ** (r - 1))           # ровно 2^(r-1) единиц за период
 
    def test_alphabet(self):
        seq = FibonacciGenerator(7, 1, k=3).sequence(500)
        self.assertTrue(all(0 <= x < 8 for x in seq))
 
    def test_stat_good_vs_bad(self):
        good = FibonacciGenerator(17, 3).sequence(20000)
        bad = FibonacciGenerator(10, 3, seed=0).sequence(20000)
        self.assertTrue(frequency_test(good, 2).passed)
        self.assertFalse(frequency_test(bad, 2).passed)
 
 
class TestStatsMath(unittest.TestCase):
    def test_chi2_sf(self):
        self.assertAlmostEqual(chi2_sf(3.841, 1), 0.05, places=3)
        self.assertAlmostEqual(chi2_sf(9.488, 4), 0.05, places=3)
        self.assertAlmostEqual(chi2_sf(18.307, 10), 0.05, places=3)
 
 
class TestPrimes(unittest.TestCase):
    def test_mod_pow(self):
        rnd = random.Random(1)
        for _ in range(200):
            b, e, m = rnd.randrange(1, 10 ** 9), rnd.randrange(0, 10 ** 6), rnd.randrange(2, 10 ** 9)
            self.assertEqual(mod_pow(b, e, m), pow(b, e, m))
 
    def test_sieve(self):
        self.assertEqual(len(sieve(256)), 54)
        self.assertEqual(len(sieve(2000)), 303)
 
    def test_miller_rabin_vs_bruteforce(self):
        primes = set(sieve(5000))
        for n in range(2, 5000):
            self.assertEqual(miller_rabin(n, rounds=20), n in primes, n)
 
    def test_carmichael(self):
        for n in (561, 1105, 1729, 2465, 2821, 6601, 8911):
            self.assertFalse(miller_rabin(n, rounds=10), n)
 
    def test_big_numbers(self):
        self.assertTrue(miller_rabin(2 ** 127 - 1, rounds=10))
        self.assertTrue(miller_rabin(2 ** 89 - 1, rounds=10))
        self.assertFalse(miller_rabin(2 ** 128 + 1, rounds=10))
 
    def test_generate_prime(self):
        rng = FibonacciGenerator(127, 1, seed=0xBEEF)
        rng.skip(500)
        for limit in (0, 256, 2000):
            n, log = generate_prime(32, rng, small_limit=limit)
            self.assertEqual(n.bit_length(), 32)
            self.assertEqual(n % 2, 1)
            self.assertTrue(all(n % d for d in range(2, math.isqrt(n) + 1)))   # перебор делителей
            self.assertEqual(log.candidates, log.rejected_small + log.rejected_mr + 1)
 
    def test_generate_prime_sequential(self):
        rng = FibonacciGenerator(127, 1, seed=0xF00D)
        rng.skip(500)
        n, _ = generate_prime(128, rng, sequential=True)
        self.assertEqual(n.bit_length(), 128)
        self.assertTrue(miller_rabin(n, rounds=30))
 
 
if __name__ == "__main__":
    unittest.main()
 
