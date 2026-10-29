# main.py
"""
Лабораторная работа №5: итеративные коды.
Вариант 3 (k=24, 2D: 4x6, 3D: 3x4x2).
"""

import random
from config import Config
from matrix_ops import (bits_to_matrix_2d, bits_to_matrix_3d,
                        print_matrix_2d, print_matrix_3d)
from parity import (parity_2groups_2d, parity_3groups_2d,
                    parity_4groups_3d, parity_5groups_3d)
from encoder import (encode_2groups_2d, encode_3groups_2d,
                     encode_4groups_3d, encode_5groups_3d)
from decoder import (decode_2groups_2d, decode_3groups_2d,
                     decode_4groups_3d, decode_5groups_3d)
from errors import inject_errors
from analyzer import run_full_analysis


def generate_random_bits(k, seed=None):
    rng = random.Random(seed)
    return [rng.randint(0, 1) for _ in range(k)]


def print_menu():
    print("\n" + "=" * 60)
    print(" Лабораторная работа №5. Итеративные коды (вариант 10(5))")
    print("=" * 60)
    print(" 1. Показать параметры варианта")
    print(" 2. Сгенерировать Xk и вычислить паритеты")
    print(" 3. Закодировать Xk -> Xn (все группы)")
    print(" 4. Внести ошибки и декодировать")
    print(" 5. Анализ N2/N1 и N3/N1 (полный)")
    print(" 0. Выход")
    print("-" * 60)


def run_decoding_experiment(cfg, current_bits, Xn_dict, i):
    """Вспомогательная функция для пункта 4 (тест ошибок)."""
    print(f"\n--- Тестирование кратности ошибки i = {i} ---")
    rng = random.Random(cfg.seed)

    # 2 группы
    if 2 in Xn_dict:
        Xn2 = Xn_dict[2]
        Yn2, pos2 = inject_errors(Xn2, i, rng)
        Yk2, err2, ident2, corr2 = decode_2groups_2d(Yn2, cfg.k1, cfg.k2)
        print(f"[2 группы] Позиции ошибок: {pos2}")
        print(f"           Найдено декодером: {err2}")
        print(f"           Кратность идентифицирована: {ident2}")
        print(f"           Успешно исправлено: {corr2}")

    # 3 группы
    if 3 in Xn_dict:
        Xn3 = Xn_dict[3]
        Yn3, pos3 = inject_errors(Xn3, i, rng)
        Yk3, err3, ident3, corr3 = decode_3groups_2d(Yn3, cfg.k1, cfg.k2)
        print(f"[3 группы] Позиции ошибок: {pos3}")
        print(f"           Найдено декодером: {err3}")
        print(f"           Кратность идентифицирована: {ident3}")
        print(f"           Успешно исправлено: {corr3}")

    # 4 группы (3D)
    if 4 in Xn_dict:
        a, b, c = cfg.k3d
        Xn4 = Xn_dict[4]
        Yn4, pos4 = inject_errors(Xn4, i, rng)
        Yk4, err4, ident4, corr4 = decode_4groups_3d(Yn4, a, b, c)
        print(f"[4 группы] Позиции ошибок: {pos4}")
        print(f"           Найдено декодером: {err4}")
        print(f"           Кратность идентифицирована: {ident4}")
        print(f"           Успешно исправлено: {corr4}")

    # 5 группы (3D)
    if 5 in Xn_dict:
        a, b, c = cfg.k3d
        Xn5 = Xn_dict[5]
        Yn5, pos5 = inject_errors(Xn5, i, rng)
        Yk5, err5, ident5, corr5 = decode_5groups_3d(Yn5, a, b, c)
        print(f"[5 группы] Позиции ошибок: {pos5}")
        print(f"           Найдено декодером: {err5}")
        print(f"           Кратность идентифицирована: {ident5}")
        print(f"           Успешно исправлено: {corr5}")


