"""
Модуль вероятностного теста простоты Леманна (Lehmann primality test).

Теория (раздел 6.6 методических указаний):
  Для проверки нечетного числа n:
  1. Выбирается случайное число a < n.
  2. Вычисляется t = a^((n - 1) / 2) mod n.
  3. Если t != 1 и t != -1 (т.е. t != n - 1 mod n), то число n составное.
  4. Если t == 1 или t == -1, вероятность ошибки не более 1/2.
  При повторении проверки k раз:
  Если результат вычислений равен 1 или -1, но не всегда равен 1
  (для хотя бы одного a получено -1), то n — простое число с вероятностью ошибки <= (1/2)^k.
"""

import math
import random
from typing import Tuple, List, Dict, Any, Optional


def lehmann_test(
    n: int,
    k: int = 15,
    rng: Optional[random.Random] = None
) -> bool:
    """
    Быстрый вероятностный тест Леманна.
    Возвращает True, если n вероятно простое, и False, если составное.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    if rng is None:
        rng = random.Random()

    exp = (n - 1) // 2
    has_minus_one = False

    for _ in range(k):
        a = rng.randint(2, n - 2)
        # Если a и n имеют общий делитель, то n заведомо составное
        if math.gcd(a, n) > 1:
            return False

        t = pow(a, exp, n)

        # Проверка условия t == +1 или t == -1 (mod n)
        if t != 1 and t != (n - 1):
            return False

        if t == (n - 1):
            has_minus_one = True

    # Для простых чисел при k >= 10 вероятность не встретить -1 крайне мала: (1/2)^k.
    # Если же -1 ни разу не встретилось, число отбраковывается согласно методичке:
    # "не всегда равен 1" (устранение ложных срабатываний на псевдопростых числах).
    return has_minus_one if k >= 5 else True


def lehmann_test_detailed(
    n: int,
    k: int = 15,
    rng: Optional[random.Random] = None
) -> Dict[str, Any]:
    """
    Детальный тест Леманна с протоколированием каждого раунда
    (используется для демонстрации и отчета).
    """
    if n < 2:
        return {"is_prime": False, "reason": "n < 2", "rounds": []}
    if n in (2, 3):
        return {"is_prime": True, "reason": "n in {2, 3}", "rounds": []}
    if n % 2 == 0:
        return {"is_prime": False, "reason": "Четное число > 2", "rounds": []}

    if rng is None:
        rng = random.Random()

    exp = (n - 1) // 2
    rounds_log: List[Dict[str, Any]] = []
    has_minus_one = False

    for r in range(1, k + 1):
        a = rng.randint(2, n - 2)
        g = math.gcd(a, n)
        if g > 1:
            rounds_log.append({
                "round": r,
                "a": a,
                "gcd": g,
                "t": None,
                "verdict": f"НОД({a}, {n}) = {g} > 1 -> СОСТАВНОЕ"
            })
            return {
                "is_prime": False,
                "reason": f"Найден нетривиальный делитель {g}",
                "rounds": rounds_log
            }

        t = pow(a, exp, n)
        t_repr = "+1" if t == 1 else ("-1" if t == (n - 1) else f"{t} (mod {n})")

        if t != 1 and t != (n - 1):
            rounds_log.append({
                "round": r,
                "a": a,
                "gcd": 1,
                "t": t_repr,
                "verdict": f"t = {t} != ±1 -> СОСТАВНОЕ"
            })
            return {
                "is_prime": False,
                "reason": f"a^((n-1)/2) mod n != ±1 на раунде {r}",
                "rounds": rounds_log
            }

        if t == (n - 1):
            has_minus_one = True

        rounds_log.append({
            "round": r,
            "a": a,
            "gcd": 1,
            "t": t_repr,
            "verdict": "OK (±1)"
        })

    if k >= 5 and not has_minus_one:
        return {
            "is_prime": False,
            "reason": f"Все {k} раундов дали t = +1 (отсутствует свидетель -1)",
            "rounds": rounds_log
        }

    err_prob = 1.0 / (2 ** k)
    return {
        "is_prime": True,
        "reason": f"Успешно пройдено {k} раундов (вероятность ошибки <= {err_prob:.2e})",
        "rounds": rounds_log,
        "rounds_passed": k,
        "error_probability": err_prob
    }

