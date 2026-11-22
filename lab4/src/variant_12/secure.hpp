#pragma once

#include "curve.hpp"

namespace lab4 {
constexpr std::size_t nonce_attempts = 100;
using NonceBatch = std::array<Byte, nonce_attempts * 32>;
using FillRandom = bool (*)(void* state, Byte* output, std::size_t size);

struct Entropy {
    FillRandom fill;
    void* state;
};
struct NonceResult {
    UInt256 value{};
    bool ok = false;
    std::size_t candidates = 0;
    std::size_t limb_comparisons = 0;
};
struct MultiplyStats {
    std::size_t bits = 0;
    std::size_t additions = 0;
    std::size_t doublings = 0;
};

NonceResult select_nonce(const NonceBatch& batch, const Modulus& order) noexcept;
NonceResult generate_nonce(const Modulus& order, Entropy entropy) noexcept;
Entropy system_entropy() noexcept;
Point multiply_secret(const Curve& curve, const UInt256& scalar, const Point& point,
                      MultiplyStats* stats = nullptr) noexcept;
}
