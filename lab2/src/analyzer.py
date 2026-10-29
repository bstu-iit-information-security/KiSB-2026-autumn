# analyzer.py
"""
Анализ корректирующей способности (расчет N2/N1 и N3/N1).
"""

import random
from errors import inject_errors
from encoder import (encode_2groups_2d, encode_3groups_2d,
                     encode_4groups_3d, encode_5groups_3d)
from decoder import (decode_2groups_2d, decode_3groups_2d,
                     decode_4groups_3d, decode_5groups_3d)


def analyze_correction(bits, encode_fn, decode_fn, i, N1=1000, seed=42):
    """
    Для ошибок кратности i выполнить N1 испытаний.
    Возвращает (N2/N1, N3/N1).
    """
    rng = random.Random(seed)
    Xn, _ = encode_fn(bits)

    N2 = 0
    N3 = 0

    for _ in range(N1):
        # 1. Вносим i ошибок
        Yn, true_pos = inject_errors(Xn, i, rng)

        # 2. Декодируем
        Yk_fixed, found_pos, identified, corrected = decode_fn(Yn)

        # 3. Считаем метрики
        if identified:
            N2 += 1
        if corrected and list(Yk_fixed) == list(bits):
            N3 += 1

    return N2 / N1, N3 / N1


def run_full_analysis(cfg):
    """Запуск полного анализа для всех конфигураций и кратностей."""
    print("\n" + "=" * 70)
    print(f" Анализ корректирующей способности (N1 = {cfg.N1} испытаний)")
    print("=" * 70)

    # Генерируем случайное слово для тестов
    rng = random.Random(cfg.seed)
    bits = [rng.randint(0, 1) for _ in range(cfg.k)]
    print(f"Тестовое слово Xk ({cfg.k} бит): {''.join(map(str, bits))}\n")

    a, b, c = cfg.k3d

    # Словарь с конфигурациями
    configs = [
        (2, "2 группы (2D)",
         lambda x: encode_2groups_2d(x, cfg.k1, cfg.k2),
         lambda y: decode_2groups_2d(y, cfg.k1, cfg.k2)),

        (3, "3 группы (2D+диаг)",
         lambda x: encode_3groups_2d(x, cfg.k1, cfg.k2),
         lambda y: decode_3groups_2d(y, cfg.k1, cfg.k2)),

        (4, "4 группы (3D)",
         lambda x: encode_4groups_3d(x, a, b, c),
         lambda y: decode_4groups_3d(y, a, b, c)),

        (5, "5 группы (3D+диаг)",
         lambda x: encode_5groups_3d(x, a, b, c),
         lambda y: decode_5groups_3d(y, a, b, c)),
    ]

    for i in cfg.error_multiplicities:
        print(f"--- Кратность ошибки i = {i} ---")
        print(f"{'Конфигурация':<20} | {'N2/N1 (обнаружено)':<20} | {'N3/N1 (исправлено)':<20}")
        print("-" * 66)

        for _, name, enc_fn, dec_fn in configs:
            p2, p3 = analyze_correction(bits, enc_fn, dec_fn, i, cfg.N1, cfg.seed)
            print(f"{name:<20} | {p2:>18.3f}   | {p3:>18.3f}")
        print()


if __name__ == "__main__":
    from config import Config

    cfg = Config()
    cfg.check()
    run_full_analysis(cfg)