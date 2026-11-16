"""Проверка запуска программы так, как её использует студент."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "lab3.py"
KEY = "000102030405060708090a0b0c0d0e0f"
IV = "101112131415161718191a1b1c1d1e1f"


class CommandLineTests(unittest.TestCase):
    def run_lab(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              cwd=ROOT, text=True, capture_output=True)

    def test_default_demonstration(self):
        result = self.run_lab()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ECB", result.stdout)
        self.assertIn("CFB", result.stdout)
        self.assertIn("Совпадает: да", result.stdout)

    def test_hex_round_trip_for_both_modes(self):
        data = "00112233445566778899aabbccddee123456"
        for mode in ("ecb", "cfb"):
            with self.subTest(mode=mode):
                extra = ["--iv", IV] if mode == "cfb" else []
                enc = self.run_lab("encrypt", mode, KEY, data, *extra)
                self.assertEqual(enc.returncode, 0, enc.stderr)
                dec = self.run_lab("decrypt", mode, KEY, enc.stdout.strip(), *extra)
                self.assertEqual(dec.returncode, 0, dec.stderr)
                self.assertEqual(dec.stdout.strip(), data)

    def test_rejects_bad_hex_and_missing_iv(self):
        self.assertNotEqual(self.run_lab("encrypt", "ecb", KEY, "xyz").returncode, 0)
        self.assertNotEqual(self.run_lab("encrypt", "cfb", KEY, "00").returncode, 0)


if __name__ == "__main__":
    unittest.main()
