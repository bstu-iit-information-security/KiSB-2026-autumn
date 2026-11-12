"""Модуль генераторов псевдослучайных последовательностей (LFSR, Shrinking Generator)."""

from .lfsr import LFSR, check_primitive_gf2
from .shrinking import ShrinkingGenerator

__all__ = ["LFSR", "check_primitive_gf2", "ShrinkingGenerator"]

