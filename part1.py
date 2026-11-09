from __future__ import annotations
import random
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Callable


def bits_to_str(bits: List[int]) -> str:
    return "".join(str(b) for b in bits)


def print_bits(title: str, bits: Optional[List[int]], width: int = 64) -> List[str]:
    if bits is None:
        return [f"{title:<22} —"]
    s = bits_to_str(bits)
    out = []
    for i in range(0, len(s), width):
        prefix = title if i == 0 else ""
        out.append(f"{prefix:<22} {s[i:i+width]}")
    return out


def build_hamming_parity(k: int, d_min: int) -> List[List[int]]:
    """Строит строки матрицы A (часть H = [A | I]).
    Столбцы информационной части выбираются так, чтобы не пересекаться
    с единичными столбцами проверочной части.
    d_min=3 → обычный код; d_min=4 → расширенный (нечётный вес столбцов).
    """
    r0 = 0
    while (1 << r0) < k + r0 + 1:
        r0 += 1

    if d_min == 3:
        r = r0
        powers = {1 << i for i in range(r)}
        cols = [m for m in range(1, 1 << r) if m not in powers]
        cols = sorted(cols, key=lambda m: (bin(m).count("1"), m))[:k]
    else:
        r = r0 + 1
        powers = {1 << i for i in range(r)}
        cols = [m for m in range(1, 1 << r)
                if bin(m).count("1") % 2 == 1 and m not in powers]
        cols = sorted(cols, key=lambda m: (bin(m).count("1"), m))[:k]

    A = [[(cols[j] >> i) & 1 for j in range(k)] for i in range(r)]
    return A


def make_H(A: List[List[int]]) -> List[List[int]]:
    r = len(A)
    return [row + [1 if i == j else 0 for j in range(r)] for i, row in enumerate(A)]


def encode_word(info: List[int], A: List[List[int]]) -> List[int]:
    parity = [sum(a * b for a, b in zip(row, info)) % 2 for row in A]
    return info + parity


def inject_errors(codeword: List[int], num: int, rng: random.Random) -> Tuple[List[int], List[int]]:
    pos = sorted(rng.sample(range(len(codeword)), num)) if num else []
    received = codeword[:]
    for p in pos:
        received[p] ^= 1
    return received, pos


def syndrome_decoder(H: List[List[int]], d_min: int) -> Callable:
    """Возвращает функцию декодирования по синдрому."""
    col_vals = []
    for j in range(len(H[0])):
        val = 0
        for i, row in enumerate(H):
            if row[j]:
                val |= (1 << i)
        col_vals.append(val)

    single_map = {v: idx for idx, v in enumerate(col_vals)}

    def decode(received: List[int]):
        syn = 0
        for bit, col in zip(received, col_vals):
            if bit:
                syn ^= col
        syn_vec = [(syn >> i) & 1 for i in range(len(H))]
        overall = sum(received) % 2   # для расширенного кода

        if syn == 0:
            if d_min == 4 and overall:
                return received[:], syn_vec, None, None, "аномалия чётности"
            return received[:], syn_vec, (), 0, "синдром нулевой"

        if d_min == 4:
            if overall == 1 and syn in single_map:
                pos = single_map[syn]
                fixed = received[:]
                fixed[pos] ^= 1
                return fixed, syn_vec, (pos,), 1, "исправлена одиночная ошибка"
            return received[:], syn_vec, None, 2, "обнаружена двойная ошибка (не исправляем)"

        if syn in single_map:
            pos = single_map[syn]
            fixed = received[:]
            fixed[pos] ^= 1
            return fixed, syn_vec, (pos,), 1, "исправлена одиночная ошибка"
        return received[:], syn_vec, None, None, "неопознанный синдром"

    return decode


def run_stats(codeword: List[int], decode_fn, trials: int, rng: random.Random) -> List[str]:
    lines = [
        "",
        "СТАТИСТИКА ПО КРАТНОСТИ ОШИБОК",
        " i | опыты | обнаружено | верная кратн. | полное восст. | N2/N1 | N3/N1 | ложные",
    ]
    max_i = min(5, len(codeword))
    for i in range(max_i + 1):
        det = n2 = n3 = false = 0
        for _ in range(trials):
            recv, _ = inject_errors(codeword, i, rng)
            restored, syn, est, w, status = decode_fn(recv)
            if any(syn):
                det += 1
            if w == i:
                n2 += 1
            if restored == codeword:
                n3 += 1
            if est is not None and est != () and restored != codeword:
                false += 1
        lines.append(
            f"{i:>2} | {trials:>5} | {det:>10} | {n2:>13} | {n3:>13} | "
            f"{n2/trials:5.3f} | {n3/trials:5.3f} | {false:>6}"
        )
    return lines


