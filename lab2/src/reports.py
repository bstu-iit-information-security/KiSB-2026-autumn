"""
Формирование текстовых отчётов: демонстрация кодирования/декодирования
(слова X_k, X_r, X_n, Y_n, Y_r, Y_r', синдром S, вектор ошибки E_n - по п. 7
практического задания ЛР №4) и таблицы результатов экспериментов.
Позиции в выводе нумеруются с 1, как в методичке (e_1, e_2, ..., e_n).
"""
from __future__ import annotations

import random

from .bits import bit_str, bits_to_int, text_to_bits
from .experiments import error_table
from .hamming import HammingCode, format_matrix, min_check_bits
from .iterative import VARIANT1_CONFIGS, IterativeCode, IterativeConfig


def _positions(rng: random.Random, n: int, count: int) -> list[int]:
    return sorted(rng.sample(range(n), count))


def hamming_demo(
    text: str,
    dmin: int = 3,
    n_errors: int = 1,
    seed: int = 1,
    positions: list[int] | None = None,
) -> str:
    bits = text_to_bits(text)
    k = len(bits)
    if k < 16:
        raise ValueError(f"длина сообщения {k} бит; по заданию должна быть не менее 16")
    code = HammingCode(k, dmin)
    info = bits_to_int(bits)
    word = code.encode(info)
    x_k, x_r = code.split(word)

    if positions is None:
        positions = _positions(random.Random(seed), code.n, n_errors)
    else:
        positions = sorted(p - 1 for p in positions)
    received = word
    for p in positions:
        received ^= 1 << p
    y_k, y_r = code.split(received)
    y_r_new = code.checks(y_k)
    res = code.decode_word(received)
    e_vec = 0
    for p in res.error_positions:
        e_vec |= 1 << p

    L = [
        f"Информационное сообщение: {text!r}",
        f"k = {k}, r = {code.r}, n = {code.n}, d_min = {dmin}, скорость R = k/n = {code.rate:.3f}, "
        f"избыточность r/n = {code.redundancy:.3f}",
        "",
        "Проверочная матрица H = [P' | I]:",
        format_matrix(code.h_matrix(), code.k),
        "",
        f"X_k  = {bit_str(x_k, k, 8)}",
        f"X_r  = {bit_str(x_r, code.r)}",
        f"X_n  = {bit_str(word, code.n)}",
        "",
        f"Внесено ошибок: {len(positions)}; позиции (с 1): {[p + 1 for p in positions] or '-'}",
        f"Y_n  = {bit_str(received, code.n)}",
        f"Y_r  = {bit_str(y_r, code.r)}   (проверочные символы принятого слова)",
        f"Y_r' = {bit_str(y_r_new, code.r)}   (вновь вычисленные по принятым информационным)",
        f"S    = {bit_str(res.syndrome, code.r)}   (S = Y_r xor Y_r')",
    ]
    if res.status == "ok":
        L.append("Синдром нулевой: ошибок не обнаружено." + (" (!) Ошибка не замечена." if positions else ""))
    elif res.status == "corrected":
        L += [
            f"Синдром равен столбцу {res.error_positions[0] + 1} матрицы H -> ошибка в позиции {res.error_positions[0] + 1}.",
            f"E_n  = {bit_str(e_vec, code.n)}",
            f"Y_n' = Y_n + E_n = {bit_str(res.word, code.n)}",
        ]
    else:
        L.append("Синдром ненулевой, но не совпадает ни с одним столбцом H: обнаружена неисправимая (кратная) ошибка.")
    if res.status != "detected":
        ok = res.word == word
        L.append("Результат: " + ("слово восстановлено верно (Y_n' = X_n)." if ok else "восстановлено НЕВЕРНО (ошибочная коррекция)."))
    return "\n".join(L)


def hamming_matrices_report(ks=(4, 6, 8, 9, 10, 15, 16)) -> str:
    """Параметры и проверочные матрицы для k из вопроса 3 методички."""
    L = ["Параметры кода Хемминга (зависимость r от k):", ""]
    L.append("|  k |  r | n (d=3) | R=k/n | r+1 | n (d=4) | R=k/n |")
    L.append("|---:|---:|---:|---:|---:|---:|---:|")
    for k in ks:
        c3, c4 = HammingCode(k, 3), HammingCode(k, 4)
        L.append(f"| {k} | {c3.r} | {c3.n} | {c3.rate:.3f} | {c4.r} | {c4.n} | {c4.rate:.3f} |")
    L.append("")
    for k in ks:
        for d in (3, 4):
            c = HammingCode(k, d)
            L.append(f"H для k={k}, d_min={d} ({c.n},{k}):")
            L.append(format_matrix(c.h_matrix(), k))
            L.append("")
    return "\n".join(L)


def _fmt_rows(rows: list[dict]) -> list[str]:
    L = ["| i | N1 | режим | N2/N1 | N3/N1 | исправлено | ошибочная коррекция | обнаружено, не исправлено | не обнаружено |",
         "|---:|---:|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        L.append(
            f"| {r['i']} | {r['N1']} | {r['mode']} | {r['N2/N1']:.4f} | {r['N3/N1']:.4f} | "
            f"{r['exact']} | {r['miscorrected']} | {r['detected']} | {r['undetected']} |"
        )
    return L


