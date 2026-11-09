#pragma once
// Этап 1: проверка гипотезы о равномерном распределении
// по критерию согласия Пирсона (хи-квадрат).

#include <array>
#include <cstdint>

#include "additive_generator.hpp"

// Табличное критическое значение хи-квадрат для df = N - 1 = 29, alpha = 0.05.
const double kChi2Critical = 42.557;

// Частоты символов 0..N-1 в выборке длины sample.
inline std::array<uint32_t, kN> frequencies(AdditiveGenerator g, uint32_t sample) {
    std::array<uint32_t, kN> counts{};
    g.reset();
    for (uint32_t i = 0; i < sample; ++i) ++counts[g.next()];
    return counts;
}

struct Chi2Result {
    double chi2;
    bool uniform;  // true -- гипотеза о равномерности не отвергается
};

inline Chi2Result chi_square(const AdditiveGenerator& g, uint32_t sample) {
    const std::array<uint32_t, kN> counts = frequencies(g, sample);
    const double expected = static_cast<double>(sample) / kN;
    double chi2 = 0.0;
    for (uint32_t k = 0; k < kN; ++k) {
        const double d = counts[k] - expected;
        chi2 += d * d / expected;
    }
    return Chi2Result{chi2, chi2 <= kChi2Critical};
}
