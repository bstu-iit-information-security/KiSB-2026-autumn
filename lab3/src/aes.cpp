#include "aes.hpp"

#include <stdexcept>

namespace {

uint8_t gf_mul(uint8_t a, uint8_t b) {
    uint8_t result = 0;
    for (int i = 0; i < 8; ++i) {
        if (b & 1) result ^= a;
        bool high = (a & 0x80) != 0;
        a = static_cast<uint8_t>(a << 1);
        if (high) a ^= 0x1b;
        b = static_cast<uint8_t>(b >> 1);
    }
    return result;
}

uint8_t rotl8(uint8_t value, int shift) {
    return static_cast<uint8_t>((value << shift) | (value >> (8 - shift)));
}

}  

Block xor_blocks(const Block& lhs, const Block& rhs) {
    Block out{};
    for (size_t i = 0; i < 16; ++i) out[i] = static_cast<uint8_t>(lhs[i] ^ rhs[i]);
    return out;
}

Block block_at(const Bytes& data, size_t offset) {
    if (offset + 16 > data.size()) throw std::out_of_range("short AES block");
    Block block{};
    for (size_t i = 0; i < 16; ++i) block[i] = data[offset + i];
    return block;
}

std::string to_hex(const uint8_t* data, size_t length) {
    static const char digits[] = "0123456789abcdef";
    std::string out;
    out.reserve(length * 2);
    for (size_t i = 0; i < length; ++i) {
        out += digits[data[i] >> 4];
        out += digits[data[i] & 0x0f];
    }
    return out;
}

std::string to_hex(const Block& block) { return to_hex(block.data(), block.size()); }

AES128::AES128(const Block& key) {
    for (unsigned i = 0; i < 256; ++i) {
        uint8_t inverse = 0;
        if (i != 0) {
            for (unsigned j = 1; j < 256; ++j) {
                if (gf_mul(static_cast<uint8_t>(i), static_cast<uint8_t>(j)) == 1) {
                    inverse = static_cast<uint8_t>(j);
                    break;
                }
            }
        }
        uint8_t value = static_cast<uint8_t>(inverse ^ rotl8(inverse, 1) ^
                                             rotl8(inverse, 2) ^ rotl8(inverse, 3) ^
                                             rotl8(inverse, 4) ^ 0x63);
        sbox_[i] = value;
        inverse_sbox_[value] = static_cast<uint8_t>(i);
    }

    for (size_t i = 0; i < 16; ++i) round_keys_[i] = key[i];

    uint8_t rcon = 1;
    for (unsigned word = 4; word < 44; ++word) {
        uint8_t temp[4] = {
            round_keys_[4 * (word - 1) + 0], round_keys_[4 * (word - 1) + 1],
            round_keys_[4 * (word - 1) + 2], round_keys_[4 * (word - 1) + 3]};
        if (word % 4 == 0) {
            uint8_t first = temp[0];
            temp[0] = static_cast<uint8_t>(sbox_[temp[1]] ^ rcon);
            temp[1] = sbox_[temp[2]];
            temp[2] = sbox_[temp[3]];
            temp[3] = sbox_[first];
            rcon = gf_mul(rcon, 2);
        }
        for (unsigned j = 0; j < 4; ++j) {
            round_keys_[4 * word + j] =
                static_cast<uint8_t>(round_keys_[4 * (word - 4) + j] ^ temp[j]);
        }
    }
}

void AES128::add_round_key(Block& state, unsigned round) const {
    for (size_t i = 0; i < 16; ++i) {
        state[i] = static_cast<uint8_t>(state[i] ^ round_keys_[16 * round + i]);
    }
}

void AES128::sub_bytes(Block& state, bool inverse) const {
    for (size_t i = 0; i < 16; ++i) {
        state[i] = inverse ? inverse_sbox_[state[i]] : sbox_[state[i]];
    }
}

void AES128::shift_rows(Block& state, bool inverse) const {
    Block copy = state;
    for (unsigned row = 0; row < 4; ++row) {
        for (unsigned col = 0; col < 4; ++col) {
            unsigned from = inverse ? (col + 4 - row) % 4 : (col + row) % 4;
            state[4 * col + row] = copy[4 * from + row];
        }
    }
}

void AES128::mix_columns(Block& state, bool inverse) const {
    for (unsigned col = 0; col < 4; ++col) {
        uint8_t a = state[4 * col + 0];
        uint8_t b = state[4 * col + 1];
        uint8_t c = state[4 * col + 2];
        uint8_t d = state[4 * col + 3];
        if (inverse) {
            state[4 * col + 0] = static_cast<uint8_t>(gf_mul(a, 14) ^ gf_mul(b, 11) ^
                                                      gf_mul(c, 13) ^ gf_mul(d, 9));
            state[4 * col + 1] = static_cast<uint8_t>(gf_mul(a, 9) ^ gf_mul(b, 14) ^
                                                      gf_mul(c, 11) ^ gf_mul(d, 13));
            state[4 * col + 2] = static_cast<uint8_t>(gf_mul(a, 13) ^ gf_mul(b, 9) ^
                                                      gf_mul(c, 14) ^ gf_mul(d, 11));
            state[4 * col + 3] = static_cast<uint8_t>(gf_mul(a, 11) ^ gf_mul(b, 13) ^
                                                      gf_mul(c, 9) ^ gf_mul(d, 14));
        } else {
            state[4 * col + 0] = static_cast<uint8_t>(gf_mul(a, 2) ^ gf_mul(b, 3) ^ c ^ d);
            state[4 * col + 1] = static_cast<uint8_t>(a ^ gf_mul(b, 2) ^ gf_mul(c, 3) ^ d);
            state[4 * col + 2] = static_cast<uint8_t>(a ^ b ^ gf_mul(c, 2) ^ gf_mul(d, 3));
            state[4 * col + 3] = static_cast<uint8_t>(gf_mul(a, 3) ^ b ^ c ^ gf_mul(d, 2));
        }
    }
}

Block AES128::encrypt_block(const Block& plaintext) const {
    Block state = plaintext;
    add_round_key(state, 0);
    for (unsigned round = 1; round <= 9; ++round) {
        sub_bytes(state, false);
        shift_rows(state, false);
        mix_columns(state, false);
        add_round_key(state, round);
    }
    sub_bytes(state, false);
    shift_rows(state, false);
    add_round_key(state, 10);
    return state;
}

Block AES128::decrypt_block(const Block& ciphertext) const {
    Block state = ciphertext;
    add_round_key(state, 10);
    for (unsigned round = 9; round >= 1; --round) {
        shift_rows(state, true);
        sub_bytes(state, true);
        add_round_key(state, round);
        mix_columns(state, true);
    }
    shift_rows(state, true);
    sub_bytes(state, true);
    add_round_key(state, 0);
    return state;
}
