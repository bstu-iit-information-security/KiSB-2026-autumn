#pragma once

#include <array>
#include <cstdint>

namespace lab3 {
using Byte = std::uint8_t;
using Block = std::array<Byte, 16>;
using Key = std::array<Byte, 32>;

Block encrypt_block(const Block& input, const Key& key) noexcept;
Block decrypt_block(const Block& input, const Key& key) noexcept;
}
