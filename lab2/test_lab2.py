import random
import unittest

import hamming
import iterative


class HammingTest(unittest.TestCase):
    def test_r(self):
        self.assertEqual([hamming.calc_r(k) for k in (1, 4, 11, 16, 26, 57)], [2, 3, 4, 5, 5, 6])

    def test_matrix(self):
        for k in (4, 16, 24, 100):
            for d in (3, 4):
                H = hamming.build_matrix(k, d)
                cols = [tuple(row[j] for row in H) for j in range(len(H[0]))]
                self.assertEqual(len(set(cols)), len(cols))
                self.assertTrue(all(any(c) for c in cols))
                if d == 4:
                    self.assertTrue(all(sum(c) % 2 for c in cols))

    def test_codeword_syndrome_zero(self):
        rng = random.Random(1)
        for d in (3, 4):
            xk = [rng.randint(0, 1) for _ in range(40)]
            H = hamming.build_matrix(40, d)
            xn = xk + hamming.encode(xk, H)
            res = hamming.decode(xn, H, 40)
            self.assertEqual(res["status"], "none")

    def test_single_error_every_position(self):
        rng = random.Random(2)
        for d in (3, 4):
            xk = [rng.randint(0, 1) for _ in range(24)]
            H = hamming.build_matrix(24, d)
            xn = xk + hamming.encode(xk, H)
            for p in range(len(xn)):
                y = xn[:]
                y[p] ^= 1
                res = hamming.decode(y, H, 24)
                self.assertEqual(res["status"], "corrected")
                self.assertEqual(res["y"], xn)

    def test_double_error_extended(self):
        rng = random.Random(3)
        xk = [rng.randint(0, 1) for _ in range(24)]
        H = hamming.build_matrix(24, 4)
        xn = xk + hamming.encode(xk, H)
        for a in range(len(xn)):
            for b in range(a + 1, len(xn)):
                y = xn[:]
                y[a] ^= 1
                y[b] ^= 1
                self.assertEqual(hamming.decode(y, H, 24)["status"], "detected")

    def test_text_bits(self):
        self.assertEqual(hamming.text_to_bits("A"), [0, 1, 0, 0, 0, 0, 0, 1])


class IterativeTest(unittest.TestCase):
    def test_size(self):
        c = iterative.Code(5, 8, 1, 2)
        self.assertEqual((c.k, c.r, c.n), (40, 13, 53))

    def test_single_error_all_configs(self):
        rng = random.Random(4)
        for v in iterative.VARIANTS:
            for cfg in iterative.VARIANTS[v]:
                self.assertEqual(cfg[0] * cfg[1] * cfg[2], (16, 20, 24, 32, 40)[v - 1])
                for g in iterative.group_options(cfg[2]):
                    code = iterative.Code(*cfg, g)
                    xk = [rng.randint(0, 1) for _ in range(code.k)]
                    xn = code.encode(xk)
                    for p in range(code.n):
                        y = xn[:]
                        y[p] ^= 1
                        y2, flips, ok = code.decode(y)
                        self.assertTrue(ok)
                        self.assertEqual(y2, xn)
                        self.assertEqual(flips, [p])

    def test_no_errors(self):
        code = iterative.Code(4, 10, 1, 3)
        xn = code.encode([1, 0] * 20)
        self.assertEqual(code.decode(xn), (xn, [], True))

    def test_rectangle_not_detected(self):
        code = iterative.Code(5, 8, 1, 2)
        xn = code.encode([0] * 40)
        y = xn[:]
        for p in (code.idx(0, 1, 1), code.idx(0, 1, 3), code.idx(0, 3, 1), code.idx(0, 3, 3)):
            y[p] ^= 1
        self.assertEqual(code.failed(y), set())


if __name__ == "__main__":
    unittest.main()
