# config.py
"""
Параметры лабораторной работы №5 (итеративные коды).
Вариант 10 (логически совпадает с вариантом 5).
"""

from dataclasses import dataclass


@dataclass
class Config:
    # ---- Данные варианта 10 (он же 5) ----
    variant: int = 10
    k: int = 40                 # длина информационного слова (бит)

    # 2D-разложение (для 2 и 3 групп паритетов)
    k1: int = 5                 # строки 2D-матрицы
    k2: int = 8                 # столбцы 2D-матрицы

    # 3D-разложение (для 4 и 5 групп паритетов)
    # 5 * 4 * 2 = 40
    k3d: tuple = (5, 4, 2)

    # Количество групп паритетов
    parity_groups: tuple = (2, 3, 4, 5)

    # ---- Параметры эксперимента ----
    N1: int = 1000              # число испытаний на одну кратность
    error_multiplicities: tuple = (1, 2, 3)  # кратности i
    seed: int = 42              # зерно ГПСЧ

    def check(self):
        """Проверка корректности разложений k."""
        assert self.k1 * self.k2 == self.k, \
            f"2D: k1*k2={self.k1 * self.k2} != k={self.k}"
        a, b, c = self.k3d
        assert a * b * c == self.k, \
            f"3D: {a}*{b}*{c} != k={self.k}"
        return True


if __name__ == "__main__":
    cfg = Config()
    cfg.check()
    print(f"Конфигурация варианта {cfg.variant} корректна:")
    print(f"  k  = {cfg.k}")
    print(f"  2D: {cfg.k1} x {cfg.k2} = {cfg.k1 * cfg.k2}")
    print(f"  3D: {cfg.k3d[0]} x {cfg.k3d[1]} x {cfg.k3d[2]} = "
          f"{cfg.k3d[0] * cfg.k3d[1] * cfg.k3d[2]}")
    print(f"  Группы паритетов: {cfg.parity_groups}")