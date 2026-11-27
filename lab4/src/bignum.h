#pragma once
#include <cstddef>
#include <cstdint>
#include <string>

// Число фиксированной длины 512 бит: 16 слов по 32 бита, младшее слово первым.
// Память под число всегда одна и та же (64 байта), куча не используется.
const int LIMBS = 16;

struct BigNum {
    std::uint32_t w[LIMBS];
};

BigNum Zero();
BigNum FromUint(std::uint32_t value);
BigNum FromHex(const char* hex);
std::string ToHex(const BigNum& a, int bytes = 32);

BigNum FromBytesLE(const std::uint8_t* bytes, std::size_t count);
void ToBytesLE(const BigNum& a, std::uint8_t* out, std::size_t count);

std::uint32_t GetBit(const BigNum& a, int index);
bool IsEqual(const BigNum& a, const BigNum& b);
bool IsLess(const BigNum& a, const BigNum& b);

// mask = 0xFFFFFFFF -> результат ifOne, mask = 0 -> результат ifZero
BigNum Select(std::uint32_t mask, const BigNum& ifOne, const BigNum& ifZero);

std::uint32_t Add(const BigNum& a, const BigNum& b, BigNum& out);
std::uint32_t Sub(const BigNum& a, const BigNum& b, BigNum& out);
BigNum Mul(const BigNum& a, const BigNum& b);
BigNum Mod(const BigNum& x, const BigNum& m);

BigNum AddMod(const BigNum& a, const BigNum& b, const BigNum& m);
BigNum SubMod(const BigNum& a, const BigNum& b, const BigNum& m);
BigNum MulMod(const BigNum& a, const BigNum& b, const BigNum& m);
BigNum PowMod(const BigNum& base, const BigNum& exponent, const BigNum& m);
BigNum InvMod(const BigNum& a, const BigNum& m);
