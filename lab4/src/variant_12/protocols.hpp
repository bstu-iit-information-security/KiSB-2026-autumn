#pragma once

#include "secure.hpp"

namespace lab4 {
using Signature = std::array<Byte, 48>;
struct KeyPair {
    UInt256 secret{};
    Point public_key{};
    bool ok = false;
};
struct SharedSecret {
    UInt256 x{};
    bool ok = false;
};
struct SignResult {
    Signature signature{};
    bool ok = false;
};
struct CourseSignature {
    UInt256 r{};
    UInt256 s{};
    bool ok = false;
};

Bytes32 belt_hash(const Byte* message, std::size_t size) noexcept;
KeyPair key_pair(const Curve& curve, Entropy entropy) noexcept;
SharedSecret ecdh(const Curve& curve, const UInt256& secret, const Point& peer) noexcept;
SignResult bign_sign_with_nonce(const Curve& curve, const Bytes32& hash,
                               const UInt256& secret, const UInt256& nonce) noexcept;
SignResult bign_sign(const Curve& curve, const Bytes32& hash,
                    const UInt256& secret, Entropy entropy) noexcept;
bool bign_verify(const Curve& curve, const Bytes32& hash,
                 const Point& public_key, const Signature& signature) noexcept;
// The separate (r,s) equations in the course handout are GOST-style.
CourseSignature course_sign(const Curve& curve, const Bytes32& hash,
                            const UInt256& secret, const UInt256& nonce) noexcept;
bool course_verify(const Curve& curve, const Bytes32& hash,
                   const Point& public_key, const CourseSignature& signature) noexcept;
}