def main():
    cfg = Config()
    cfg.check()

    current_bits = None
    Xn_dict = {}  # Сюда сохраним закодированные слова

    while True:
        print_menu()
        choice = input("Выбор: ").strip()

        if choice == "1":
            print(f"\nВариант: {cfg.variant}")
            print(f"  k  = {cfg.k} бит")
            print(f"  2D: {cfg.k1} x {cfg.k2} = {cfg.k1 * cfg.k2}")
            print(f"  3D: {cfg.k3d[0]} x {cfg.k3d[1]} x {cfg.k3d[2]} = "
                  f"{cfg.k3d[0] * cfg.k3d[1] * cfg.k3d[2]}")
            print(f"  Группы паритетов: {cfg.parity_groups}")
            print(f"  N1 = {cfg.N1}, кратности: {cfg.error_multiplicities}")

        elif choice == "2":
            current_bits = generate_random_bits(cfg.k, cfg.seed)
            print(f"\nXk ({cfg.k} бит):")
            print("  " + "".join(map(str, current_bits)))

            m = bits_to_matrix_2d(current_bits, cfg.k1, cfg.k2)
            print_matrix_2d(m, f"\nМатрица 2D {cfg.k1}x{cfg.k2}:")

            Xh, Xv, Xhv = parity_2groups_2d(m)
            print(f"\n[2 группы] Xh={Xh} Xv={Xv} Xhv={Xhv}")

            Xh3, Xv3, Xhv3, Xd3 = parity_3groups_2d(m)
            print(f"[3 группы] Xd={Xd3}")

            a, b, c = cfg.k3d
            planes = bits_to_matrix_3d(current_bits, a, b, c)
            print_matrix_3d(planes, f"\nМатрица 3D {a}x{b}x{c}:")

            Xh4, Xv4, Xz4, Xhv4 = parity_4groups_3d(planes)
            print("[4 группы] Xz (матрица) =")
            for row in Xz4:
                print("           " + " ".join(map(str, row)))

            Xh5, Xv5, Xz5, Xhv5, Xd5 = parity_5groups_3d(planes)
            print(f"[5 группы] Xd={Xd5}")

        elif choice == "3":
            if current_bits is None:
                print("\nСначала сгенерируйте Xk (пункт 2).")
                continue

            Xn2, _ = encode_2groups_2d(current_bits, cfg.k1, cfg.k2)
            Xn3, _ = encode_3groups_2d(current_bits, cfg.k1, cfg.k2)
            a, b, c = cfg.k3d
            Xn4, _ = encode_4groups_3d(current_bits, a, b, c)
            Xn5, _ = encode_5groups_3d(current_bits, a, b, c)

            Xn_dict = {2: Xn2, 3: Xn3, 4: Xn4, 5: Xn5}

            print(f"\n[2 группы] n={len(Xn2)} (r={len(Xn2) - cfg.k})")
            print(f"Xn2: {''.join(map(str, Xn2))}")

            print(f"\n[3 группы] n={len(Xn3)} (r={len(Xn3) - cfg.k})")
            print(f"Xn3: {''.join(map(str, Xn3))}")

            print(f"\n[4 группы] n={len(Xn4)} (r={len(Xn4) - cfg.k})")
            print(f"Xn4: {''.join(map(str, Xn4))}")

            print(f"\n[5 группы] n={len(Xn5)} (r={len(Xn5) - cfg.k})")
            print(f"Xn5: {''.join(map(str, Xn5))}")

        elif choice == "4":
            if not Xn_dict:
                print("\nСначала закодируйте слово (пункт 3).")
                continue

            try:
                i = int(input("Введите кратность ошибки i (1, 2, 3...): "))
            except ValueError:
                print("Некорректный ввод.")
                continue

            run_decoding_experiment(cfg, current_bits, Xn_dict, i)

        elif choice == "5":
            run_full_analysis(cfg)

        elif choice == "0":
            print("Выход.")
            break

        else:
            print("Некорректный ввод.")


if __name__ == "__main__":
    main()