#pragma once
// Вариант 8, этап 2: тест на основе малой теоремы Ферма.
// Если n простое, то a^(n-1) = 1 (mod n) для любого a, взаимно простого с n.

#include <cstdint>
#include <utility>

#include "additive_generator.hpp"
#include "bignum.hpp"

// Источник случайных бит на основе генератора этапа 1.
// Выход генератора -- число 0..29. Используются только значения 0..15
// (ровно 4 бита), остальные отбрасываются -- так биты не смещаются.
class RandomBits {
public:
    explicit RandomBits(AdditiveGenerator& g) : g_(g) {}

    uint32_t next4() {
        for (;;) {
            const uint32_t x = g_.next();
            if (x < 16) return x;
        }
    }

    uint32_t next32() {
        uint32_t r = 0;
        for (int i = 0; i < 8; ++i) r = (r << 4) | next4();
        return r;
    }

private:
    AdditiveGenerator& g_;
};

// НОД бинарным алгоритмом Евклида (сдвиги и вычитания вместо деления).
inline BigNum gcd(BigNum a, BigNum b) {
    if (a.is_zero()) return b;
    if (b.is_zero()) return a;
    int shift = 0;
    while (!a.is_odd() && !b.is_odd()) {
        shr1(a);
        shr1(b);
        ++shift;
    }
    while (!a.is_odd()) shr1(a);
    while (!b.is_zero()) {
        while (!b.is_odd()) shr1(b);
        if (compare(a, b) > 0) std::swap(a, b);
        sub(b, a, b);
    }
    while (shift-- > 0) shl1(a);
    return a;
}

// Случайное основание a из [2; n-2].
inline BigNum random_base(const BigNum& n, RandomBits& rnd) {
    const uint32_t r = rnd.next32();
    if (n.bit_length() <= 64) return BigNum::from_u64(2 + r % (n.low64() - 3));
    return BigNum::from_u64(2 + static_cast<uint64_t>(r));
}

// true -- "вероятно простое", false -- "составное".
inline bool fermat_test(const BigNum& n, int rounds, RandomBits& rnd) {
    const BigNum one = BigNum::from_u64(1);
    if (n.bit_length() <= 3) return n == BigNum::from_u64(2) ||
                                    n == BigNum::from_u64(3) ||
                                    n == BigNum::from_u64(5) ||
                                    n == BigNum::from_u64(7);
    if (!n.is_odd()) return false;

    BigNum n_minus_1;
    sub(n, one, n_minus_1);

    for (int r = 0; r < rounds; ++r) {
        const BigNum a = random_base(n, rnd);
        if (gcd(a, n) != one) return false;               // шаг 1: НОД(a, n) = 1
        if (pow_mod(a, n_minus_1, n) != one) return false; // шаги 2-3: a^(n-1) mod n
    }
    return true;                                           // шаг 4: все раунды пройдены
}
