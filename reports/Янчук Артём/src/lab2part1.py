import random

def text_to_bits(text):

    encoded = text.encode('cp1251', errors='ignore')
    bits = []
    for byte in encoded:
        bits.extend([int(b) for b in format(byte, '08b')])
    return bits

def calculate_r(k):

    r = 2
    while (2**r) < (k + r + 1):
        r += 1
    return r

def generate_hamming_matrix(k, r):

    n = k + r

    I_cols = [[1 if i == j else 0 for j in range(r)] for i in range(r)]

    P_cols = []
    for i in range(1, 2**r):
        col = [int(x) for x in format(i, f'0{r}b')]
        if sum(col) >= 2:
            P_cols.append(col)
            if len(P_cols) == k:
                break

    if len(P_cols) < k:
        raise ValueError("Не хватает комбинаций для матрицы. Увеличьте r.")

    H_cols = P_cols + I_cols
    return H_cols, P_cols

def print_matrix(H_cols, r, n):
    for row_idx in range(r):
        row = [H_cols[col_idx][row_idx] for col_idx in range(n)]
        print("  [" + " ".join(map(str, row)) + "]")

def simulate_transmission(X, num_errors):
    Y = X.copy()
    n = len(Y)
    error_positions = random.sample(range(n), num_errors)
    for pos in error_positions:
        Y[pos] ^= 1
    return Y, error_positions

def main():
    text_message = "Кот"
    Y_k = text_to_bits(text_message)
    k = len(Y_k)

    r = calculate_r(k)
    n = k + r

    print("=== ЭТАП 1: Параметры и генерация ===")
    print(f"Исходное сообщение: '{text_message}'")
    print(f"Информационное слово (Y_k): {''.join(map(str, Y_k))}")
    print(f"Параметры: K = {k}, r = {r}, n = {n}")

    H_cols, P_cols = generate_hamming_matrix(k, r)
    print("\nПроверочная матрица Хемминга H (r x n):")
    print_matrix(H_cols, r, n)

    Y_r = []
    for i in range(r):

        bit = sum(Y_k[j] * P_cols[j][i] for j in range(k)) % 2
        Y_r.append(bit)

    X = Y_k + Y_r
    print(f"\nИзбыточные символы (Y_r): {''.join(map(str, Y_r))}")
    print(f"Сформированное кодовое слово (X): {''.join(map(str, X))}")

    for num_errors in [0, 1, 2]:
        print(f"\n{'='*40}")
        print(f"=== ТЕСТ: Передача с {num_errors} ошибками ===")

        Y_n, true_err_pos = simulate_transmission(X, num_errors)
        Y_k_recv = Y_n[:k]
        Y_r_recv = Y_n[k:]

        print(f"Принятое слово (Y_n): {''.join(map(str, Y_n))}")
        print(f"Принятые избыточные (Y_r): {''.join(map(str, Y_r_recv))}")
        if num_errors > 0:
            print(f"Фактические позиции ошибок (индексы): {true_err_pos}")

        Y_r_prime = []
        for i in range(r):
            bit = sum(Y_k_recv[j] * P_cols[j][i] for j in range(k)) % 2
            Y_r_prime.append(bit)
        print(f"Вычисленные избыточные (Y_r'): {''.join(map(str, Y_r_prime))}")

        S = [(Y_r_recv[i] ^ Y_r_prime[i]) for i in range(r)]
        print(f"Синдром (S): {''.join(map(str, S))}")

        E_n = [0] * n
        if sum(S) == 0:
            print("Синдром равен 0 Ошибок нет")
            print(f"Вектор ошибки (E_n): {''.join(map(str, E_n))}")
        else:
            print("Синдром не равен 0 ошибка")

            if S in H_cols:
                error_idx = H_cols.index(S)
                E_n[error_idx] = 1
                print(f"Вектор ошибки (E_n): {''.join(map(str, E_n))}")

                corrected_Y_n = [(Y_n[i] ^ E_n[i]) for i in range(n)]
                print(f"Исправленное слово:  {''.join(map(str, corrected_Y_n))}")

                if num_errors == 1:
                    print("Одиночная ошибка исправлена")
                elif num_errors == 2:
                    print("Было 2 ошибки")

            else:

                print("Синдром не найден")

if __name__ == "__main__":
    main()