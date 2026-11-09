#include "modes.hpp"

#include <algorithm>
#include <cstring>

namespace lab3 {
namespace {
constexpr std::size_t block_size = Block{}.size();

Block read_block(const Byte* input) noexcept {
    Block block;
    std::memcpy(block.data(), input, block.size());
    return block;
}

void xor_gamma(const Byte* input, const Byte* gamma, Byte* output, std::size_t count) noexcept {
    for (std::size_t i = 0; i < count; ++i) output[i] = input[i] ^ gamma[i];
}
}

Result pkcs7_pad(const Byte* input, std::size_t size,
                 Byte* output, std::size_t capacity) noexcept {
    const auto pad = block_size - size % block_size;
    if (!output || (size != 0 && !input) || size > capacity || pad > capacity - size) {
        return {false, 0};
    }
    if (size != 0) std::memmove(output, input, size);
    std::memset(output + size, static_cast<int>(pad), pad);
    return {true, size + pad};
}

Result pkcs7_unpad(const Byte* input, std::size_t size) noexcept {
    if (!input || size == 0 || size % block_size != 0) return {false, 0};
    const std::uint32_t pad = input[size - 1];
    std::uint32_t mismatch = 0;
    for (std::uint32_t i = 0; i < block_size; ++i) {
        // Underflow selects the bytes at distances smaller than pad.
        const std::uint32_t mask = 0U - ((i - pad) >> 31);
        mismatch |= (input[size - 1 - i] ^ pad) & mask;
    }
    if (pad == 0 || pad > block_size || mismatch != 0) return {false, 0};
    return {true, size - pad};
}

Result ecb_encrypt(const Key& key, const Byte* input, std::size_t size,
                   Byte* output, std::size_t capacity) noexcept {
    const auto padded = pkcs7_pad(input, size, output, capacity);
    if (!padded.ok) return padded;
    for (std::size_t offset = 0; offset < padded.size; offset += block_size) {
        const auto block = encrypt_block(read_block(output + offset), key);
        std::memcpy(output + offset, block.data(), block.size());
    }
    return padded;
}

Result ecb_decrypt(const Key& key, const Byte* input, std::size_t size,
                   Byte* output, std::size_t capacity) noexcept {
    if (!input || size == 0 || size % block_size != 0) return {false, 0};
    const auto last_offset = size - block_size;
    const auto last = decrypt_block(read_block(input + last_offset), key);
    const auto tail = pkcs7_unpad(last.data(), last.size());
    const auto plain_size = last_offset + tail.size;
    if (!tail.ok || plain_size > capacity || (plain_size != 0 && !output)) return {false, 0};
    for (std::size_t offset = 0; offset < last_offset; offset += block_size) {
        const auto block = decrypt_block(read_block(input + offset), key);
        std::memcpy(output + offset, block.data(), block.size());
    }
    if (tail.size != 0) std::memcpy(output + last_offset, last.data(), tail.size);
    return {true, plain_size};
}

OfbStream::OfbStream(const Key& key, const Block& iv) noexcept
    : key_(key), feedback_(iv) {}

bool OfbStream::prepare(std::size_t count) noexcept {
    if (begin_ != end_ || count > cache_.size()) return false;
    for (std::size_t written = 0; written < count;) {
        const auto gamma = take_gamma(count - written);
        std::memcpy(cache_.data() + written, gamma.bytes, gamma.size);
        written += gamma.size;
    }
    begin_ = 0;
    end_ = count;
    return true;
}

bool OfbStream::apply(const Byte* input, Byte* output, std::size_t count) noexcept {
    if (count == 0) return true;
    if (!input || !output) return false;
    const auto ready = std::min(count, end_ - begin_);
    xor_gamma(input, cache_.data() + begin_, output, ready);
    begin_ += ready;
    for (std::size_t processed = ready; processed < count;) {
        const auto gamma = take_gamma(count - processed);
        xor_gamma(input + processed, gamma.bytes, output + processed, gamma.size);
        processed += gamma.size;
    }
    return true;
}

OfbStream::GammaChunk OfbStream::take_gamma(std::size_t count) noexcept {
    if (offset_ == block_size) {
        // OFB feeds the previous output of the block cipher back into it.
        feedback_ = encrypt_block(feedback_, key_);
        offset_ = 0;
    }
    const GammaChunk gamma{feedback_.data() + offset_, std::min(count, block_size - offset_)};
    offset_ += gamma.size;
    return gamma;
}
}
