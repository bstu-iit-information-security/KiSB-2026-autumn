import argparse
import json
import os
import platform
from pathlib import Path
from statistics import median
from time import perf_counter

from belt import H
from modes import ecb_encrypt, ctr_crypt, ctr_parallel


def measure(function, repeats):
    times = []
    for _ in range(repeats):
        started = perf_counter()
        function()
        times.append(perf_counter() - started)
    return median(times)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[4096, 65536, 262144])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if min(args.sizes) < 1 or args.workers < 1 or args.repeats < 1:
        parser.error("Размеры, количество процессов и повторов должны быть > 0.")

    key = H[128:160]
    iv = bytes.fromhex("0011223344556677")
    rows = []
    for size in args.sizes:
        data = (bytes(range(256)) * ((size + 255) // 256))[:size]
        expected = ctr_crypt(data, key, iv)
        assert ctr_parallel(data, key, iv, args.workers) == expected
        ecb_time = measure(lambda: ecb_encrypt(data, key), args.repeats)
        ctr_time = measure(lambda: ctr_crypt(data, key, iv), args.repeats)
        parallel_time = measure(
            lambda: ctr_parallel(data, key, iv, args.workers), args.repeats
        )
        row = dict(bytes=size, ecb_seconds=ecb_time, ctr_seconds=ctr_time,
                   parallel_seconds=parallel_time,
                   ctr_speedup=ctr_time / parallel_time,
                   ecb_to_parallel=ecb_time / parallel_time)
        rows.append(row)
        print(f"{size:>7} байт | ECB {ecb_time:.4f} с | CTR {ctr_time:.4f} с | "
              f"CTR ({args.workers} процесса) {parallel_time:.4f} с | "
              f"ускорение CTR {row['ctr_speedup']:.2f}", flush=True)

    result = dict(python=platform.python_version(), platform=platform.platform(),
                  logical_cpus=os.cpu_count(), workers=args.workers,
                  repeats=args.repeats, statistic="median",
                  includes_process_startup=True, rows=rows)
    output = Path(__file__).parent / "results" / "benchmark.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
