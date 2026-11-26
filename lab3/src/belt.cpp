#include "belt.h"
#include <utility>

namespace {

// H-блок (таблица подстановки) из СТБ 34.101.31
const std::uint8_t H[256] = {
    0xB1, 0x94, 0xBA, 0xC8, 0x0A, 0x08, 0xF5, 0x3B, 0x36, 0x6D, 0x00, 0x8E, 0x58, 0x4A, 0x5D, 0xE4,
    0x85, 0x04, 0xFA, 0x9D, 0x1B, 0xB6, 0xC7, 0xAC, 0x25, 0x2E, 0x72, 0xC2, 0x02, 0xFD, 0xCE, 0x0D,
    0x5B, 0xE3, 0xD6, 0x12, 0x17, 0xB9, 0x61, 0x81, 0xFE, 0x67, 0x86, 0xAD, 0x71, 0x6B, 0x89, 0x0B,
    0x5C, 0xB0, 0xC0, 0xFF, 0x33, 0xC3, 0x56, 0xB8, 0x35, 0xC4, 0x05, 0xAE, 0xD8, 0xE0, 0x7F, 0x99,
    0xE1, 0x2B, 0xDC, 0x1A, 0xE2, 0x82, 0x57, 0xEC, 0x70, 0x3F, 0xCC, 0xF0, 0x95, 0xEE, 0x8D, 0xF1,
    0xC1, 0xAB, 0x76, 0x38, 0x9F, 0xE6, 0x78, 0xCA, 0xF7, 0xC6, 0xF8, 0x60, 0xD5, 0xBB, 0x9C, 0x4F,
    0xF3, 0x3C, 0x65, 0x7B, 0x63, 0x7C, 0x30, 0x6A, 0xDD, 0x4E, 0xA7, 0x79, 0x9E, 0xB2, 0x3D, 0x31,
    0x3E, 0x98, 0xB5, 0x6E, 0x27, 0xD3, 0xBC, 0xCF, 0x59, 0x1E, 0x18, 0x1F, 0x4C, 0x5A, 0xB7, 0x93,
    0xE9, 0xDE, 0xE7, 0x2C, 0x8F, 0x0C, 0x0F, 0xA6, 0x2D, 0xDB, 0x49, 0xF4, 0x6F, 0x73, 0x96, 0x47,
    0x06, 0x07, 0x53, 0x16, 0xED, 0x24, 0x7A, 0x37, 0x39, 0xCB, 0xA3, 0x83, 0x03, 0xA9, 0x8B, 0xF6,
    0x92, 0xBD, 0x9B, 0x1C, 0xE5, 0xD1, 0x41, 0x01, 0x54, 0x45, 0xFB, 0xC9, 0x5E, 0x4D, 0x0E, 0xF2,
    0x68, 0x20, 0x80, 0xAA, 0x22, 0x7D, 0x64, 0x2F, 0x26, 0x87, 0xF9, 0x34, 0x90, 0x40, 0x55, 0x11,
    0xBE, 0x32, 0x97, 0x13, 0x43, 0xFC, 0x9A, 0x48, 0xA0, 0x2A, 0x88, 0x5F, 0x19, 0x4B, 0x09, 0xA1,
    0x7E, 0xCD, 0xA4, 0xD0, 0x15, 0x44, 0xAF, 0x8C, 0xA5, 0x84, 0x50, 0xBF, 0x66, 0xD2, 0xE8, 0x8A,
    0xA2, 0xD7, 0x46, 0x52, 0x42, 0xA8, 0xDF, 0xB3, 0x69, 0x74, 0xC5, 0x51, 0xEB, 0x23, 0x29, 0x21,
    0xD4, 0xEF, 0xD9, 0xB4, 0x3A, 0x62, 0x28, 0x75, 0x91, 0x14, 0x10, 0xEA, 0x77, 0x6C, 0xDA, 0x1D,
};

std::uint32_t rotl(std::uint32_t x, int r) {
    return (x << r) | (x >> (32 - r));
}

// G_r: замена каждого байта слова через H, затем циклический сдвиг влево на r бит
std::uint32_t G(std::uint32_t u, int r) {
    std::uint32_t substituted = static_cast<std::uint32_t>(H[u & 0xFF])
                              | static_cast<std::uint32_t>(H[(u >> 8) & 0xFF]) << 8
                              | static_cast<std::uint32_t>(H[(u >> 16) & 0xFF]) << 16
                              | static_cast<std::uint32_t>(H[(u >> 24) & 0xFF]) << 24;
    return rotl(substituted, r);
}

// Слова в СТБ записываются младшим байтом вперёд (little-endian)
std::uint32_t load_word(const std::uint8_t* p) {
    return static_cast<std::uint32_t>(p[0])
         | static_cast<std::uint32_t>(p[1]) << 8
         | static_cast<std::uint32_t>(p[2]) << 16
         | static_cast<std::uint32_t>(p[3]) << 24;
}

void store_word(std::uint32_t w, std::uint8_t* p) {
    p[0] = static_cast<std::uint8_t>(w);
    p[1] = static_cast<std::uint8_t>(w >> 8);
    p[2] = static_cast<std::uint8_t>(w >> 16);
    p[3] = static_cast<std::uint8_t>(w >> 24);
}

// Раундовые подключи k[1..56] — циклическое повторение K1..K8; k[0] не используется,
// чтобы индексы совпадали с формулами стандарта
void expand_key(const Key& key, std::uint32_t k[57]) {
    std::uint32_t K[8];
    for (int j = 0; j < 8; ++j)
        K[j] = load_word(&key[4 * j]);
    for (int i = 1; i <= 56; ++i)
        k[i] = K[(i - 1) % 8];
}

} // namespace

