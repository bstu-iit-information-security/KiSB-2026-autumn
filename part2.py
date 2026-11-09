from __future__ import annotations
import random
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Callable, Dict, Set


def bits_str(bits: List[int]) -> str:
    return "".join(map(str, bits))


def fmt_bits(label: str, bits: Optional[List[int]], chunk: int = 64) -> List[str]:
    if bits is None:
        return [f"{label:<20} —"]
    s = bits_str(bits)
    res = []
    for i in range(0, len(s), chunk):
        res.append(f"{(label if i == 0 else ''):<20} {s[i:i+chunk]}")
    return res


def build_checks(rows: int, cols: int, depth: int, n_groups: int, use_hv: bool) -> List[List[int]]:
    """Формирует строки проверочной матрицы A (только информационные позиции).
    n_groups:
      2 — H + V
      3 — H + V + D+
      4 — H + V + D+ + D-
      5 — + Z (межслойные)
    use_hv — дополнительная проверка чётности всего слоя
    """
    k = rows * cols * depth
    checks: List[List[int]] = []

    def add(positions: List[Tuple[int, int, int]]) -> None:
        row = [0] * k
        for t, i, j in positions:
            idx = (t * rows + i) * cols + j
            row[idx] = 1
        checks.append(row)

    for t in range(depth):
        for i in range(rows):
            add([(t, i, j) for j in range(cols)])
        # вертикальные (по столбцам)
        for j in range(cols):
            add([(t, i, j) for i in range(rows)])

        if n_groups >= 3:
            if depth == 1:
                for d in range(rows + cols - 1):
                    add([(t, i, j) for i in range(rows) for j in range(cols) if i + j == d])
            else:
                for d in range(rows):
                    add([(t, i, j) for i in range(rows) for j in range(cols)
                         if (i + j) % rows == d])

        if n_groups >= 4:
            for d in range(rows):
                add([(t, i, j) for i in range(rows) for j in range(cols)
                     if (i - j) % rows == d])

        if use_hv:
            add([(t, i, j) for i in range(rows) for j in range(cols)])

    if n_groups == 5:
        for i in range(rows):
            for j in range(cols):
                add([(t, i, j) for t in range(depth)])

    return checks


def parity_matrix(A: List[List[int]]) -> List[List[int]]:
    r = len(A)
    return [row[:] + [1 if i == j else 0 for j in range(r)] for i, row in enumerate(A)]


def encode(info: List[int], A: List[List[int]]) -> List[int]:
    par = [sum(x * y for x, y in zip(info, row)) % 2 for row in A]
    return info + par


def add_noise(word: List[int], weight: int, rng: random.Random) -> Tuple[List[int], List[int]]:
    if weight == 0:
        return word[:], []
    pos = sorted(rng.sample(range(len(word)), weight))
    noisy = word[:]
    for p in pos:
        noisy[p] ^= 1
    return noisy, pos


def create_decoder(H: List[List[int]]) -> Callable:
    """Синдромный декодер, ищущий ошибки веса 1–3."""
    n = len(H[0])
    r = len(H)
    cols = []
    for j in range(n):
        v = 0
        for i in range(r):
            if H[i][j]:
                v |= 1 << i
        cols.append(v)

    single: Dict[int, Tuple[int, ...]] = {v: (j,) for j, v in enumerate(cols)}
    pair_map: Dict[int, List[Tuple[int, int]]] = {}
    for a in range(n):
        for b in range(a + 1, n):
            pair_map.setdefault(cols[a] ^ cols[b], []).append((a, b))

    triple_cache: Dict[int, Tuple[Optional[int], Optional[Tuple[int, ...]]]] = {}

    def locate(syn: int) -> Tuple[Optional[int], Optional[Tuple[int, ...]]]:
        if syn == 0:
            return 0, ()
        if syn in single:
            return 1, single[syn]
        if syn in pair_map:
            cands = pair_map[syn]
            if len(cands) == 1:
                return 2, cands[0]
            return 2, None  # неоднозначно
        if syn in triple_cache:
            return triple_cache[syn]
        found: Set[Tuple[int, ...]] = set()
        for i, c in enumerate(cols):
            for pr in pair_map.get(syn ^ c, ()):
                if i not in pr:
                    found.add(tuple(sorted((i,) + pr)))
                    if len(found) > 1:
                        triple_cache[syn] = (3, None)
                        return 3, None
        if len(found) == 1:
            ans = (3, next(iter(found)))
        else:
            ans = (None, None)
        triple_cache[syn] = ans
        return ans

    def decode(received: List[int]):
        syn = 0
        for bit, c in zip(received, cols):
            if bit:
                syn ^= c
        syn_bits = [(syn >> i) & 1 for i in range(r)]
        w, pos = locate(syn)
        if w == 0:
            return received[:], syn_bits, (), 0, "проверки выполнены"
        if pos is None:
            msg = "неоднозначность" if w else "нет решения веса ≤3"
            return received[:], syn_bits, None, w, msg
        corrected = received[:]
        for p in pos:
            corrected[p] ^= 1
        return corrected, syn_bits, pos, w, "применён кандидат минимального веса"

    return decode


