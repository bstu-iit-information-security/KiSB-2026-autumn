#pragma once

#include "belt.hpp"

#include <cstddef>

namespace lab3 {
struct Result {
    bool ok;
    std::size_t size;
};

// Buffers can be disjoint or have the same starting address. An empty input
// can be null. ECB encryption needs space for a whole extra padding block
// when the input is aligned. ECB decryption needs space for the plaintext.
Result pkcs7_pad(const Byte* input, std::size_t size,
                 Byte* output, std::size_t capacity) noexcept;
Result pkcs7_unpad(const Byte* input, std::size_t size) noexcept;
Result ecb_encrypt(const Key& key, const Byte* input, std::size_t size,
                   Byte* output, std::size_t capacity) noexcept;
Result ecb_decrypt(const Key& key, const Byte* input, std::size_t size,
                   Byte* output, std::size_t capacity) noexcept;

class OfbStream {
public:
    static constexpr std::size_t cache_capacity = 4096;

    // Each new message needs a unique IV per key.
    OfbStream(const Key& key, const Block& iv) noexcept;
    OfbStream(const OfbStream&) = delete;
    OfbStream& operator=(const OfbStream&) = delete;

    // Prepare the next count bytes before input arrives. Requires an empty cache.
    bool prepare(std::size_t count) noexcept;
    // Processes count bytes in either direction. Buffers follow the rule above.
    bool apply(const Byte* input, Byte* output, std::size_t count) noexcept;

private:
    struct GammaChunk {
        const Byte* bytes;
        std::size_t size;
    };

    GammaChunk take_gamma(std::size_t count) noexcept;

    const Key key_;
    Block feedback_;
    std::size_t offset_ = Block{}.size();
    std::array<Byte, cache_capacity> cache_;
    std::size_t begin_ = 0;
    std::size_t end_ = 0;
};
}