def demo_case(info: List[int], A: List[List[int]], decode_fn, err_cnt: int, rng: random.Random) -> List[str]:
    cw = encode_word(info, A)
    recv, real_pos = inject_errors(cw, err_cnt, rng)
    fixed, syn, est, weight, status = decode_fn(recv)
    k = len(info)
    n = len(cw)
    lines = [
        f"--- демонстрация: внесено {err_cnt} ошибок ---",
        *print_bits("Xk (инф.)", info),
        *print_bits("Xn (код.)", cw),
        *print_bits("Yn (принято)", recv),
        *print_bits("синдром", syn),
        f"{'реальные поз.':<22} {[p+1 for p in real_pos]}",
        f"{'оценённые поз.':<22} {None if est is None else [p+1 for p in est]}",
        f"{'оценка кратности':<22} {weight}",
        f"{'статус':<22} {status}",
        f"{'восстановлено':<22} {'да' if fixed == cw else 'нет'}",
        *print_bits("Yn*", fixed),
    ]
    return lines


def main() -> None:
    print("=" * 60)
    print("ЛАБОРАТОРНАЯ №4 — КОД ХЕММИНГА")
    print("=" * 60)

    path = Path("message.txt")
    if not path.exists():
        default = "Hello"
        text = input(f"Файл message.txt не найден. Введите текст [{default}]: ").strip() or default
        path.write_text(text, encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    info = [int(b) for byte in text.encode("utf-8") for b in f"{byte:08b}"]
    if len(info) < 16:
        raise SystemExit("По условию требуется не менее 16 информационных бит.")

    print(f"Исходный текст: {text!r}")
    print(f"Длина информационного слова k = {len(info)} бит")

    mode = int(input("Режим (1=d_min=3, 2=d_min=4, 3=оба) [3]: ").strip() or "3")
    show_matrix = int(input("Печатать матрицу H? (0/1) [0]: ").strip() or "0")
    trials = int(input("Число опытов на кратность [250]: ").strip() or "250")

    report: List[str] = [
        "ЛАБОРАТОРНАЯ РАБОТА №4. КОД ХЕММИНГА",
        f"Исходный файл: {path}",
        f"Текст: {text!r} (UTF-8), k={len(info)}",
        "Матрица H представлена в форме [A | I]. Арифметика по модулю 2.",
        "Нумерация позиций с 1 слева направо.",
        f"Seed подробных примеров = 7, статистика = 11.",
    ]

    distances = (3, 4) if mode == 3 else (mode + 2,)
    for d in distances:
        A = build_hamming_parity(len(info), d)
        H = make_H(A)
        decode = syndrome_decoder(H, d)
        r = len(A)
        n = len(info) + r
        block = [
            "",
            "=" * 60,
            f"КОД ХЕММИНГА, d_min = {d}",
            f"k={len(info)}, r={r}, n={n}, скорость={len(info)/n:.4f}, избыточность={r/n:.4f}",
        ]
        print("\n".join(block))
        report.extend(block)

        # матрица
        mat_lines = ["Проверочная матрица H:"]
        for start in range(0, n, 28):
            end = min(start + 28, n)
            mat_lines.append(f"  столбцы {start+1}–{end}:")
            for i, row in enumerate(H, 1):
                mat_lines.append(f"  {i:>2}: " + " ".join(str(x) for x in row[start:end]))
        report.extend(mat_lines)
        if show_matrix:
            print("\n".join(mat_lines))

        rng_demo = random.Random(7)
        for e in (0, 1, 2):
            demo = demo_case(info, A, decode, e, rng_demo)
            print("\n".join(demo))
            report.extend(demo)

        stats = run_stats(encode_word(info, A), decode, trials, random.Random(11))
        print("\n".join(stats))
        report.extend(stats)

    report.extend([
        "",
        "ВЫВОДЫ",
        "Обычный код (d_min=3) гарантирует исправление любой одиночной ошибки.",
        "При двух ошибках синдром ненулевой, однако декодер может принять его",
        "за синдром одиночной ошибки и «исправить» неверный бит.",
        "Расширенный код (d_min=4) дополнительно обнаруживает двойные ошибки",
        "и не пытается их исправлять.",
        "Нулевой синдром не является абсолютной гарантией отсутствия ошибок",
        "(возможны ошибки чётной кратности, кратные кодовым словам).",
    ])

    out = Path("lab4_result.txt")
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nРезультаты сохранены в {out}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nПрервано пользователем.")
        sys.exit(1)
