#pragma once
#include "linear_code.hpp"

// Наименьшее r, при котором 2^r >= k + r + 1.
inline int hamming_check_count(int k) {
    int r = 1;
    while ((1 << r) < k + r + 1) ++r;
    return r;
}

inline long long binomial(int n, int m) {
    long long result = 1;
    for (int i = 1; i <= m; ++i) result = result * (n - m + i) / i;
    return result;
}

inline int bit_count(unsigned value) {
    int count = 0;
    for (; value != 0; value >>= 1) count += value & 1u;
    return count;
}

// Столбцы P' — двоичные записи чисел веса 2, затем 3 и т. д. в порядке возрастания
// (3 = 00011, 5 = 00101, 6 = 00110, ...). Для d_min = 4 добавляется строка
// общей чётности, сразу приведённая к каноническому виду (сумма всех строк).
inline void build_hamming(LinearCode& code, int k, int d_min) {
    const int base_r = hamming_check_count(k);
    code = LinearCode{};
    code.k = k;
    code.r = base_r + (d_min == 4 ? 1 : 0);
    code.n = k + code.r;

    int column = 0;
    for (int weight = 2; weight <= base_r && column < k; ++weight)
        for (unsigned number = 1; number < (1u << base_r) && column < k; ++number) {
            if (bit_count(number) != weight) continue;
            for (int i = 0; i < base_r; ++i)
                code.H[i][column] = static_cast<std::uint8_t>((number >> (base_r - 1 - i)) & 1u);
            ++column;
        }

    if (d_min == 4)
        for (int j = 0; j < k; ++j) {
            std::uint8_t parity = 0;
            for (int i = 0; i < base_r; ++i) parity ^= code.H[i][j];
            code.H[base_r][j] = parity ^ 1;
        }
    code.fill_identity_part();
}
