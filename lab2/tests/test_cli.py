import pytest

from src.main import build_parser
from src.reports import iterative_demo, iterative_parameters_report


def test_iterative_demo_corrects_single_error():
    text = iterative_demo(cfg_index=1, groups=3, n_errors=1, seed=3)
    assert "восстановлено верно" in text and "Не выполнены проверки" in text


def test_iterative_demo_rejects_wrong_group_count():
    with pytest.raises(ValueError):
        iterative_demo(cfg_index=1, groups=5)  # 5 групп только для 3D-конфигураций


def test_iterative_demo_requires_16_bits():
    with pytest.raises(ValueError):
        iterative_demo(text="Hello")


def test_parameters_report_has_all_twelve_rows():
    report = iterative_parameters_report()
    assert report.count("\n| ") >= 12 + 1


def test_parser_accepts_all_commands():
    p = build_parser()
    for argv in (["hamming"], ["matrices"], ["experiment-hamming"], ["iterative", "--config", "3"],
                 ["iterative-params"], ["experiment-iterative", "--trials", "10"]):
        assert p.parse_args(argv).func
