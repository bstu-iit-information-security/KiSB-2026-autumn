#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace lab4 {
using Byte = std::uint8_t;
using Bytes32 = std::array<Byte, 32>;

struct UInt256 {
    std::array<std::uint32_t, 8> words{};
};

struct Modulus {
    UInt256 value;
    UInt256 r2;
    UInt256 one;
    std::uint32_t negative_inverse;
};

UInt256 from_u32(std::uint32_t value) noexcept;
bool parse_hex(const char* hex, UInt256& result) noexcept;
UInt256 from_le(const Bytes32& bytes) noexcept;
Bytes32 to_le(const UInt256& value) noexcept;
void to_hex(const UInt256& value, char (&hex)[65]) noexcept;
std::uint32_t nonzero(const UInt256& value) noexcept;
std::uint32_t equal(const UInt256& a, const UInt256& b) noexcept;
std::uint32_t less(const UInt256& a, const UInt256& b) noexcept;
UInt256 select(const UInt256& a, const UInt256& b, std::uint32_t choose_b) noexcept;
Modulus make_modulus(const UInt256& value) noexcept;
UInt256 reduce_once(const UInt256& value, const Modulus& modulus) noexcept;
UInt256 mod_add(const UInt256& a, const UInt256& b, const Modulus& modulus) noexcept;
UInt256 mod_sub(const UInt256& a, const UInt256& b, const Modulus& modulus) noexcept;
UInt256 mod_mul(const UInt256& a, const UInt256& b, const Modulus& modulus) noexcept;
UInt256 mod_inverse(const UInt256& value, const Modulus& modulus) noexcept;
}