# Вариант 1
SHAPES = [
    (4, 4, 1),   
    (8, 2, 1),   
    (4, 2, 2),   
    (2, 4, 2),   
]


def detailed_run(info: List[int], A: List[List[int]], dec, err: int, rng: random.Random) -> List[str]:
    cw = encode(info, A)
    recv, real = add_noise(cw, err, rng)
    fixed, syn, est, w, status = dec(recv)
    lines = [
        f"--- пример с {err} ошибками ---",
        *fmt_bits("Xk", info),
        *fmt_bits("Xn", cw),
        *fmt_bits("Yn", recv),
        *fmt_bits("синдром", syn),
        f"{'факт. позиции':<20} {[p+1 for p in real]}",
        f"{'оценка позиций':<20} {None if est is None else [p+1 for p in est]}",
        f"{'оценка веса':<20} {w}",
        f"{'статус':<20} {status}",
        f"{'совпало с Xn':<20} {'да' if fixed == cw else 'нет'}",
        *fmt_bits("Yn*", fixed),
    ]
    return lines


def statistics(cw: List[int], dec, trials: int, rng: random.Random) -> List[str]:
    lines = [
        "",
        "СТАТИСТИКА",
        " i | N1  | обнар. | N2  | N3  | N2/N1 | N3/N1 | ложн.",
        "N2 — совпала оценка кратности; N3 — полностью восстановлено слово",
    ]
    for i in range(0, 7):
        det = n2 = n3 = false = 0
        for _ in range(trials):
            recv, _ = add_noise(cw, i, rng)
            fixed, syn, est, w, _ = dec(recv)
            if any(syn):
                det += 1
            if w == i:
                n2 += 1
            if fixed == cw:
                n3 += 1
            if est not in (None, ()) and fixed != cw:
                false += 1
        lines.append(
            f"{i:>2} | {trials:>3} | {det:>6} | {n2:>3} | {n3:>3} | "
            f"{n2/trials:5.3f} | {n3/trials:5.3f} | {false:>5}"
        )
    return lines


