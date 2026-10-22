import random


class IterativeCode:
    def __init__(self, k1=4, k2=6):
        self.k1 = k1
        self.k2 = k2
        self.k = k1 * k2  # 24 бита
        self.num_diags = self.k1 + self.k2 - 1

    def _get_diag_index(self, r, c):
        return r - c + (self.k2 - 1)

    def generate_random_word(self):
        return [random.choice([0, 1]) for _ in range(self.k)]

    def encode(self, data, num_groups):

        assert len(data) == self.k
        matrix = [data[i * self.k2:(i + 1) * self.k2] for i in range(self.k1)]

        p1_row = [sum(row) % 2 for row in matrix]

        p2_col = [sum(matrix[r][c] for r in range(self.k1)) % 2 for c in range(self.k2)]

        encoded = data + p1_row + p2_col

        if num_groups == 3:
            p3_diag = [0] * self.num_diags
            for r in range(self.k1):
                for c in range(self.k2):
                    d_idx = self._get_diag_index(r, c)
                    p3_diag[d_idx] ^= matrix[r][c]
            encoded += p3_diag

        return encoded, matrix

    def apply_errors(self, codeword, num_errors):
        corrupted = codeword.copy()
        n = len(corrupted)
        error_positions = random.sample(range(n), num_errors)
        for pos in error_positions:
            corrupted[pos] ^= 1
        return corrupted, error_positions

    def decode(self, received, num_groups):
        recv_data = received[:self.k]
        recv_p1 = received[self.k: self.k + self.k1]
        recv_p2 = received[self.k + self.k1: self.k + self.k1 + self.k2]

        if num_groups == 3:
            recv_p3 = received[self.k + self.k1 + self.k2:]

        matrix = [recv_data[i * self.k2:(i + 1) * self.k2] for i in range(self.k1)]

        max_iterations = 10
        for iteration in range(max_iterations):
            cur_p1 = [sum(row) % 2 for row in matrix]
            cur_p2 = [sum(matrix[r][c] for r in range(self.k1)) % 2 for c in range(self.k2)]

            s1 = [recv_p1[i] ^ cur_p1[i] for i in range(self.k1)]
            s2 = [recv_p2[i] ^ cur_p2[i] for i in range(self.k2)]

            s3 = [0] * self.num_diags
            if num_groups == 3:
                cur_p3 = [0] * self.num_diags
                for r in range(self.k1):
                    for c in range(self.k2):
                        d_idx = self._get_diag_index(r, c)
                        cur_p3[d_idx] ^= matrix[r][c]
                s3 = [recv_p3[i] ^ cur_p3[i] for i in range(self.num_diags)]

            total_syndromes = sum(s1) + sum(s2) + sum(s3)
            if total_syndromes == 0:
                break

            max_fails = 0
            best_bit = None

            for r in range(self.k1):
                for c in range(self.k2):
                    fails = s1[r] + s2[c]
                    if num_groups == 3:
                        d_idx = self._get_diag_index(r, c)
                        fails += s3[d_idx]

                    if fails > max_fails:
                        max_fails = fails
                        best_bit = (r, c)

            if best_bit and max_fails >= 2:
                r, c = best_bit
                matrix[r][c] ^= 1
            else:
                break

        corrected_data = []
        for row in matrix:
            corrected_data.extend(row)

        return corrected_data, total_syndromes > 0

    def analyze(self, max_errors=4, trials=1000):
        print(f"\n--- Анализ корректирующей способности (k={self.k}, испытаний={trials}) ---")

        for groups in [2, 3]:
            print(f"\nГруппы паритетов: {groups} " + (
                "(Строки, Столбцы)" if groups == 2 else "(Строки, Столбцы, Диагонали)"))
            print(f"{'Кратность ошибки':<20} | {'Обнаружено (%)':<15} | {'Скорректировано (%)'}")
            print("-" * 60)

            for num_errors in range(1, max_errors + 1):
                detected_count = 0
                corrected_count = 0

                for _ in range(trials):
                    data = self.generate_random_word()
                    encoded, _ = self.encode(data, groups)

                    corrupted, _ = self.apply_errors(encoded, num_errors)

                    decoded_data, has_syndromes = self.decode(corrupted, groups)

                    if has_syndromes or decoded_data != data:
                        detected_count += 1

                    if decoded_data == data:
                        corrected_count += 1

                det_percent = (detected_count / trials) * 100
                corr_percent = (corrected_count / trials) * 100
                print(f"{num_errors:<20} | {det_percent:<15.1f} | {corr_percent:.1f}")


def main():
    coder = IterativeCode(k1=4, k2=6)
    data = coder.generate_random_word()

    print("=== Демонстрация работы (2 группы паритетов) ===")
    print(f"1) Информационное слово (X_k): {''.join(map(str, data))}")

    encoded, matrix = coder.encode(data, num_groups=2)
    print("   Матрица 4x6:")
    for row in matrix:
        print("   " + str(row))

    print(f"3) Кодовое слово (X_n): {''.join(map(str, encoded))}")


    corrupted, err_pos = coder.apply_errors(encoded, num_errors=1)
    print(f"4) Слово с ошибкой (Y_n) (позиции {err_pos}): {''.join(map(str, corrupted))}")


    corrected, _ = coder.decode(corrupted, num_groups=2)
    print(f"5) Исправленное слово (Y_n'): {''.join(map(str, corrected))}")
    print(f"   Успешно исправлено: {corrected == data}")


    coder.analyze(max_errors=4, trials=1000)


if __name__ == "__main__":
    main()