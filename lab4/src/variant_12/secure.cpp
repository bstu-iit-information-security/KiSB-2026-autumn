#include "secure.hpp"

#include <cstring>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#else
#include <cerrno>
#include <sys/random.h>
#endif

namespace lab4 {
namespace {
void erase(Byte* memory, std::size_t size) noexcept {
    volatile Byte* target = memory;
    for (std::size_t i = 0; i < size; ++i) target[i] = 0;
}

bool os_random(void*, Byte* output, std::size_t size) {
#ifdef _WIN32
    return BCryptGenRandom(nullptr, output, static_cast<ULONG>(size),
                           BCRYPT_USE_SYSTEM_PREFERRED_RNG) == 0;
#else
    std::size_t written = 0;
    while (written < size) {
        const auto count = getrandom(output + written, size - written, 0);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return false;
        written += static_cast<std::size_t>(count);
    }
    return true;
#endif
}

void conditional_swap(Point& a, Point& b, std::uint32_t bit) noexcept {
    const auto saved_a = a;
    a = point_select(a, b, bit);
    b = point_select(b, saved_a, bit);
}
}

NonceResult select_nonce(const NonceBatch& batch, const Modulus& order) noexcept {
    NonceResult result{};
    std::uint32_t found = 0;
    for (std::size_t i = 0; i < nonce_attempts; ++i) {
        Bytes32 bytes{};
        std::memcpy(bytes.data(), batch.data() + 32 * i, bytes.size());
        const auto candidate = from_le(bytes);
        const auto valid = nonzero(candidate) & less(candidate, order.value);
        const auto take = valid & (found ^ 1U);
        result.value = select(result.value, candidate, take);
        found |= valid;
        ++result.candidates;
        result.limb_comparisons += candidate.words.size();
        erase(bytes.data(), bytes.size());
    }
    result.ok = found != 0;
    return result;
}

NonceResult generate_nonce(const Modulus& order, Entropy entropy) noexcept {
    NonceBatch batch{};
    if (!entropy.fill || !entropy.fill(entropy.state, batch.data(), batch.size())) {
        erase(batch.data(), batch.size());
        return {};
    }
    const auto result = select_nonce(batch, order);
    erase(batch.data(), batch.size());
    return result;
}

Entropy system_entropy() noexcept {
    return {os_random, nullptr};
}

Point multiply_secret(const Curve& c, const UInt256& scalar, const Point& point,
                      MultiplyStats* stats) noexcept {
    Point r0{}, r1 = point;
    MultiplyStats operations{};
    for (int i = 255; i >= 0; --i) {
        const auto bit = (scalar.words[i / 32] >> (i % 32)) & 1U;
        conditional_swap(r0, r1, bit);
        r1 = point_add(c, r0, r1);
        ++operations.additions;
        r0 = point_double(c, r0);
        ++operations.doublings;
        conditional_swap(r0, r1, bit);
        ++operations.bits;
    }
    if (stats) *stats = operations;
    return r0;
}
}
