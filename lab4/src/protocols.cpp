#include "protocols.h"

#include <stdexcept>

#include "secure.h"
#include "sha512.h"

EcdhKeyPair EcdhGenerateKeyPair() {
    EcdhKeyPair keys;
    keys.d = RandomScalar();
    keys.Q = ToAffine(SecureMultiply(keys.d, BasePoint()));
    return keys;
}

BigNum EcdhSharedSecret(const BigNum& ownSecret, const AffinePoint& otherPublic) {
    if (!IsOnCurve(otherPublic))
        throw std::invalid_argument("ECDH: открытый ключ не лежит на кривой");
    AffinePoint K = ToAffine(SecureMultiply(ownSecret, FromAffine(otherPublic)));
    return K.x;
}

// SHA-512(part1 || part2 || part3) как 512-битное число, приведённое по модулю q
static BigNum HashToScalar(const std::uint8_t* part1, std::size_t length1,
                           const std::uint8_t* part2, std::size_t length2,
                           const std::uint8_t* part3, std::size_t length3) {
    Sha512 hash;
    hash.Update(part1, length1);
    hash.Update(part2, length2);
    hash.Update(part3, length3);
    std::uint8_t digest[64];
    hash.Final(digest);
    return Mod(FromBytesLE(digest, 64), CURVE_Q);
}

Ed25519Keys Ed25519KeysFromSeed(const std::uint8_t seed[32]) {
    std::uint8_t digest[64];
    Sha512 hash;
    hash.Update(seed, 32);
    hash.Final(digest);

    // «Зажатие» скаляра по RFC 8032: кратен 8 (кофактор кривой), бит 254 = 1
    digest[0] &= 248;
    digest[31] &= 127;
    digest[31] |= 64;

    Ed25519Keys keys;
    keys.a = FromBytesLE(digest, 32);
    for (int i = 0; i < 32; ++i)
        keys.prefix[i] = digest[32 + i];
    keys.A = ToAffine(SecureMultiply(keys.a, BasePoint()));
    Encode(keys.A, keys.encodedA);
    return keys;
}

Signature Ed25519Sign(const Ed25519Keys& keys, const std::uint8_t* message, std::size_t length) {
    BigNum r = HashToScalar(keys.prefix, 32, message, length, nullptr, 0);

    Signature signature;
    signature.R = ToAffine(SecureMultiply(r, BasePoint()));
    std::uint8_t encodedR[32];
    Encode(signature.R, encodedR);

    BigNum h = HashToScalar(encodedR, 32, keys.encodedA, 32, message, length);
    signature.S = AddMod(r, MulMod(h, keys.a, CURVE_Q), CURVE_Q);  // S = (r + h * a) mod q
    return signature;
}

// Все данные открытые, поэтому используется обычный Multiply
bool Ed25519Verify(const AffinePoint& publicKey, const Signature& signature,
                   const std::uint8_t* message, std::size_t length) {
    if (!IsOnCurve(publicKey) || !IsOnCurve(signature.R) || !IsLess(signature.S, CURVE_Q))
        return false;

    std::uint8_t encodedR[32], encodedA[32];
    Encode(signature.R, encodedR);
    Encode(publicKey, encodedA);
    BigNum h = HashToScalar(encodedR, 32, encodedA, 32, message, length);

    Point left = Multiply(signature.S, BasePoint());                                   // S * G
    Point right = Add(FromAffine(signature.R), Multiply(h, FromAffine(publicKey)));    // R + h * A
    return IsSamePoint(left, right);
}

void EncodeSignature(const Signature& signature, std::uint8_t out[64]) {
    Encode(signature.R, out);
    ToBytesLE(signature.S, out + 32, 32);
}
