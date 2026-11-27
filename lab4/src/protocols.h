#pragma once
#include <cstddef>
#include <cstdint>

#include "bignum.h"
#include "curve.h"

// Модуль 2. Протокол ECDH и подпись EdDSA (Ed25519, RFC 8032)

struct EcdhKeyPair {
    BigNum d;          // секретный ключ
    AffinePoint Q;     // открытый ключ Q = d * G
};

EcdhKeyPair EcdhGenerateKeyPair();
BigNum EcdhSharedSecret(const BigNum& ownSecret, const AffinePoint& otherPublic);  // x(d * Q)

struct Ed25519Keys {
    BigNum a;                    // секретный скаляр (младшая половина SHA-512(seed))
    std::uint8_t prefix[32];     // h_B — старшая половина SHA-512(seed)
    AffinePoint A;               // открытый ключ A = a * G
    std::uint8_t encodedA[32];
};

struct Signature {
    AffinePoint R;
    BigNum S;
};

Ed25519Keys Ed25519KeysFromSeed(const std::uint8_t seed[32]);
Signature Ed25519Sign(const Ed25519Keys& keys, const std::uint8_t* message, std::size_t length);
bool Ed25519Verify(const AffinePoint& publicKey, const Signature& signature,
                   const std::uint8_t* message, std::size_t length);
void EncodeSignature(const Signature& signature, std::uint8_t out[64]);
