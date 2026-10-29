import sys
import time
import sympy

# Добавляем текущую папку в пути поиска, чтобы импорты работали
sys.path.insert(0, '.')
from mihailescu import generate_prime_mihailescu


def run(bits_list, e=0.5):
    print(f"{'Разряд (бит)':>12} | {'Время (с)':>9} | {'F (бит)':>7} | "
          f"{'Кандидатов':>10} | {'Доказано':>8} | sympy.isprime")
    print("-" * 75)

    for b in bits_list:
        r = generate_prime_mihailescu(b, e=e, s=200)
        if r['n'] is not None:
            sp = sympy.isprime(r['n'])
            print(f"{b:>12} | {r['time']:>9.4f} | {r['F'].bit_length():>7} | "
                  f"{r['attempts']:>10} | {str(r['proven']):>8} | {sp}")
        else:
            print(f"{b:>12} | {r['time']:>9.4f} | —       | "
                  f"{r['attempts']:>10} | False    | —")


if __name__ == "__main__":
    # Проверяем генерацию чисел от 32 до 256 бит
    run([32, 64, 128, 256, 512])