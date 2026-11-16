import argparse
import time
from Goncheryonok.primes import is_prime_miller_rabin, sieve_of_eratosthenes, generate_random_bits, bits_to_int
from Goncheryonok.sg_generator import SGGenerator
from Goncheryonok.main import POLYNOMIALS  # Берем твои примитивные многочлены


def run_prime_generator(g1_idx: int, g2_idx: int, bits_p: int, count_primes: int):
    print("=" * 60)
    print(f"Генерация {count_primes} простых чисел размером {bits_p} бит")
    print("=" * 60)

    # 1. Инициализируем SG-генератор (с фаззингом или случайным сидом)
    import random
    seed1 = random.randint(1, 65535)
    seed2 = random.randint(1, 32767)
    gen = SGGenerator(POLYNOMIALS[g1_idx], seed1, POLYNOMIALS[g2_idx], seed2)

    # 2. Готовим малые простые для фильтрации (до 2000)
    small_primes = sieve_of_eratosthenes(2000)

    stats = {"candidates": 0, "sieve_rejected": 0, "mr_rejected": 0}
    found_primes = []

    start_time = time.perf_counter()

    while len(found_primes) < count_primes:
        stats["candidates"] += 1

        # Генерируем p бит и собираем в число
        bits = generate_random_bits(gen, bits_p)
        n = bits_to_int(bits)

        # Ставим старший и младший биты в 1
        n |= (1 << (bits_p - 1))  # Старший бит
        n |= 1  # Младший бит

        # Предварительная фильтрация
        rejected_by_sieve = False
        for p in small_primes:
            if n == p:  # Если сгенерировали само малое простое
                break
            if n % p == 0:
                stats["sieve_rejected"] += 1
                rejected_by_sieve = True
                break

        if rejected_by_sieve:
            continue

        # Финальный тест Миллера-Рабина
        if is_prime_miller_rabin(n, k=5):
            found_primes.append(n)
            print(f"Найдено простое #{len(found_primes)}: {n} (hex: {hex(n)})")
        else:
            stats["mr_rejected"] += 1

    end_time = time.perf_counter()

    print("\n" + "=" * 60)
    print("Статистика")
    print("=" * 60)
    print(f"Всего сгенерировано кандидатов: {stats['candidates']}")
    print(f"Отсеяно решетом (малые делители): {stats['sieve_rejected']}")
    print(f"Отсеяно Миллером-Рабином: {stats['mr_rejected']}")
    print(f"Найдено простых: {len(found_primes)}")
    print(f"Время выполнения: {end_time - start_time:.2f} сек")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ЛР №1 Часть 2 — Генерация простых чисел")
    ap.add_argument("--g1", type=int, default=8, choices=[7, 8],
                    help="номер многочлена для G1 (рекомендуется 8)")
    ap.add_argument("--g2", type=int, default=7, choices=[7, 8],
                    help="номер многочлена для G2 (рекомендуется 7)")
    ap.add_argument("--bits", type=int, default=32, help="Разрядность числа (по умолчанию 32)")
    ap.add_argument("--count", type=int, default=5, help="Сколько простых чисел искать")
    args = ap.parse_args()

    run_prime_generator(args.g1, args.g2, args.bits, args.count)