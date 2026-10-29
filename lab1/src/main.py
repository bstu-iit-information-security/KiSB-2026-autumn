import sys
import os
import subprocess

# Чтобы импорты работали из любой папки
sys.path.insert(0, 'part1_generators')
sys.path.insert(0, 'part2_primes')


def run_script(path):
    """Вспомогательная функция для запуска скриптов."""
    try:
        subprocess.run([sys.executable, path], check=True)
    except Exception as e:
        print(f"Ошибка при запуске {path}: {e}")


def main_menu():
    while True:
        print("\n" + "=" * 50)
        print(" ЛАБОРАТОРНАЯ РАБОТА №1 — Вариант 10")
        print("=" * 50)
        print("--- ЧАСТЬ 1: Генераторы (SG) ---")
        print("1. Проверить примитивность многочленов f1, f2, f3")
        print("2. Тест LFSR (проверка периода 31)")
        print("3. Сгенерировать SG-последовательность (первые 50 бит)")
        print("4. Проверить максимальный период SG-генератора (1984)")
        print("5. Запустить статистические тесты")
        print("6. Построить графики для отчета")
        print("\n--- ЧАСТЬ 2: Тесты простоты ---")
        print("7. Сгенерировать доказуемо простые числа (Михалеску, e=1/2)")
        print("0. Выход")
        print("=" * 50)

        choice = input("Выберите действие (0-7): ").strip()

        if choice == '1':
            run_script('part1_generators/check_polys.py')
        elif choice == '2':
            run_script('part1_generators/test_lfsr.py')
        elif choice == '3':
            run_script('part1_generators/test_shrinking.py')
        elif choice == '4':
            run_script('part1_generators/find_period.py')
        elif choice == '5':
            run_script('part1_generators/test_stats.py')
        elif choice == '6':
            run_script('part1_generators/plot_results.py')
            print("Графики сохранены в папке report/plots/")
        elif choice == '7':
            run_script('part2_primes/run_experiment.py')
        elif choice == '0':
            print("Выход...")
            break
        else:
            print("Неверный ввод, попробуйте снова.")


if __name__ == "__main__":
    main_menu()
    #python main.py