// Сложение и вычитание uint32_t в C++ выполняются по модулю 2^32
Block encrypt_block(const Block& pt_block, const Key& key) {
    std::uint32_t k[57];
    expand_key(key, k);

    std::uint32_t a = load_word(&pt_block[0]);
    std::uint32_t b = load_word(&pt_block[4]);
    std::uint32_t c = load_word(&pt_block[8]);
    std::uint32_t d = load_word(&pt_block[12]);

    for (int i = 1; i <= 8; ++i) {
        b ^= G(a + k[7 * i - 6], 5);
        c ^= G(d + k[7 * i - 5], 21);
        a -= G(b + k[7 * i - 4], 13);
        std::uint32_t e = G(b + c + k[7 * i - 3], 21) ^ static_cast<std::uint32_t>(i);
        b += e;
        c -= e;
        d += G(c + k[7 * i - 2], 13);
        b ^= G(a + k[7 * i - 1], 21);
        c ^= G(d + k[7 * i], 5);
        std::swap(a, b);
        std::swap(c, d);
        std::swap(b, c);
    }

    Block ct_block;
    store_word(b, &ct_block[0]);
    store_word(d, &ct_block[4]);
    store_word(a, &ct_block[8]);
    store_word(c, &ct_block[12]);
    return ct_block;
}

// Раунды в обратном порядке 8..1, подключи внутри раунда — от k[7i] к k[7i-6]
Block decrypt_block(const Block& ct_block, const Key& key) {
    std::uint32_t k[57];
    expand_key(key, k);

    std::uint32_t a = load_word(&ct_block[0]);
    std::uint32_t b = load_word(&ct_block[4]);
    std::uint32_t c = load_word(&ct_block[8]);
    std::uint32_t d = load_word(&ct_block[12]);

    for (int i = 8; i >= 1; --i) {
        b ^= G(a + k[7 * i], 5);
        c ^= G(d + k[7 * i - 1], 21);
        a -= G(b + k[7 * i - 2], 13);
        std::uint32_t e = G(b + c + k[7 * i - 3], 21) ^ static_cast<std::uint32_t>(i);
        b += e;
        c -= e;
        d += G(c + k[7 * i - 4], 13);
        b ^= G(a + k[7 * i - 5], 21);
        c ^= G(d + k[7 * i - 6], 5);
        std::swap(a, b);
        std::swap(c, d);
        std::swap(a, d);
    }

    Block pt_block;
    store_word(c, &pt_block[0]);
    store_word(a, &pt_block[4]);
    store_word(d, &pt_block[8]);
    store_word(b, &pt_block[12]);
    return pt_block;
}
