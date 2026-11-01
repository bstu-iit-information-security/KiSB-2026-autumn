
##Запуск:
##    python -m src.main --check-primitive
##    python -m src.main --g1 2 --g2 3 --seed1 1 --seed2 1 --bits 100000


import argparse
import time

from src.lfsr import is_primitive, poly_degree
from src.sg_generator import SGGenerator
from src.stats import monobit_test, block_test, chi2_critical, runs_test


POLYNOMIALS = {
    1: 0b10001111,   # x^7 + x^3 + x^2 + x + 1
    2: 0b10000011,   # x^7 + x + 1
    3: 0b10001001,   # x^7 + x^3 + 1
}


def check_primitive() -> None:
    print("=" * 60)
    print("Проверка примитивности многочленов (вариант 2)")
    print("=" * 60)
    for idx, poly in POLYNOMIALS.items():
        n = poly_degree(poly)
        prim = is_primitive(poly)
        print(f"f{idx}(x), степень {n}, маска 0b{poly:b} — "
              f"{'ПРИМИТИВЕН' if prim else 'не примитивен'}")
    print()


def run_sg(g1_idx: int, g2_idx: int, seed1: int, seed2: int,
           bits_count: int) -> dict:
    poly1 = POLYNOMIALS[g1_idx]
    poly2 = POLYNOMIALS[g2_idx]
    gen = SGGenerator(poly1, seed1, poly2, seed2)

    print(f"G1: f{g1_idx} = 0b{poly1:b}, seed = {seed1}, "
          f"период LFSR = {gen._g1.period}")
    print(f"G2: f{g2_idx} = 0b{poly2:b}, seed = {seed2}, "
          f"период LFSR = {gen._g2.period}")
    try:
        print(f"Теоретический период SG: {gen.theoretical_period}")
    except ValueError as e:
        print(f"⚠ {e}")

    print(f"\nГенерация {bits_count} бит...")
    t0 = time.perf_counter()
    bits = gen.next_bits(bits_count)
    dt = time.perf_counter() - t0
    print(f"Сгенерировано за {dt:.4f} с ({bits_count / dt / 1000:.1f} кбит/с)")

    print("\n" + "=" * 60)
    print("Статистические тесты")
    print("=" * 60)

    p, z = monobit_test(bits)
    print(f"Частотный: доля единиц = {p:.6f}, z = {z:.4f} "
          f"(|z| < 1.96 → H0 не отвергается)")

    r = runs_test(bits)
    print(f"Серийный: runs = {r['runs']}, expected = {r['expected']:.1f}, "
          f"z = {r['z']:.4f}")

    for k in (4, 8):
        try:
            chi2 = block_test(bits, k)
            df = (1 << k) - 1
            crit = chi2_critical(df)
            verdict = "OK" if chi2 < crit else "ОТКЛОНЕНО"
            print(f"Блочный k={k}: χ² = {chi2:.2f}, "
                  f"крит. = {crit:.2f} (df={df}) → {verdict}")
        except ValueError as e:
            print(f"Блочный k={k}: {e}")

    return {"p": p, "z": z, "runs": r["runs"], "bits": bits_count}


def main():
    ap = argparse.ArgumentParser(description="ЛР №1, вариант 2 — SG-генератор")
    ap.add_argument("--check-primitive", action="store_true",
                    help="проверить примитивность многочленов варианта")
    ap.add_argument("--g1", type=int, default=2, choices=[1, 2, 3],
                    help="номер многочлена для G1 (по умолчанию 2)")
    ap.add_argument("--g2", type=int, default=3, choices=[1, 2, 3],
                    help="номер многочлена для G2 (по умолчанию 3)")
    ap.add_argument("--seed1", type=int, default=1)
    ap.add_argument("--seed2", type=int, default=1)
    ap.add_argument("--bits", type=int, default=100_000)
    args = ap.parse_args()

    if args.check_primitive:
        check_primitive()
        return

    check_primitive()
    run_sg(args.g1, args.g2, args.seed1, args.seed2, args.bits)


if __name__ == "__main__":
    main()