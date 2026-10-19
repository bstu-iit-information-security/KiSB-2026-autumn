"""Run tests and save machine-readable and human-readable validation records."""
from pathlib import Path
from datetime import datetime, timezone
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
(ROOT/'results').mkdir(exist_ok=True)
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
with (ROOT/'results/tests.txt').open('w') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
record={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'skipped':len(result.skipped),'successful':result.wasSuccessful(),'python':sys.version,
        'timestamp_utc':datetime.now(timezone.utc).isoformat()}
(ROOT/'results/validation.json').write_text(json.dumps(record,indent=2)+'\n')
print((ROOT/'results/tests.txt').read_text())
raise SystemExit(0 if result.wasSuccessful() else 1)
