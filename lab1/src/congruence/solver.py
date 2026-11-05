"""
Модуль решения линейных сравнений первой степени ax = b (mod m).
Контрольный вопрос 12 (Вариант 2): 5x = 3 (mod 12).

Решение тремя способами:
  а) Алгоритм Евклида;
  б) Расширенный алгоритм Евклида (EEA);
  в) Метод Эйлера (с использованием теоремы Эйлера).
"""

import math
from typing import Dict, Any, List, Tuple


def euler_phi(n: int) -> int:
    """Вычисление функции Эйлера phi(n)."""
    result = n
    p = 2
    temp = n
    while p * p <= temp:
        if temp % p == 0:
            while temp % p == 0:
                temp //= p
            result -= result // p
        p += 1
    if temp > 1:
        result -= result // temp
    return result


def solve_congruence_detailed(a: int, b: int, m: int) -> Dict[str, Any]:
    """
    Подробное решение линейного сравнения ax = b (mod m) тремя методами.
    Возвращает словарь с пошаговыми протоколами каждого метода.
    """
    g = math.gcd(a, m)
    if b % g != 0:
        return {
            "has_solution": False,
            "reason": f"НОД({a}, {m}) = {g} не делит {b}. Сравнение не имеет решений."
        }

    # Редуцируем сравнение, если g > 1
    a_red, b_red, m_red = a // g, b // g, m // g

    # 1. Алгоритм Евклида (деление с остатком)
    euclid_steps: List[Dict[str, int]] = []
    r0, r1 = m_red, a_red
    while r1 != 0:
        q = r0 // r1
        rem = r0 % r1
        euclid_steps.append({"r0": r0, "q": q, "r1": r1, "rem": rem})
        r0, r1 = r1, rem

    # 2. Расширенный алгоритм Евклида (EEA)
    # Ищем u, v такие, что u * m_red + v * a_red = 1
    eea_table: List[Dict[str, int]] = []
    r_prev, r_curr = m_red, a_red
    u0, u1 = 1, 0
    v0, v1 = 0, 1

    eea_table.append({"step": 0, "r": r_prev, "q": 0, "u": u0, "v": v0})
    eea_table.append({"step": 1, "r": r_curr, "q": 0, "u": u1, "v": v1})

    step_idx = 2
    while r_curr != 0:
        q = r_prev // r_curr
        r_next = r_prev % r_curr
        u_next = u0 - q * u1
        v_next = v0 - q * v1

        eea_table.append({"step": step_idx, "r": r_next, "q": q, "u": u_next, "v": v_next})

        r_prev, r_curr = r_curr, r_next
        u0, u1 = u1, u_next
        v0, v1 = v1, v_next
        step_idx += 1

    # Обратный элемент a_red^(-1) mod m_red:
    v_bezout = v0
    inv_a_eea = v_bezout % m_red
    x0_eea = (b_red * inv_a_eea) % m_red

    # 3. Метод Эйлера
    # По теореме Эйлера: a^phi(m) = 1 (mod m) => a^(-1) = a^(phi(m) - 1) (mod m)
    phi_m = euler_phi(m_red)
    inv_a_euler = pow(a_red, phi_m - 1, m_red)
    x0_euler = (b_red * inv_a_euler) % m_red

    # Все решения в исходном модуле m
    all_solutions = [(x0_eea + i * m_red) % m for i in range(g)]
    all_solutions.sort()

    # Проверка
    is_valid = ((a * x0_eea) % m) == (b % m)

    return {
        "has_solution": True,
        "a": a,
        "b": b,
        "m": m,
        "gcd": g,
        "num_solutions": g,
        "reduced": (a_red, b_red, m_red),
        "euclid_steps": euclid_steps,
        "eea_table": eea_table,
        "v_bezout": v_bezout,
        "inv_a": inv_a_eea,
        "phi_m": phi_m,
        "inv_a_euler": inv_a_euler,
        "solution_base": x0_eea,
        "all_solutions": all_solutions,
        "is_valid": is_valid
    }


def print_congruence_solution_variant2() -> None:
    """Вывод подробного решения контрольного сравнения Варианта 2: 5x = 3 (mod 12)."""
    res = solve_congruence_detailed(5, 3, 12)

    print("\n" + "=" * 75)
    print("КОНТРОЛЬНОЕ ЗАДАНИЕ №12 (Вариант 2): Решить сравнение 5x ≡ 3 (mod 12)")
    print("=" * 75)

    print(f"\nПараметры: a = 5, b = 3, m = 12.")
    print(f"НОД(5, 12) = {res['gcd']}. Так как НОД(5, 12) = 1 делит 3, сравнение имеет 1 решение.")

    print("\n[a] Способ 1: Алгоритм Евклида (деление с остатком):")
    for s in res["euclid_steps"]:
        print(f"    {s['r0']} = {s['q']} * {s['r1']} + {s['rem']}")
    print("    Обратный ход (выражение 1 через остатки):")
    print("    1 = 5 - 2 * 2")
    print("    1 = 5 - 2 * (12 - 2 * 5) = 5 * 5 - 2 * 12")
    print("    Отсюда: 5 * 5 ≡ 1 (mod 12) => 5^(-1) ≡ 5 (mod 12).")
    print(f"    Умножая обе части сравнения на 5: x ≡ 3 * 5 = 15 ≡ {res['solution_base']} (mod 12).")

    print("\n[б] Способ 2: Расширенный алгоритм Евклида (EEA):")
    print("    Линейная комбинация Безу: u * 12 + v * 5 = 1")
    print(f"    Найденный коэффициент Безу при 5: v = {res['v_bezout']}")
    print(f"    Обратный элемент: 5^(-1) ≡ {res['v_bezout']} ≡ {res['inv_a']} (mod 12)")
    print(f"    Решение: x ≡ (3 * {res['inv_a']}) mod 12 = {res['solution_base']}")

    print("\n[в] Способ 3: Метод Эйлера (теорема Эйлера):")
    print(f"    Факторизация модуля: 12 = 2^2 * 3")
    print(f"    Функция Эйлера: phi(12) = 12 * (1 - 1/2) * (1 - 1/3) = {res['phi_m']}")
    print("    Взаимно простые с 12 вычеты: {1, 5, 7, 11}")
    print(f"    По теореме Эйлера: 5^phi(12) ≡ 5^4 ≡ 1 (mod 12)")
    print(f"    Обратный элемент: 5^(-1) ≡ 5^(phi(12) - 1) = 5^3 = 125 ≡ {res['inv_a_euler']} (mod 12)")
    print(f"    Решение: x ≡ (3 * 5^3) mod 12 = (3 * {res['inv_a_euler']}) mod 12 = {res['solution_base']}")

    print("\n[Проверка]:")
    check_val = (5 * res['solution_base']) % 12
    print(f"    Подставляем x = {res['solution_base']} в левую часть:")
    print(f"    5 * {res['solution_base']} = {5 * res['solution_base']} ≡ {check_val} (mod 12)")
    print(f"    {check_val} ≡ 3 (mod 12) — РАВЕНСТВО ВЕРНО! Решение корректно.")