def hamming_experiment_report(k: int = 16, trials: int = 10000, seed: int = 2026) -> str:
    L = [f"Эксперимент: код Хемминга, k = {k}", ""]
    for d in (3, 4):
        c = HammingCode(k, d)
        L.append(f"d_min = {d}: ({c.n},{k})-код, r = {c.r}, R = {c.rate:.3f}, измеренное d_min = {c.min_distance()}")
        L += _fmt_rows(error_table(c, 4, trials, 1, seed, exhaustive_up_to=2))
        L.append("")
    return "\n".join(L)


def iterative_demo(
    cfg_index: int = 1,
    groups: int | None = None,
    n_errors: int = 1,
    seed: int = 1,
    text: str = "Hi",
    positions: list[int] | None = None,
    max_weight: int = 3,
) -> str:
    k1, k2, z, allowed = VARIANT1_CONFIGS[cfg_index - 1]
    groups = groups or allowed[-1]
    if groups not in allowed:
        raise ValueError(f"для конфигурации {cfg_index} допустимо число групп: {allowed}")
    code = IterativeCode(IterativeConfig(k1, k2, z, groups))
    bits = text_to_bits(text)
    if len(bits) != code.k:
        raise ValueError(f"сообщение {text!r} = {len(bits)} бит, а k = {code.k} (вариант 1)")
    info = bits_to_int(bits)
    word = code.encode(info)
    x_k, x_r = code.split(word)

    if positions is None:
        positions = _positions(random.Random(seed), code.n, n_errors)
    else:
        positions = sorted(p - 1 for p in positions)
    received = word
    for p in positions:
        received ^= 1 << p
    res = code.decode(received, max_weight)

    sizes = code.group_sizes()
    L = [
        f"Итеративный код, конфигурация {cfg_index} варианта 1: k1={k1}, k2={k2}, z={z}, групп паритетов: {groups}",
        f"Диагонали: {code.cfg.diag_mode}; k = {code.k}, r = {code.r}, n = {code.n}, "
        f"скорость k/(k+r) = {code.rate:.3f}",
        "Проверочных символов по группам: " + ", ".join(f"{g}-я ({n})" for g, n in sizes.items()),
        "",
        f"Информационное слово X_k = {bit_str(x_k, code.k, 8)}  ({text!r})",
        code.render(word),
        f"X_r = {bit_str(x_r, code.r)}",
        f"X_n = {bit_str(word, code.n)}",
        "",
        f"Внесено ошибок: {len(positions)}; позиции (с 1): {[p + 1 for p in positions] or '-'}",
    ]
    for p in positions:
        L.append("  - " + code.position_name(p))
    L += [f"Y_n  = {bit_str(received, code.n)}", f"S    = {bit_str(res.syndrome, code.r)}"]
    failed = code.failed_checks(res.syndrome)
    L.append("Не выполнены проверки: " + (", ".join(failed) if failed else "нет"))
    if res.status == "ok":
        L.append("Синдром нулевой: ошибок не обнаружено." + (" (!) Ошибка не замечена." if positions else ""))
    elif res.status == "corrected":
        L.append(f"Найден вектор ошибки веса {len(res.error_positions)}:")
        for p in res.error_positions:
            L.append("  - " + code.position_name(p))
        L.append(f"Y_n' = {bit_str(res.word, code.n)}")
        L.append("Результат: " + ("слово восстановлено верно (Y_n' = X_n)." if res.word == word else "восстановлено НЕВЕРНО (ошибочная коррекция)."))
    else:
        L.append("Ошибка обнаружена, но исправить её однозначно нельзя (кратность превышает корректирующую способность).")
    return "\n".join(L)


def iterative_parameters_rows() -> list[dict]:
    rows = []
    for idx, (k1, k2, z, allowed) in enumerate(VARIANT1_CONFIGS, 1):
        for g in allowed:
            c = IterativeCode(IterativeConfig(k1, k2, z, g))
            rows.append({
                "config": idx, "k1": k1, "k2": k2, "z": z, "groups": g, "k": c.k, "r": c.r,
                "n": c.n, "rate": c.rate, "dmin": c.min_distance(), "sizes": c.group_sizes(),
            })
    return rows


def iterative_parameters_report() -> str:
    L = ["Параметры итеративных кодов варианта 1 (k = 16)", "",
         "| конф. | k1 x k2 x z | групп | r | n | k/(k+r) | d_min (измерено) | проверок по группам |",
         "|---:|---|---:|---:|---:|---:|---:|---|"]
    for r in iterative_parameters_rows():
        dims = f"{r['k1']}x{r['k2']}" + (f"x{r['z']}" if r["z"] > 1 else "")
        sizes = "+".join(str(v) for v in r["sizes"].values())
        L.append(f"| {r['config']} | {dims} | {r['groups']} | {r['r']} | {r['n']} | {r['rate']:.3f} | {r['dmin']} | {sizes} |")
    return "\n".join(L)


def iterative_experiment_report(trials: int = 10000, seed: int = 2026, max_multiplicity: int = 5, max_weight: int = 3) -> str:
    L = [iterative_parameters_report(), ""]
    for idx, (k1, k2, z, allowed) in enumerate(VARIANT1_CONFIGS, 1):
        for g in allowed:
            c = IterativeCode(IterativeConfig(k1, k2, z, g))
            L.append(f"Конфигурация {idx}: {c.cfg.title} (n={c.n}, r={c.r})")
            L += _fmt_rows(error_table(c, max_multiplicity, trials, max_weight, seed))
            L.append("")
    return "\n".join(L)
