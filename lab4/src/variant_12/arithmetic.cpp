#include "arithmetic.hpp"

#include <cstring>

namespace lab4 {
namespace {
using Word = std::uint32_t;
using Wide = std::uint64_t;

Word subtract(const UInt256& a, const UInt256& b, UInt256& result) noexcept {
    Wide borrow = 0;
    for (std::size_t i = 0; i < 8; ++i) {
        const Wide difference = Wide{a.words[i]} - b.words[i] - borrow;
        result.words[i] = static_cast<Word>(difference);
        borrow = difference >> 63;
    }
    return static_cast<Word>(borrow);
}

UInt256 montgomery(const UInt256& a, const UInt256& b, const Modulus& m) noexcept {
    std::array<Word, 17> product{};
    for (std::size_t i = 0; i < 8; ++i) {
        Wide carry = 0;
        for (std::size_t j = 0; j < 8; ++j) {
            const Wide sum = Wide{a.words[i]} * b.words[j] + product[i + j] + carry;
            product[i + j] = static_cast<Word>(sum);
            carry = sum >> 32;
        }
        product[i + 8] = static_cast<Word>(carry);
    }
    for (std::size_t i = 0; i < 8; ++i) {
        const Word factor = product[i] * m.negative_inverse;
        Wide carry = 0;
        for (std::size_t j = 0; j < 8; ++j) {
            const Wide sum = Wide{factor} * m.value.words[j] + product[i + j] + carry;
            product[i + j] = static_cast<Word>(sum);
            carry = sum >> 32;
        }
        for (std::size_t j = i + 8; j < product.size(); ++j) {
            const Wide sum = Wide{product[j]} + carry;
            product[j] = static_cast<Word>(sum);
            carry = sum >> 32;
        }
    }
    UInt256 result{};
    for (std::size_t i = 0; i < 8; ++i) result.words[i] = product[i + 8];
    UInt256 reduced{};
    const Word borrow = subtract(result, m.value, reduced);
    return select(result, reduced, product[16] | (borrow ^ 1U));
}
}

UInt256 from_u32(std::uint32_t value) noexcept {
    UInt256 result{};
    result.words[0] = value;
    return result;
}

bool parse_hex(const char* hex, UInt256& result) noexcept {
    if (!hex) return false;
    const auto length = std::strlen(hex);
    if (length == 0 || length > 64) return false;
    UInt256 parsed{};
    for (std::size_t i = 0; i < length; ++i) {
        const char c = hex[length - 1 - i];
        unsigned digit = 16;
        if (c >= '0' && c <= '9') digit = static_cast<unsigned>(c - '0');
        if (c >= 'a' && c <= 'f') digit = static_cast<unsigned>(c - 'a' + 10);
        if (c >= 'A' && c <= 'F') digit = static_cast<unsigned>(c - 'A' + 10);
        if (digit == 16) return false;
        parsed.words[i / 8] |= digit << (4 * (i % 8));
    }
    result = parsed;
    return true;
}

UInt256 from_le(const Bytes32& bytes) noexcept {
    UInt256 result{};
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        result.words[i / 4] |= Word{bytes[i]} << (8 * (i % 4));
    }
    return result;
}

Bytes32 to_le(const UInt256& value) noexcept {
    Bytes32 result{};
    for (std::size_t i = 0; i < result.size(); ++i) {
        result[i] = static_cast<Byte>(value.words[i / 4] >> (8 * (i % 4)));
    }
    return result;
}

void to_hex(const UInt256& value, char (&hex)[65]) noexcept {
    constexpr char digits[] = "0123456789abcdef";
    const auto bytes = to_le(value);
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        const auto byte = bytes[31 - i];
        hex[2 * i] = digits[byte >> 4];
        hex[2 * i + 1] = digits[byte & 15U];
    }
    hex[64] = 0;
}

std::uint32_t nonzero(const UInt256& value) noexcept {
    Word combined = 0;
    for (const auto word : value.words) combined |= word;
    return (combined | (0U - combined)) >> 31;
}

std::uint32_t equal(const UInt256& a, const UInt256& b) noexcept {
    UInt256 difference{};
    for (std::size_t i = 0; i < 8; ++i) difference.words[i] = a.words[i] ^ b.words[i];
    return nonzero(difference) ^ 1U;
}

std::uint32_t less(const UInt256& a, const UInt256& b) noexcept {
    UInt256 difference{};
    return subtract(a, b, difference);
}

UInt256 select(const UInt256& a, const UInt256& b, std::uint32_t choose_b) noexcept {
    const Word mask = 0U - choose_b;
    UInt256 result{};
    for (std::size_t i = 0; i < 8; ++i) {
        result.words[i] = a.words[i] ^ ((a.words[i] ^ b.words[i]) & mask);
    }
    return result;
}

UInt256 reduce_once(const UInt256& value, const Modulus& m) noexcept {
    UInt256 reduced{};
    const auto borrow = subtract(value, m.value, reduced);
    return select(reduced, value, borrow);
}

UInt256 mod_add(const UInt256& a, const UInt256& b, const Modulus& m) noexcept {
    UInt256 sum{}, reduced{};
    Wide carry = 0;
    for (std::size_t i = 0; i < 8; ++i) {
        const Wide value = Wide{a.words[i]} + b.words[i] + carry;
        sum.words[i] = static_cast<Word>(value);
        carry = value >> 32;
    }
    const auto borrow = subtract(sum, m.value, reduced);
    return select(sum, reduced, static_cast<Word>(carry) | (borrow ^ 1U));
}

UInt256 mod_sub(const UInt256& a, const UInt256& b, const Modulus& m) noexcept {
    UInt256 result{};
    const Word mask = 0U - subtract(a, b, result);
    Wide carry = 0;
    for (std::size_t i = 0; i < 8; ++i) {
        const Wide sum = Wide{result.words[i]} + (m.value.words[i] & mask) + carry;
        result.words[i] = static_cast<Word>(sum);
        carry = sum >> 32;
    }
    return result;
}

Modulus make_modulus(const UInt256& value) noexcept {
    Modulus m{value, {}, {}, 0};
    Word inverse = 1;
    for (unsigned i = 0; i < 5; ++i) inverse *= 2U - value.words[0] * inverse;
    m.negative_inverse = 0U - inverse;
    UInt256 power = from_u32(1);
    for (unsigned i = 0; i < 256; ++i) power = mod_add(power, power, m);
    m.one = power;
    for (unsigned i = 0; i < 256; ++i) power = mod_add(power, power, m);
    m.r2 = power;
    return m;
}

UInt256 mod_mul(const UInt256& a, const UInt256& b, const Modulus& m) noexcept {
    return montgomery(montgomery(a, m.r2, m), b, m);
}

UInt256 mod_inverse(const UInt256& value, const Modulus& m) noexcept {
    UInt256 exponent{};
    subtract(m.value, from_u32(2), exponent);
    const auto base = montgomery(value, m.r2, m);
    auto result = m.one;
    for (int i = 255; i >= 0; --i) {
        result = montgomery(result, result, m);
        const auto product = montgomery(result, base, m);
        const auto bit = (exponent.words[i / 32] >> (i % 32)) & 1U;
        result = select(result, product, bit);
    }
    return montgomery(result, from_u32(1), m);
}
}
