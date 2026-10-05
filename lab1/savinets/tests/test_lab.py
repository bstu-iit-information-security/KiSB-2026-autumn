import csv
import io
import math
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from lab1 import (Parameters, Generator, cycle, statistics, perfect_power, multiply,
                      polynomial_congruence, aks, candidate, generate, trial_prime, MAX_R)

ROOT = Path(__file__).resolve().parents[1]


class GeneratorTests(unittest.TestCase):
    def test_known_sequences(self):
        self.assertEqual(list(Generator().sequence(12)), [1,2,3,4,5,6,7,8,9,0,1,2])
        self.assertEqual(list(Generator(Parameters(5,2,0,1)).sequence(8)), [7,9,3,1,7,9,3,1])

    def test_all_cycles_independent_floyd(self):
        maxima = [0, 0]
        for d in range(1, 10):
            for a in range(10):
                for c in range(10):
                    for seed in range(10):
                        def step(x):
                            return (d*x*x+a*x+c) % 10
                        slow, fast = step(seed), step(step(seed))
                        while slow != fast:
                            slow, fast = step(slow), step(step(fast))
                        slow, transient = seed, 0
                        while slow != fast:
                            slow, fast = step(slow), step(fast)
                            transient += 1
                        period, fast = 1, step(slow)
                        while slow != fast:
                            fast = step(fast)
                            period += 1
                        got = cycle(Parameters(d,a,c,seed))
                        self.assertEqual((got.transient,got.period),(transient,period),(d,a,c,seed))
                        maxima[c != 0] = max(maxima[c != 0],period)
        self.assertEqual(maxima,[4,10])

    def test_statistics(self):
        s = statistics(Parameters(),10000)
        self.assertEqual(s.counts,[1000]*10)
        self.assertEqual(s.chi_square,0)
        self.assertAlmostEqual(s.entropy,math.log2(10))
        self.assertEqual(sum(s.pairs),9999)
        self.assertGreater(s.pair_chi_square,80000)
        self.assertIsNone(statistics(Parameters(5,2,0,0),100).serial_correlation)
        self.assertEqual(statistics(Parameters(),1).counts[1],1)
        self.assertEqual(list(Generator().sequence(0)),[])

    def test_invalid_inputs(self):
        for args in [(0,6,1,0),(10,6,1,0),(5,-1,1,0),(5,6,1,10),(5.0,6,1,0)]:
            with self.assertRaises(ValueError): Parameters(*args)
        for length in (-1,0,1.5):
            with self.assertRaises(ValueError): statistics(Parameters(),length)
        with self.assertRaises(ValueError): list(Generator().sequence(-1))


class PolynomialTests(unittest.TestCase):
    @staticmethod
    def reference(left,right,n):
        r = len(left)
        out = [0]*r
        for i,x in enumerate(left):
            for j,y in enumerate(right):
                out[(i+j)%r] = (out[(i+j)%r]+x*y)%n
        return out

    def test_packed_against_naive(self):
        rng = random.Random(11011)
        for n in (2,15,97,65537,4294967295):
            for r in (2,3,7,31,61):
                for _ in range(4):
                    left = [rng.randrange(n) for _ in range(r)]
                    right = [rng.randrange(n) for _ in range(r)]
                    self.assertEqual(multiply(left,right,n),self.reference(left,right,n))

    def test_largest_ring_no_carry(self):
        n = 4294967295
        self.assertEqual(multiply([n-1]*MAX_R,[n-1]*MAX_R,n),[MAX_R]*MAX_R)

    def test_polynomial_vs_binomial(self):
        # Independent expansion of (X+a)^n using exact binomial coefficients.
        for n in range(2,25):
            for r in (2,3,7):
                for a in (1,2,5):
                    expected = [0]*r
                    for k in range(n+1):
                        expected[k%r] = (expected[k%r]+math.comb(n,k)*a**(n-k))%n
                    rhs = [0]*r
                    rhs[0] = a%n
                    rhs[n%r] = (rhs[n%r]+1)%n
                    self.assertEqual(polynomial_congruence(n,r,a),expected==rhs,(n,r,a))

    def test_invalid_polynomials(self):
        for left,right,n in [([1],[1],3),([1,0],[1],3),([1,0],[1,0],1),([-1,0],[1,0],3),([3,0],[1,0],3)]:
            with self.assertRaises(ValueError): multiply(left,right,n)
        with self.assertRaises(ValueError): polynomial_congruence(1,7,1)


