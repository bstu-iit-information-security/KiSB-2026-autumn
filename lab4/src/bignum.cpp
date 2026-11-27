#include "bignum.h"

#include <stdexcept>

BigNum Zero() {
    BigNum r;
    for (int i = 0; i < LIMBS; ++i)
        r.w[i] = 0;
    return r;
}

BigNum FromUint(std::uint32_t value) {
    BigNum r = Zero();
    r.w[0] = value;
    return r;
}

static int HexDigit(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    throw std::invalid_argument("FromHex: недопустимый символ");
}

// Строка читается как обычная запись числа: старшая цифра слева
BigNum FromHex(const char* hex) {
    BigNum r = Zero();
    int length = 0;
    while (hex[length] != '\0')
        ++length;
    if (length > LIMBS * 8)
        throw std::invalid_argument("FromHex: число длиннее 512 бит");
    for (int i = 0; i < length; ++i) {
        int position = length - 1 - i;  // номер 4-битной цифры от младшей
        r.w[position / 8] |= static_cast<std::uint32_t>(HexDigit(hex[i])) << (4 * (position % 8));
    }
    return r;
}

std::string ToHex(const BigNum& a, int bytes) {
    const char* digits = "0123456789abcdef";
    std::string s;
    for (int position = bytes * 2 - 1; position >= 0; --position)
        s += digits[(a.w[position / 8] >> (4 * (position % 8))) & 0xF];
    return s;
}

BigNum FromBytesLE(const std::uint8_t* bytes, std::size_t count) {
    BigNum r = Zero();
    for (std::size_t i = 0; i < count && i < LIMBS * 4; ++i)
        r.w[i / 4] |= static_cast<std::uint32_t>(bytes[i]) << (8 * (i % 4));
    return r;
}

void ToBytesLE(const BigNum& a, std::uint8_t* out, std::size_t count) {
    for (std::size_t i = 0; i < count; ++i)
        out[i] = static_cast<std::uint8_t>(a.w[i / 4] >> (8 * (i % 4)));
}

std::uint32_t GetBit(const BigNum& a, int index) {
    return (a.w[index / 32] >> (index % 32)) & 1;
}

bool IsEqual(const BigNum& a, const BigNum& b) {
    std::uint32_t difference = 0;
    for (int i = 0; i < LIMBS; ++i)
        difference |= a.w[i] ^ b.w[i];
    return difference == 0;
}

bool IsLess(const BigNum& a, const BigNum& b) {
    for (int i = LIMBS - 1; i >= 0; --i)
        if (a.w[i] != b.w[i])
            return a.w[i] < b.w[i];
    return false;
}

BigNum Select(std::uint32_t mask, const BigNum& ifOne, const BigNum& ifZero) {
    BigNum r;
    for (int i = 0; i < LIMBS; ++i)
        r.w[i] = (ifOne.w[i] & mask) | (ifZero.w[i] & ~mask);
    return r;
}

std::uint32_t Add(const BigNum& a, const BigNum& b, BigNum& out) {
    std::uint64_t carry = 0;
    for (int i = 0; i < LIMBS; ++i) {
        std::uint64_t sum = static_cast<std::uint64_t>(a.w[i]) + b.w[i] + carry;
        out.w[i] = static_cast<std::uint32_t>(sum);
        carry = sum >> 32;
    }
    return static_cast<std::uint32_t>(carry);
}

std::uint32_t Sub(const BigNum& a, const BigNum& b, BigNum& out) {
    std::uint64_t borrow = 0;
    for (int i = 0; i < LIMBS; ++i) {
        std::uint64_t difference = static_cast<std::uint64_t>(a.w[i]) - b.w[i] - borrow;
        out.w[i] = static_cast<std::uint32_t>(difference);
        borrow = (difference >> 32) & 1;
    }
    return static_cast<std::uint32_t>(borrow);
}

// Умножение «в столбик». Результат берётся по модулю 2^512,
// для множителей меньше 2^256 он точный.
BigNum Mul(const BigNum& a, const BigNum& b) {
    BigNum r = Zero();
    for (int i = 0; i < LIMBS; ++i) {
        std::uint64_t carry = 0;
        for (int j = 0; i + j < LIMBS; ++j) {
            std::uint64_t current = static_cast<std::uint64_t>(a.w[i]) * b.w[j] + r.w[i + j] + carry;
            r.w[i + j] = static_cast<std::uint32_t>(current);
            carry = current >> 32;
        }
    }
    return r;
}

// Двоичное деление «в столбик»: остаток сдвигается на бит влево,
// и если он стал не меньше m, из него вычитается m.
// Выбор делается маской, поэтому число итераций и действий не зависит от x.
BigNum Mod(const BigNum& x, const BigNum& m) {
    BigNum r = Zero();
    for (int bit = LIMBS * 32 - 1; bit >= 0; --bit) {
        for (int i = LIMBS - 1; i > 0; --i)
            r.w[i] = (r.w[i] << 1) | (r.w[i - 1] >> 31);
        r.w[0] = (r.w[0] << 1) | GetBit(x, bit);

        BigNum reduced;
        std::uint32_t borrow = Sub(r, m, reduced);  // borrow = 1, если r < m
        r = Select(0 - borrow, r, reduced);
    }
    return r;
}

// Для AddMod и SubMod аргументы должны быть уже приведены: a, b < m
BigNum AddMod(const BigNum& a, const BigNum& b, const BigNum& m) {
    BigNum sum, reduced;
    Add(a, b, sum);
    std::uint32_t borrow = Sub(sum, m, reduced);
    return Select(0 - borrow, sum, reduced);
}

BigNum SubMod(const BigNum& a, const BigNum& b, const BigNum& m) {
    BigNum difference;
    std::uint32_t borrow = Sub(a, b, difference);
    BigNum correction = Select(0 - borrow, m, Zero());  // при a < b прибавляем m
    Add(difference, correction, difference);
    return difference;
}

BigNum MulMod(const BigNum& a, const BigNum& b, const BigNum& m) {
    return Mod(Mul(a, b), m);
}

// Возведение в степень «слева направо». Показатель здесь всегда открытый
// (p - 2 или q - 2), поэтому ветвление по его битам ничего не раскрывает.
BigNum PowMod(const BigNum& base, const BigNum& exponent, const BigNum& m) {
    BigNum result = FromUint(1);
    for (int bit = 255; bit >= 0; --bit) {
        result = MulMod(result, result, m);
        if (GetBit(exponent, bit))
            result = MulMod(result, base, m);
    }
    return result;
}

// Малая теорема Ферма: для простого m  a^(m-1) = 1, значит a^(-1) = a^(m-2)
BigNum InvMod(const BigNum& a, const BigNum& m) {
    BigNum exponent;
    Sub(m, FromUint(2), exponent);
    return PowMod(a, exponent, m);
}
