#pragma once
// Вариант 8, этап 1: аддитивный генератор
//     x(t+1) = (x(t) + x(t-1)) mod N,   N = 30

#include <cstdint>

const uint32_t kN = 30;  // размер алфавита по варианту

class AdditiveGenerator {
public:
    AdditiveGenerator(uint32_t x0, uint32_t x1)
        : x0_(x0 % kN), x1_(x1 % kN), a_(x0_), b_(x1_) {}

    // Выдаёт очередной член последовательности.
    uint32_t next() {
        const uint32_t out = a_;
        const uint32_t c = (a_ + b_) % kN;
        a_ = b_;
        b_ = c;
        return out;
    }

    void reset() { a_ = x0_; b_ = x1_; }
    bool at_start() const { return a_ == x0_ && b_ == x1_; }

    uint32_t x0() const { return x0_; }
    uint32_t x1() const { return x1_; }

private:
    uint32_t x0_, x1_;  // стартовые значения
    uint32_t a_, b_;    // текущее состояние: (x(t), x(t+1))
};

// Период последовательности: число шагов до возврата в стартовое состояние.
// Переход (a, b) -> (b, (a + b) mod N) обратим, поэтому предпериода нет и
// генератор всегда возвращается в начальное состояние.
inline uint32_t period_of(AdditiveGenerator g) {
    g.reset();
    uint32_t steps = 0;
    do {
        g.next();
        ++steps;
    } while (!g.at_start());
    return steps;
}

struct SeedSearchResult {
    uint32_t max_period = 0;
    uint32_t best_x0 = 0, best_x1 = 0;
    uint32_t pairs_with_max = 0;
};

// Подбор параметров: полный перебор всех N*N стартовых пар (x0, x1).
inline SeedSearchResult find_best_seed() {
    SeedSearchResult r;
    for (uint32_t x0 = 0; x0 < kN; ++x0) {
        for (uint32_t x1 = 0; x1 < kN; ++x1) {
            const uint32_t t = period_of(AdditiveGenerator(x0, x1));
            if (t > r.max_period) {
                r.max_period = t;
                r.best_x0 = x0;
                r.best_x1 = x1;
                r.pairs_with_max = 1;
            } else if (t == r.max_period) {
                ++r.pairs_with_max;
            }
        }
    }
    return r;
}
