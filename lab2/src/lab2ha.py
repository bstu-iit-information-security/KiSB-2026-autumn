import random
import numpy as np


class IterativeCode2D:

  def __init__(self, k1: int, k2: int):
    self.k1 = k1
    self.k2 = k2
    self.k = k1 * k2

  def encode(self, data_bits: list[int]):
    """Кодирует k-битный вектор в двумерный код с проверками по строкам, столбцам и X_hv."""
    matrix = np.array(data_bits, dtype=int).reshape((self.k1, self.k2))

    # Горизонтальные проверки (паритеты строк)
    p_row = np.sum(matrix, axis=1) % 2
    # Вертикальные проверки (паритеты столбцов)
    p_col = np.sum(matrix, axis=0) % 2
    # Паритет паритетов
    p_all = np.sum(p_row) % 2

    return {
        "matrix": matrix,
        "p_row": p_row,
        "p_col": p_col,
        "p_all": p_all,
        "full_vector": np.concatenate(
            [data_bits, p_row, p_col, [p_all]]
        ).tolist(),
    }

  def introduce_errors(self, full_vector: list[int], error_count: int):
    """Искажает случайные error_count бит."""
    corrupted = list(full_vector)
    indices = random.sample(range(len(corrupted)), error_count)
    for idx in indices:
      corrupted[idx] ^= 1
    return corrupted, indices

  def decode_and_correct(self, received_vector: list[int]):
    """Синдромное декодирование и коррекция одиночной ошибки в матрице."""
    data_bits = received_vector[: self.k]
    r_matrix = np.array(data_bits, dtype=int).reshape((self.k1, self.k2))

    rec_p_row = np.array(
        received_vector[self.k : self.k + self.k1], dtype=int
    )
    rec_p_col = np.array(
        received_vector[self.k + self.k1 : self.k + self.k1 + self.k2],
        dtype=int,
    )
    rec_p_all = received_vector[-1]

    # Вычисление синдромов
    calc_p_row = np.sum(r_matrix, axis=1) % 2
    calc_p_col = np.sum(r_matrix, axis=0) % 2
    calc_p_all = np.sum(calc_p_row) % 2

    syn_row = (calc_p_row ^ rec_p_row).tolist()
    syn_col = (calc_p_col ^ rec_p_col).tolist()
    syn_all = calc_p_all ^ rec_p_all

    row_errs = [i for i, v in enumerate(syn_row) if v != 0]
    col_errs = [j for j, v in enumerate(syn_col) if v != 0]

    detected = (len(row_errs) > 0) or (len(col_errs) > 0) or (syn_all != 0)
    corrected_matrix = r_matrix.copy()
    corrected = False

    # Исправление одиночной ошибки в информационном поле
    if len(row_errs) == 1 and len(col_errs) == 1:
      r_idx, c_idx = row_errs[0], col_errs[0]
      corrected_matrix[r_idx, c_idx] ^= 1
      corrected = True
    elif not detected:
      corrected = True  # Ошибок не было изначально

    corrected_data = corrected_matrix.flatten().tolist()
    return {
        "detected": detected,
        "corrected": corrected,
        "corrected_data": corrected_data,
        "row_syndrome": syn_row,
        "col_syndrome": syn_col,
    }


def run_experiment(k1=4, k2=6, trials=1000, max_errors=3):
  """Экспериментальная оценка корректирующей способности (п. 6 практического задания)."""
  codec = IterativeCode2D(k1, k2)
  print(f"=== Результаты испытаний (матрица {k1}x{k2}, k={k1*k2}) ===")

  for err_count in range(1, max_errors + 1):
    n1 = trials  # Общее число испытаний с данной кратностью
    n2 = 0  # Число верно обнаруженных ошибок
    n3 = 0  # Число полностью исправленных сообщений

    for _ in range(trials):
      # Генерируем случайное слово
      src_data = [random.randint(0, 1) for _ in range(codec.k)]
      encoded = codec.encode(src_data)

      corrupted, _ = codec.introduce_errors(
          encoded["full_vector"], error_count=err_count
      )
      res = codec.decode_and_correct(corrupted)

      if res["detected"]:
        n2 += 1
      if res["corrected_data"] == src_data:
        n3 += 1

    print(
        f"Кратность ошибки {err_count}: "
        f"Обнаружено N2/N1 = {n2/n1:.4f} ({n2}/{n1}), "
        f"Исправлено N3/N1 = {n3/n1:.4f} ({n3}/{n1})"
    )


if __name__ == "__main__":
  # 1. Демонстрация единичного прогона
  codec = IterativeCode2D(k1=4, k2=6)
  sample_data = [
      1,
      0,
      1,
      1,
      0,
      0,
      0,
      1,
      1,
      0,
      1,
      0,
      1,
      1,
      0,
      0,
      1,
      1,
      0,
      0,
      1,
      1,
      0,
      1,
  ]

  encoded = codec.encode(sample_data)
  print("Исходная матрица:")
  print(encoded["matrix"])
  print("Паритеты строк:", encoded["p_row"])
  print("Паритеты столбцов:", encoded["p_col"])

  # Внесение 1 ошибки
  corrupted, err_pos = codec.introduce_errors(
      encoded["full_vector"], error_count=1
  )
  print(f"\nВнесена 1 ошибка в позицию: {err_pos}")

  result = codec.decode_and_correct(corrupted)
  print(f"Ошибка обнаружена: {result['detected']}")
  print(f"Успешно исправлена: {result['corrected_data'] == sample_data}")

  print()
  # 2. Статистический эксперимент
  run_experiment(k1=4, k2=6, trials=1000, max_errors=3)