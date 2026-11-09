#pragma once

#include <array>
#include <cstdint>

namespace lab3 {
using Byte = std::uint8_t;
using Block = std::array<Byte, 16>;
using Key = std::array<Byte, 32>;

class Belt {
public:
    explicit Belt(const Key& key) noexcept;
    Block encrypt_block(const Block& input) const noexcept;
    Block decrypt_block(const Block& input) const noexcept;
private:
    std::array<std::uint32_t, 56> round_keys_{};
};
}
