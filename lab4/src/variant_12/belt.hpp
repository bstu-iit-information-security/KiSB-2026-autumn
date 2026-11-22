#pragma once

#include "arithmetic.hpp"

namespace lab4::belt {
using Block = std::array<Byte, 16>;
using Key = Bytes32;
Block encrypt_block(const Block& input, const Key& key) noexcept;
}
