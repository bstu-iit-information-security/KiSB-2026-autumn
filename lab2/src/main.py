"""
ЛР №2 «Избыточное кодирование данных в информационных системах»
(ч.1 - код Хемминга, ч.2 - итеративные коды), Вариант 1.

Запуск (из директории lab2/):
    python3 -m src.main hamming --text "Hi" --dmin 3 --errors 1
    python3 -m src.main hamming --file samples/message.txt --dmin 4 --errors 2 --out report/hamming_demo.txt
    python3 -m src.main matrices
    python3 -m src.main experiment-hamming
    python3 -m src.main iterative --config 3 --groups 4 --errors 3
    python3 -m src.main experiment-iterative

Файл можно запускать и напрямую (кнопка Run в VS Code): блок ниже сам
добавляет lab2/ в sys.path, чтобы `from src...` не падал с ModuleNotFoundError.
"""
from __future__ import annotations

if __name__ == "__main__" and __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import sys

from src.reports import (
    hamming_demo,
    hamming_experiment_report,
    hamming_matrices_report,
    iterative_demo,
    iterative_experiment_report,
    iterative_parameters_report,
)


def _emit(text: str, out: str | None) -> None:
    print(text)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"\n[сохранено в {out}]")


def _read_text(args: argparse.Namespace, default: str) -> str:
    if getattr(args, "file", None):
        with open(args.file, encoding="utf-8") as f:
            return f.read().rstrip("\n")
    return args.text if args.text is not None else default


def _positions(arg: str | None) -> list[int] | None:
    return [int(x) for x in arg.split(",")] if arg else None


def cmd_hamming(args: argparse.Namespace) -> None:
    text = _read_text(args, "Hi")
    _emit(hamming_demo(text, args.dmin, args.errors, args.seed, _positions(args.positions)), args.out)


def cmd_matrices(args: argparse.Namespace) -> None:
    _emit(hamming_matrices_report(), args.out)


def cmd_exp_hamming(args: argparse.Namespace) -> None:
    _emit(hamming_experiment_report(args.k, args.trials, args.seed), args.out)


def cmd_iterative(args: argparse.Namespace) -> None:
    text = _read_text(args, "Hi")
    _emit(
        iterative_demo(args.config, args.groups, args.errors, args.seed, text, _positions(args.positions), args.max_weight),
        args.out,
    )


def cmd_params(args: argparse.Namespace) -> None:
    _emit(iterative_parameters_report(), args.out)


def cmd_exp_iterative(args: argparse.Namespace) -> None:
    _emit(iterative_experiment_report(args.trials, args.seed, args.max_errors, args.max_weight), args.out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ЛР №2 (Вариант 1): код Хемминга и итеративные коды")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--out", help="сохранить вывод в файл (UTF-8)")

    p = sub.add_parser("hamming", help="кодирование/декодирование кодом Хемминга (ЛР №4)")
    p.add_argument("--text", help="информационное сообщение (по умолчанию 'Hi')")
    p.add_argument("--file", help="текстовый файл с сообщением")
    p.add_argument("--dmin", type=int, choices=(3, 4), default=3)
    p.add_argument("--errors", type=int, choices=(0, 1, 2), default=1)
    p.add_argument("--positions", help="позиции ошибок через запятую (с 1); иначе случайные")
    p.add_argument("--seed", type=int, default=1)
    common(p)
    p.set_defaults(func=cmd_hamming)

    p = sub.add_parser("matrices", help="матрицы H и параметры для k = 4, 6, 8, 9, 10, 15, 16")
    common(p)
    p.set_defaults(func=cmd_matrices)

    p = sub.add_parser("experiment-hamming", help="статистика исправления/обнаружения ошибок кодом Хемминга")
    p.add_argument("--k", type=int, default=16)
    p.add_argument("--trials", type=int, default=10000)
    p.add_argument("--seed", type=int, default=2026)
    common(p)
    p.set_defaults(func=cmd_exp_hamming)

    p = sub.add_parser("iterative", help="кодирование/декодирование итеративным кодом (ЛР №5)")
    p.add_argument("--config", type=int, choices=(1, 2, 3, 4), default=1, help="конфигурация варианта 1 (табл. 5.2)")
    p.add_argument("--groups", type=int, choices=(2, 3, 4, 5), help="число групп паритетов")
    p.add_argument("--errors", type=int, default=1)
    p.add_argument("--positions", help="позиции ошибок через запятую (с 1); иначе случайные")
    p.add_argument("--text", help="сообщение ровно из 16 бит, напр. 'Hi'")
    p.add_argument("--file", help="файл с сообщением из 2 символов")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--max-weight", type=int, default=3, dest="max_weight", help="наибольший вес ошибки в таблице лидеров")
    common(p)
    p.set_defaults(func=cmd_iterative)

    p = sub.add_parser("iterative-params", help="r, n, скорость, d_min для всех конфигураций варианта 1")
    common(p)
    p.set_defaults(func=cmd_params)

    p = sub.add_parser("experiment-iterative", help="N2/N1 и N3/N1 по кратностям ошибок для всех конфигураций")
    p.add_argument("--trials", type=int, default=10000, help="N1 для кратностей с выборкой")
    p.add_argument("--max-errors", type=int, default=5, dest="max_errors")
    p.add_argument("--max-weight", type=int, default=3, dest="max_weight")
    p.add_argument("--seed", type=int, default=2026)
    common(p)
    p.set_defaults(func=cmd_exp_iterative)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
