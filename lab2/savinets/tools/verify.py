"""Запустить Python-тесты, сохранить протокол и сведения о проверках."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
(ROOT / 'results').mkdir(exist_ok=True)
suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
with (ROOT / 'results/tests.txt').open('w', encoding='utf-8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
metadata = dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                skipped=len(result.skipped), successful=result.wasSuccessful(), python=sys.version,
                timestamp_utc=datetime.now(timezone.utc).isoformat())
(ROOT / 'results/validation.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print((ROOT / 'results/tests.txt').read_text(encoding='utf-8'))
raise SystemExit(0 if result.wasSuccessful() else 1)
