#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

using Block = std::array<uint8_t, 16>;
using Bytes = std::vector<uint8_t>;

Block xor_blocks(const Block& lhs, const Block& rhs);
Block block_at(const Bytes& data, size_t offset);
std::string to_hex(const uint8_t* data, size_t length);
std::string to_hex(const Block& block);

class AES128 {
public:
    explicit AES128(const Block& key);

    Block encrypt_block(const Block& plaintext) const;
    Block decrypt_block(const Block& ciphertext) const;

private:
    std::array<uint8_t, 256> sbox_{};
    std::array<uint8_t, 256> inverse_sbox_{};
    std::array<uint8_t, 176> round_keys_{};

    void add_round_key(Block& state, unsigned round) const;
    void sub_bytes(Block& state, bool inverse) const;
    void shift_rows(Block& state, bool inverse) const;
    void mix_columns(Block& state, bool inverse) const;
};
