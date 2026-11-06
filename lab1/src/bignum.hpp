#pragma once
// Длинное беззнаковое число фиксированной разрядности для этапа 2.
// Хранится в std::array (без динамической памяти). Слова по 32 бита,
// все промежуточные вычисления помещаются в uint64_t.

#include <array>
#include <cstdint>
#include <string>

const int kLimbs = 9;        // 9 * 32 = 288 бит хранения
const int kMaxBits = 256;    // максимальная разрядность простого числа

struct BigNum {
    std::array<uint32_t, kLimbs> w{};  // w[0] -- младшее слово

    static BigNum from_u64(uint64_t v) {
        BigNum r;
        r.w[0] = static_cast<uint32_t>(v);
        r.w[1] = static_cast<uint32_t>(v >> 32);
        return r;
    }

    bool bit(int i) const { return (w[i / 32] >> (i % 32)) & 1u; }
    void set_bit(int i) { w[i / 32] |= (1u << (i % 32)); }
    bool is_odd() const { return (w[0] & 1u) != 0; }

    bool is_zero() const {
        for (int i = 0; i < kLimbs; ++i)
            if (w[i] != 0) return false;
        return true;
    }

    int bit_length() const {
        for (int i = kLimbs - 1; i >= 0; --i) {
            if (w[i] == 0) continue;
            int n = 0;
            for (uint32_t x = w[i]; x != 0; x >>= 1) ++n;
            return i * 32 + n;
        }
        return 0;
    }

    uint64_t low64() const {
        return (static_cast<uint64_t>(w[1]) << 32) | w[0];
    }
};

inline bool operator==(const BigNum& a, const BigNum& b) { return a.w == b.w; }
inline bool operator!=(const BigNum& a, const BigNum& b) { return !(a == b); }

inline int compare(const BigNum& a, const BigNum& b) {
    for (int i = kLimbs - 1; i >= 0; --i)
        if (a.w[i] != b.w[i]) return a.w[i] < b.w[i] ? -1 : 1;
    return 0;
}

// r = a + b, возвращает перенос.
inline uint32_t add(const BigNum& a, const BigNum& b, BigNum& r) {
    uint64_t carry = 0;
    for (int i = 0; i < kLimbs; ++i) {
        const uint64_t s = static_cast<uint64_t>(a.w[i]) + b.w[i] + carry;
        r.w[i] = static_cast<uint32_t>(s);
        carry = s >> 32;
    }
    return static_cast<uint32_t>(carry);
}

// r = a - b, возвращает заём (1, если a < b).
inline uint32_t sub(const BigNum& a, const BigNum& b, BigNum& r) {
    uint64_t borrow = 0;
    for (int i = 0; i < kLimbs; ++i) {
        const uint64_t d = static_cast<uint64_t>(a.w[i]) - b.w[i] - borrow;
        r.w[i] = static_cast<uint32_t>(d);
        borrow = (d >> 63) & 1u;
    }
    return static_cast<uint32_t>(borrow);
}

inline void shr1(BigNum& a) {
    for (int i = 0; i < kLimbs; ++i) {
        const uint32_t hi = (i + 1 < kLimbs) ? (a.w[i + 1] & 1u) : 0u;
        a.w[i] = (a.w[i] >> 1) | (hi << 31);
    }
}

inline void shl1(BigNum& a) {
    for (int i = kLimbs - 1; i > 0; --i) a.w[i] = (a.w[i] << 1) | (a.w[i - 1] >> 31);
    a.w[0] <<= 1;
}

// Остаток от деления на небольшое число (для просеивания).
inline uint32_t mod_small(const BigNum& a, uint32_t m) {
    uint64_t rem = 0;
    for (int i = kLimbs - 1; i >= 0; --i) rem = ((rem << 32) | a.w[i]) % m;
    return static_cast<uint32_t>(rem);
}

// Выбор без ветвления: r = mask ? x : r  (mask = 0xFFFFFFFF или 0).
inline void select(BigNum& r, const BigNum& x, uint32_t mask) {
    for (int i = 0; i < kLimbs; ++i) r.w[i] = (x.w[i] & mask) | (r.w[i] & ~mask);
}

inline void cswap(BigNum& a, BigNum& b, uint32_t mask) {
    for (int i = 0; i < kLimbs; ++i) {
        const uint32_t t = (a.w[i] ^ b.w[i]) & mask;
        a.w[i] ^= t;
        b.w[i] ^= t;
    }
}

// (a + b) mod n при a, b < n.
inline BigNum add_mod(const BigNum& a, const BigNum& b, const BigNum& n) {
    BigNum s, d;
    add(a, b, s);
    const uint32_t borrow = sub(s, n, d);
    select(s, d, borrow - 1u);  // заёма нет => s >= n => берём s - n
    return s;
}

// (a * b) mod n методом "удвоение-сложение", a, b < n.
inline BigNum mul_mod(const BigNum& a, const BigNum& b, const BigNum& n) {
    BigNum r;
    for (int i = n.bit_length() - 1; i >= 0; --i) {
        r = add_mod(r, r, n);
        const BigNum t = add_mod(r, a, n);
        select(r, t, 0u - static_cast<uint32_t>(b.bit(i)));
    }
    return r;
}

// (base ^ e) mod n лестницей Монтгомери: на каждом шаге выполняются
// одни и те же операции независимо от значения бита показателя.
inline BigNum pow_mod(const BigNum& base, const BigNum& e, const BigNum& n) {
    BigNum r0 = BigNum::from_u64(1);
    BigNum r1 = base;
    for (int i = n.bit_length() - 1; i >= 0; --i) {
        const uint32_t mask = 0u - static_cast<uint32_t>(e.bit(i));
        cswap(r0, r1, mask);
        r1 = mul_mod(r0, r1, n);
        r0 = mul_mod(r0, r0, n);
        cswap(r0, r1, mask);
    }
    return r0;
}

inline std::string to_dec(BigNum a) {
    if (a.is_zero()) return "0";
    std::string s;
    while (!a.is_zero()) {
        uint64_t rem = 0;  // делим на 10^9
        for (int i = kLimbs - 1; i >= 0; --i) {
            const uint64_t cur = (rem << 32) | a.w[i];
            a.w[i] = static_cast<uint32_t>(cur / 1000000000u);
            rem = cur % 1000000000u;
        }
        for (int k = 0; k < 9; ++k) {
            s.insert(s.begin(), static_cast<char>('0' + rem % 10));
            rem /= 10;
            if (a.is_zero() && rem == 0) break;
        }
    }
    return s;
}

inline BigNum from_hex(const char* hex) {
    BigNum r;
    for (const char* p = hex; *p; ++p) {
        uint32_t d;
        if (*p >= '0' && *p <= '9') d = *p - '0';
        else if (*p >= 'a' && *p <= 'f') d = *p - 'a' + 10;
        else if (*p >= 'A' && *p <= 'F') d = *p - 'A' + 10;
        else continue;
        for (int k = 0; k < 4; ++k) shl1(r);
        r.w[0] |= d;
    }
    return r;
}
