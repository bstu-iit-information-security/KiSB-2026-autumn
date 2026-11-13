#pragma once
#include <array>
#include <cstdint>
#include <random>
#include <utility>

// Ёмкости хватает на сообщение до 32 байт (код Хемминга, n <= 266)
// и на все итеративные коды варианта (r <= 58, n <= 82).
constexpr int kMaxR = 64;
constexpr int kMaxN = 272;

using Bits = std::array<std::uint8_t, kMaxN>;    // слово X_k, X_n, Y_n, E_n
using Checks = std::array<std::uint8_t, kMaxR>;  // проверочные символы, синдром

// Линейный блочный код в систематическом виде H = [P' | I]:
// столбцы 0..k-1 — информационные символы, k..n-1 — проверочные.
struct LinearCode {
    int k = 0;
    int r = 0;
    int n = 0;
    std::array<Bits, kMaxR> H{};

    void fill_identity_part() {
        for (int i = 0; i < r; ++i)
            for (int j = k; j < n; ++j) H[i][j] = (j - k == i) ? 1 : 0;
    }

    Checks check_bits(const Bits& word) const {
        Checks result{};
        for (int i = 0; i < r; ++i) {
            std::uint8_t sum = 0;
            for (int j = 0; j < k; ++j) sum ^= H[i][j] & word[j];
            result[i] = sum;
        }
        return result;
    }

    Bits encode(const Bits& info) const {
        Bits word{};
        for (int j = 0; j < k; ++j) word[j] = info[j];
        const Checks check = check_bits(info);
        for (int i = 0; i < r; ++i) word[k + i] = check[i];
        return word;
    }

    // S = Y_r xor Y_r', что совпадает с S = H * Y_n^T
    Checks syndrome(const Bits& received) const {
        const Checks recomputed = check_bits(received);
        Checks s{};
        for (int i = 0; i < r; ++i) s[i] = received[k + i] ^ recomputed[i];
        return s;
    }

    bool is_zero(const Checks& s) const {
        for (int i = 0; i < r; ++i)
            if (s[i]) return false;
        return true;
    }

    bool column_equals(int column, const Checks& s) const {
        for (int i = 0; i < r; ++i)
            if (H[i][column] != s[i]) return false;
        return true;
    }
};

enum class Status { NoError, Corrected, Uncorrectable };

struct Decoded {
    Status status = Status::NoError;
    Bits error{};      // E_n — найденный вектор ошибки
    Bits corrected{};  // Y_n' = Y_n xor E_n
    int error_weight = 0;
};

// Код Хемминга: ненулевой синдром сравнивается со столбцами H.
inline Decoded syndrome_decode(const LinearCode& code, const Bits& received) {
    Decoded result;
    result.corrected = received;
    const Checks s = code.syndrome(received);
    if (code.is_zero(s)) return result;

    int position = -1;
    for (int j = 0; j < code.n; ++j)
        if (code.column_equals(j, s)) position = j;

    if (position < 0) {
        result.status = Status::Uncorrectable;
        return result;
    }
    result.status = Status::Corrected;
    result.error[position] = 1;
    result.corrected[position] ^= 1;
    result.error_weight = 1;
    return result;
}

// Итеративный код: побитовое инвертирование. На каждом шаге инвертируется бит,
// у которого нарушенных проверок больше всего по сравнению с выполненными.
inline Decoded bit_flip_decode(const LinearCode& code, const Bits& received) {
    Decoded result;
    Bits word = received;
    while (true) {
        const Checks s = code.syndrome(word);
        if (code.is_zero(s)) break;

        int best_position = -1;
        int best_score = 0;
        for (int j = 0; j < code.n; ++j) {
            int score = 0;  // нарушенные минус выполненные
            for (int i = 0; i < code.r; ++i)
                if (code.H[i][j]) score += s[i] ? 1 : -1;
            if (score > best_score) {
                best_score = score;
                best_position = j;
            }
        }
        if (best_position < 0) {
            result.status = Status::Uncorrectable;
            result.corrected = received;
            return result;
        }
        word[best_position] ^= 1;
    }
    result.corrected = word;
    for (int j = 0; j < code.n; ++j) {
        result.error[j] = received[j] ^ word[j];
        result.error_weight += result.error[j];
    }
    result.status = result.error_weight == 0 ? Status::NoError : Status::Corrected;
    return result;
}

inline Bits random_info(int k, std::mt19937& rng) {
    std::uniform_int_distribution<int> bit(0, 1);
    Bits info{};
    for (int j = 0; j < k; ++j) info[j] = static_cast<std::uint8_t>(bit(rng));
    return info;
}

// Вектор ошибки веса count: различные случайные позиции из n.
inline Bits random_errors(int n, int count, std::mt19937& rng) {
    std::array<int, kMaxN> positions{};
    for (int j = 0; j < n; ++j) positions[j] = j;
    Bits error{};
    for (int t = 0; t < count; ++t) {
        std::uniform_int_distribution<int> pick(t, n - 1);
        std::swap(positions[t], positions[pick(rng)]);
        error[positions[t]] = 1;
    }
    return error;
}

inline Bits xor_bits(const Bits& a, const Bits& b) {
    Bits result{};
    for (int j = 0; j < kMaxN; ++j) result[j] = a[j] ^ b[j];
    return result;
}