class PrimalityTests(unittest.TestCase):
    def test_perfect_powers(self):
        for n in (4,8,9,25,64,81,125,65536,2147483648,4294836225):
            self.assertTrue(perfect_power(n),n)
        for n in (0,1,2,3,15,17,63,65,4294967295):
            self.assertFalse(perfect_power(n),n)

    def test_aks_against_independent_sieve(self):
        sieve = [True]*301
        sieve[0]=sieve[1]=False
        for p in range(2,18):
            if sieve[p]:
                for composite in range(p*p,301,p): sieve[composite]=False
        for n in range(301):
            self.assertEqual(aks(n).verdict,'prime' if sieve[n] else 'composite',n)

    def test_pseudoprimes_and_boundary(self):
        for n in (341,561,1105,1729,2465,2821,6601,4294967295):
            self.assertEqual(aks(n).verdict,'composite',n)

    def test_polynomial_witness_and_primes(self):
        result = aks(1022117)  # 1009*1013: factors exceed the chosen r.
        self.assertEqual(result.reason,'polynomial_witness')
        self.assertGreater(result.checks,0)
        for n in (997,1009):
            result=aks(n)
            self.assertEqual(result.verdict,'prime')
            self.assertGreater(result.checks,0)

    def test_capacity_and_invalid_numbers(self):
        self.assertEqual(aks(997,2).verdict,'capacity_exceeded')
        for n in (-1,1<<32,1.5,True):
            with self.assertRaises(ValueError): aks(n)
        for capacity in (0,MAX_R+1):
            with self.assertRaises(ValueError): aks(17,capacity)


class GenerationTests(unittest.TestCase):
    def test_all_bit_lengths_and_seeds(self):
        for bits in range(2,33):
            for seed in range(10):
                n=candidate(Generator(Parameters(seed=seed)),bits)
                self.assertEqual(n.bit_length(),bits)
                self.assertEqual(n%2,1)

    def test_sieve_preserves_prime(self):
        for bits in (2,3,4,8):
            plain=generate(Parameters(),bits,0)
            sieved=generate(Parameters(),bits,2000)
            self.assertTrue(plain.found and sieved.found)
            self.assertEqual(plain.prime,sieved.prime)
            self.assertTrue(trial_prime(plain.prime))
            self.assertEqual(plain.candidates,sieved.candidates)
            self.assertEqual(sieved.candidates,sieved.sieve_rejected+sieved.aks_rejected+1)

    def test_wrap_and_limit(self):
        self.assertFalse(generate(Parameters(),8,256,1).found)
        result=generate(Parameters(seed=3),4)
        self.assertEqual((result.start,result.prime,result.candidates),(15,11,3))

    def test_candidate_log(self):
        output=io.StringIO()
        result=generate(Parameters(),8,256,log=output)
        rows=list(csv.DictReader(io.StringIO(output.getvalue())))
        self.assertEqual(len(rows),result.candidates)
        self.assertEqual(rows[0]['candidate'],'143')
        self.assertEqual(rows[0]['divisor'],'11')
        self.assertEqual(rows[-1]['status'],'prime')
        self.assertEqual(rows[-1]['candidate'],'149')
        self.assertTrue(all(float(row['candidate_ms'])>=0 for row in rows))

    def test_invalid_generation(self):
        for bits in (1,33):
            with self.assertRaises(ValueError): generate(Parameters(),bits)
        with self.assertRaises(ValueError): generate(Parameters(),8,2001)
        with self.assertRaises(ValueError): generate(Parameters(),8,256,0)


class CliTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'lab1.py'),*args],cwd=ROOT,capture_output=True,text=True,timeout=30)

    def test_errors(self):
        for args in [('check','-1'),('check','4294967296'),('check','12x'),('check',''),('check','17','extra'),
                     ('generate','1'),('generate','33'),('generate','8','10'),('generate','8','0','2001'),
                     ('generate','8','0','256','0'),('stats','0'),('sequence','10','0','6','1','0'),
                     ('sequence','10','5'),('unknown','3')]:
            self.assertEqual(self.run_cli(*args).returncode,2,args)

    def test_commands(self):
        self.assertEqual(self.run_cli('--help').returncode,0)
        self.assertEqual(self.run_cli('sequence','12').stdout.split(),list('123456789012'))
        self.assertIn('verdict=prime',self.run_cli('check','97').stdout)
        self.assertEqual(self.run_cli('generate','8','0','256','1').returncode,5)

    def test_standalone_without_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            script = target / 'lab1.py'
            shutil.copy2(ROOT / 'lab1.py', script)
            other_cwd = target / 'other'
            other_cwd.mkdir()
            result = subprocess.run([sys.executable, str(script)], cwd=other_cwd,
                                    capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Лабораторная выполнена.', result.stdout)
            self.assertIn('n=997 verdict=prime', result.stdout)
            self.assertIn('n=1001 verdict=composite', result.stdout)
            output = target / 'results/latest_run'
            self.assertTrue((output / 'prime_generation.csv').is_file())
            with (output / 'period_search.csv').open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 9000)
            self.assertFalse((other_cwd / 'results').exists())


if __name__=='__main__':
    unittest.main()