def main() -> None:
    print("=" * 60)
    print("ЛАБОРАТОРНАЯ №5 — ИТЕРАТИВНЫЕ КОДЫ (вариант 1, k=16)")
    print("=" * 60)

    raw = input("16 информационных бит [1011001011001011]: ").strip() or "1011001011001011"
    raw = "".join(raw.split())
    if len(raw) != 16 or set(raw) - {"0", "1"}:
        raise SystemExit("Нужно ровно 16 символов 0/1.")
    info = [int(c) for c in raw]

    mode = int(input("1 — одна форма; 2 — все комбинации варианта [2]: ").strip() or "2")
    if mode == 1:
        print("  1: 4×4   2: 8×2   3: 4×2×2   4: 2×4×2")
        idx = int(input("Номер формы [1]: ").strip() or "1") - 1
        shape = SHAPES[idx]
        max_g = 3 if shape[2] == 1 else 5
        groups = int(input(f"Число групп паритетов (2..{max_g}) [2]: ").strip() or "2")
        hv = int(input("Доп. HV-проверка слоя (0/1) [0]: ").strip() or "0")
        configs = [(shape, groups, hv)]
    else:
        configs = []
        for shape in SHAPES:
            max_g = 3 if shape[2] == 1 else 5
            for g in range(2, max_g + 1):
                for hv in (0, 1):
                    configs.append((shape, g, hv))

    err_demo = int(input("Число ошибок в подробном примере [2]: ").strip() or "2")
    show_H = int(input("Печатать матрицы H (0/1) [0]: ").strip() or "0")
    trials = int(input("Опытов на каждую кратность [200]: ").strip() or "200")

    report: List[str] = [
        "ЛАБОРАТОРНАЯ №5. ИТЕРАТИВНЫЕ КОДЫ. ВАРИАНТ 1",
        "k = 16; допустимые формы: 4×4, 8×2, 4×2×2, 2×4×2",
        "Группы: H (строки), V (столбцы), D+ (i+j), D- (i-j), Z (по слоям)",
        "HV — дополнительная проверка чётности всего слоя",
        "Для 2D диагонали: i+j = const; для 3D — по модулю числа строк",
        "Декодер ищет единственный кандидат веса ≤ 3; при неоднозначности отказывается",
        f"Seed примеров = 13, статистики = 17",
    ]

    summary = ["", "СВОДНАЯ ТАБЛИЦА", "форма     G  HV   r    n   скорость  избыт."]

    for shape, groups, hv in configs:
        rows, cols, depth = shape
        name = f"{rows}x{cols}" + (f"x{depth}" if depth > 1 else "")
        A = build_checks(rows, cols, depth, groups, bool(hv))
        H = parity_matrix(A)
        dec = create_decoder(H)
        r = len(A)
        n = 16 + r
        header = [
            "",
            "=" * 60,
            f"ФОРМА {name} | групп={groups} | HV={hv}",
            f"k=16, r={r}, n={n}, R={16/n:.4f}, избыточность={r/n:.4f}",
        ]
        for t in range(depth):
            header.append(f"слой {t+1}:")
            for i in range(rows):
                start = (t * rows + i) * cols
                header.append("  " + " ".join(str(info[start + j]) for j in range(cols)))
        print("\n".join(header))
        report.extend(header)

        mat = ["Проверочная матрица H:"]
        for s in range(0, n, 28):
            e = min(s + 28, n)
            mat.append(f"  столбцы {s+1}–{e}:")
            for i, row in enumerate(H, 1):
                mat.append(f"  {i:>2}: " + " ".join(str(b) for b in row[s:e]))
        report.extend(mat)
        if show_H:
            print("\n".join(mat))

        demo = detailed_run(info, A, dec, err_demo, random.Random(13))
        print("\n".join(demo))
        report.extend(demo)

        stats = statistics(encode(info, A), dec, trials, random.Random(17))
        print("\n".join(stats))
        report.extend(stats)

        summary.append(f"{name:<9} {groups:>2} {hv:>3} {r:>4} {n:>4} {16/n:>9.4f} {r/n:>7.4f}")

    report.extend(summary)
    report.extend([
        "",
        "ВЫВОДЫ",
        "Увеличение числа независимых групп паритетов повышает избыточность",
        "и в большинстве случаев улучшает способность к обнаружению/исправлению.",
        "При двух и трёх ошибках синдром может соответствовать нескольким",
        "конфигурациям одинакового веса — декодер корректно отказывается от исправления.",
        "Для форм с двумя строками диагонали D+ и D- часто линейно зависимы.",
        "Нулевой синдром не доказывает отсутствие ошибок (возможны кратные коду комбинации).",
        "Полученные соотношения N2/N1 и N3/N1 дают практическую оценку корректирующей способности.",
    ])

    out = Path("lab5_result.txt")
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nОтчёт записан в {out}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nОстановлено.")
        sys.exit(1)
