#include "protocols.hpp"

#include "belt.hpp"

#include <algorithm>
#include <cstring>

namespace lab4 {
namespace {
struct Compression {
    belt::Block intermediate;
    Bytes32 hash;
};

Compression compress(const Bytes32& message, const Bytes32& state) noexcept {
    belt::Block x1{}, x2{}, x3{}, x4{}, mixed{};
    std::memcpy(x1.data(), message.data(), 16);
    std::memcpy(x2.data(), message.data() + 16, 16);
    std::memcpy(x3.data(), state.data(), 16);
    std::memcpy(x4.data(), state.data() + 16, 16);
    for (std::size_t i = 0; i < 16; ++i) mixed[i] = x3[i] ^ x4[i];
    auto s = belt::encrypt_block(mixed, message);
    for (std::size_t i = 0; i < 16; ++i) s[i] ^= mixed[i];
    Bytes32 key1{}, key2{};
    for (std::size_t i = 0; i < 16; ++i) {
        key1[i] = s[i];
        key1[16 + i] = x4[i];
        key2[i] = s[i] ^ 0xff;
        key2[16 + i] = x3[i];
    }
    const auto y1 = belt::encrypt_block(x1, key1);
    const auto y2 = belt::encrypt_block(x2, key2);
    Bytes32 hash{};
    for (std::size_t i = 0; i < 16; ++i) {
        hash[i] = y1[i] ^ x1[i];
        hash[16 + i] = y2[i] ^ x2[i];
    }
    return {s, hash};
}

bool valid_scalar(const UInt256& value, const Modulus& order) noexcept {
    return (nonzero(value) & less(value, order.value)) != 0;
}

std::array<Byte, 16> challenge(const Bytes32& hash, const UInt256& x) noexcept {
    // Fixed OID bytes are part of the hash input. No ASN.1 parser is used.
    constexpr Byte hash_oid[] = {0x06, 0x09, 0x2a, 0x70, 0x00, 0x02, 0x00, 0x22, 0x65, 0x1f, 0x51};
    std::array<Byte, sizeof(hash_oid) + 64> input{};
    std::memcpy(input.data(), hash_oid, sizeof(hash_oid));
    const auto x_bytes = to_le(x);
    std::memcpy(input.data() + sizeof(hash_oid), x_bytes.data(), x_bytes.size());
    std::memcpy(input.data() + sizeof(hash_oid) + 32, hash.data(), hash.size());
    const auto digest = belt_hash(input.data(), input.size());
    std::array<Byte, 16> result{};
    std::memcpy(result.data(), digest.data(), result.size());
    return result;
}

UInt256 challenge_scalar(const Byte* s0) noexcept {
    Bytes32 bytes{};
    std::memcpy(bytes.data(), s0, 16);
    bytes[16] = 1;  // s0 + 2^128.
    return from_le(bytes);
}

UInt256 course_hash_scalar(const Bytes32& hash, const Modulus& order) noexcept {
    const auto e = reduce_once(from_le(hash), order);
    return select(e, from_u32(1), nonzero(e) ^ 1U);
}
}

Bytes32 belt_hash(const Byte* message, std::size_t size) noexcept {
    constexpr Bytes32 initial = {
        0xb1, 0x94, 0xba, 0xc8, 0x0a, 0x08, 0xf5, 0x3b, 0x36, 0x6d, 0x00, 0x8e, 0x58, 0x4a, 0x5d, 0xe4,
        0x85, 0x04, 0xfa, 0x9d, 0x1b, 0xb6, 0xc7, 0xac, 0x25, 0x2e, 0x72, 0xc2, 0x02, 0xfd, 0xce, 0x0d
    };
    auto hash = initial;
    belt::Block accumulator{};
    std::size_t offset = 0;
    while (offset < size) {
        Bytes32 block{};
        const auto part = std::min(block.size(), size - offset);
        std::memcpy(block.data(), message + offset, part);
        const auto step = compress(block, hash);
        hash = step.hash;
        for (std::size_t i = 0; i < accumulator.size(); ++i) accumulator[i] ^= step.intermediate[i];
        offset += part;
    }
    Bytes32 final_block{};
    const auto low_bits = static_cast<std::uint64_t>(size) << 3;
    const auto high_bits = static_cast<std::uint64_t>(size) >> 61;
    for (unsigned i = 0; i < 8; ++i) {
        final_block[i] = static_cast<Byte>(low_bits >> (8 * i));
        final_block[i + 8] = static_cast<Byte>(high_bits >> (8 * i));
    }
    std::memcpy(final_block.data() + 16, accumulator.data(), accumulator.size());
    return compress(final_block, hash).hash;
}

KeyPair key_pair(const Curve& c, Entropy entropy) noexcept {
    const auto random = generate_nonce(c.order, entropy);
    if (!random.ok) return {};
    return {random.value, multiply_secret(c, random.value, c.generator), true};
}

SharedSecret ecdh(const Curve& c, const UInt256& secret, const Point& peer) noexcept {
    if (!valid_scalar(secret, c.order) || !valid_public_key(c, peer)) return {};
    const auto shared = multiply_secret(c, secret, peer);
    if (shared.infinity) return {};
    return {shared.x, true};
}

SignResult bign_sign_with_nonce(const Curve& c, const Bytes32& hash,
                               const UInt256& secret, const UInt256& nonce) noexcept {
    if (!valid_scalar(secret, c.order) || !valid_scalar(nonce, c.order)) return {};
    const auto r = multiply_secret(c, nonce, c.generator);
    const auto s0 = challenge(hash, r.x);
    const auto e = reduce_once(from_le(hash), c.order);
    const auto s1 = mod_sub(mod_sub(nonce, e, c.order),
                            mod_mul(challenge_scalar(s0.data()), secret, c.order), c.order);
    SignResult result{};
    const auto s1_bytes = to_le(s1);
    std::memcpy(result.signature.data(), s0.data(), s0.size());
    std::memcpy(result.signature.data() + 16, s1_bytes.data(), s1_bytes.size());
    result.ok = true;
    return result;
}

SignResult bign_sign(const Curve& c, const Bytes32& hash,
                    const UInt256& secret, Entropy entropy) noexcept {
    const auto random = generate_nonce(c.order, entropy);
    if (!random.ok) return {};
    return bign_sign_with_nonce(c, hash, secret, random.value);
}

bool bign_verify(const Curve& c, const Bytes32& hash,
                 const Point& public_key, const Signature& signature) noexcept {
    if (!valid_public_key(c, public_key)) return false;
    Bytes32 s1_bytes{};
    std::memcpy(s1_bytes.data(), signature.data() + 16, s1_bytes.size());
    const auto s1 = from_le(s1_bytes);
    if (!less(s1, c.order.value)) return false;
    const auto e = reduce_once(from_le(hash), c.order);
    const auto r = point_add(c,
        multiply_public(c, mod_add(s1, e, c.order), c.generator),
        multiply_public(c, challenge_scalar(signature.data()), public_key));
    if (r.infinity) return false;
    const auto expected = challenge(hash, r.x);
    unsigned difference = 0;
    for (std::size_t i = 0; i < expected.size(); ++i) difference |= expected[i] ^ signature[i];
    return difference == 0;
}

CourseSignature course_sign(const Curve& c, const Bytes32& hash,
                            const UInt256& secret, const UInt256& nonce) noexcept {
    if (!valid_scalar(secret, c.order) || !valid_scalar(nonce, c.order)) return {};
    const auto point = multiply_secret(c, nonce, c.generator);
    const auto r = reduce_once(point.x, c.order);
    const auto e = course_hash_scalar(hash, c.order);
    const auto s = mod_add(mod_mul(r, secret, c.order), mod_mul(nonce, e, c.order), c.order);
    return {r, s, (nonzero(r) & nonzero(s)) != 0};
}

bool course_verify(const Curve& c, const Bytes32& hash,
                   const Point& public_key, const CourseSignature& signature) noexcept {
    if (!signature.ok || !valid_scalar(signature.r, c.order)
        || !valid_scalar(signature.s, c.order) || !valid_public_key(c, public_key)) return false;
    const auto v = mod_inverse(course_hash_scalar(hash, c.order), c.order);
    const auto z1 = mod_mul(signature.s, v, c.order);
    const auto z2 = mod_sub({}, mod_mul(signature.r, v, c.order), c.order);
    const auto point = point_add(c, multiply_public(c, z1, c.generator),
                                multiply_public(c, z2, public_key));
    return !point.infinity && equal(reduce_once(point.x, c.order), signature.r) != 0;
}
}
