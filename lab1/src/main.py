from __future__ import annotations
 
import subprocess
import sys
 
from experiments import run_all_experiments
from fibonacci import FibonacciGenerator, find_period, search_periods, theoretical_max_period
from primes import generate_prime, miller_rabin
from stats import frequencies, run_all
 
 
def ask(prompt: str, default, cast=int):
    raw = input(f"{prompt} [{default}]: ").strip()
    return default if raw == "" else cast(raw)
 
 
def menu_sequence() -> None:
    r = ask("r", 10)
    s = ask("s (s < r)", 3)
    k = ask("k (размер алфавита N = 2^k, для варианта k=1)", 1)
    length = ask("длина последовательности", 64)
    gen = FibonacciGenerator(r, s, k)
    seq = gen.sequence(length)
    shown = "".join(map(str, seq)) if k == 1 else " ".join(map(str, seq))
    print(f"{gen}\nПоследовательность ({min(length, 200)} из {length} элементов):")
    print(shown[:400])
    print("Частоты символов:", frequencies(seq, gen.N))
 
 
def menu_period() -> None:
    r = ask("r", 10)
    res = search_periods(r)
    print(f"Теоретический максимум: {theoretical_max_period(r)}")
    for s, t in res:
        print(f"  s={s:>2}: T={t}{'  <- максимум' if t == 2 ** r - 1 else ''}")
 
 
def menu_stats() -> None:
    r = ask("r", 17)
    s = ask("s", 3)
    length = ask("длина последовательности", 20000)
    gen = FibonacciGenerator(r, s)
    seq = gen.sequence(length)
    print(f"{gen}, длина {length}, частоты {frequencies(seq, gen.N)}")
    for res in run_all(seq, gen.N):
        print(" ", res)
 
 
def menu_prime() -> None:
    bits = ask("разрядность p (бит, >= 16)", 256)
    limit = ask("просеивать малыми простыми < (0 - не просеивать, 256 или 2000)", 2000)
    seq_mode = ask("последовательный перебор вместо случайных кандидатов? (0/1)", 0) == 1
    gen = FibonacciGenerator(127, 1, 1, seed=int.from_bytes(__import__("os").urandom(16), "big") | 1)
    gen.skip(500)
    n, log = generate_prime(bits, gen, small_limit=limit, sequential=seq_mode)
    print("\nПростое число:\n", n)
    print("\nЛог:\n" + log.summary())
 
 
def menu_check() -> None:
    n = ask("число n", 561)
    rounds = ask("число раундов", 5)
    print("вероятно простое" if miller_rabin(n, rounds) else "составное")
 
 
def menu_tests() -> None:
    subprocess.run([sys.executable, "-m", "unittest", "-v", "test_lab"])
 
 
ITEMS = [
    ("Часть 1: сгенерировать последовательность", menu_sequence),
    ("Часть 1: найти периоды / подобрать параметры", menu_period),
    ("Часть 1: статистические тесты равномерности", menu_stats),
    ("Часть 2: сгенерировать простое число (с логом)", menu_prime),
    ("Часть 2: проверить число тестом Рабина-Миллера", menu_check),
    ("Отчёт: запустить все эксперименты (графики и таблицы)", run_all_experiments),
    ("Отчёт: запустить автотесты корректности", menu_tests),
]
 
 
def main() -> None:
    while True:
        print("\n=== Лабораторная работа №1 ===")
        for i, (title, _) in enumerate(ITEMS, 1):
            print(f"{i}. {title}")
        print("0. Выход")
        choice = input("Выбор: ").strip()
        if choice == "0":
            break
        if choice.isdigit() and 1 <= int(choice) <= len(ITEMS):
            try:
                ITEMS[int(choice) - 1][1]()
            except (ValueError, KeyboardInterrupt) as exc:
                print("Ошибка ввода:", exc)
        else:
            print("Неверный пункт меню")
 
 
if __name__ == "__main__":
    main()
 
