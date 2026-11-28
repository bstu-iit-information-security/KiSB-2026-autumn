#include "aes.hpp"
#include "modes.hpp"

#include <array>
#include <iostream>
#include <map>
#include <random>
#include <string>
#include <vector>

namespace {

Bytes from_string(const std::string& text) {
    return Bytes(text.begin(), text.end());
}

std::string as_string(const Bytes& bytes) {
    return std::string(bytes.begin(), bytes.end());
}

void print_blocks(const Bytes& data, size_t count, const std::string& title) {
    std::cout << title << '\n';
    for (size_t i = 0; i < count && i * 16 < data.size(); ++i) {
        std::cout << "  block " << (i + 1) << ": "
                  << to_hex(data.data() + i * 16, 16) << '\n';
    }
}

bool round_trip(const std::string& title, const Bytes& message,
                const AES128& aes, const Block& iv) {
    bool ok = true;
    Bytes ecb_ct = ecb_encrypt(message, aes);
    UnpadResult ecb_pt = ecb_decrypt(ecb_ct, aes);
    Bytes cbc_ct = cbc_encrypt(message, aes, iv);
    UnpadResult cbc_pt = cbc_decrypt(cbc_ct, aes, iv);

    ok = ok && ecb_pt.ok && ecb_pt.plaintext == message;
    ok = ok && cbc_pt.ok && cbc_pt.plaintext == message;
    std::cout << "  " << title << ": len=" << message.size()
              << ", ECB ct=" << ecb_ct.size() << " -> "
              << (ecb_pt.ok && ecb_pt.plaintext == message ? "OK" : "FAIL")
              << ", CBC ct=" << cbc_ct.size() << " -> "
              << (cbc_pt.ok && cbc_pt.plaintext == message ? "OK" : "FAIL") << '\n';
    return ok;
}

}  

int main() {
    const Block key = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                       0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f};
    const Block iv = {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
                      0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f};
    AES128 aes(key);

    std::cout << "=== Lab 3, variant 5: AES-128, ECB + CBC, safe unpadding ===\n\n";

    Block plaintext = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
                       0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff};
    Block expected = {0x69, 0xc4, 0xe0, 0xd8, 0x6a, 0x7b, 0x04, 0x30,
                      0xd8, 0xcd, 0xb7, 0x80, 0x70, 0xb4, 0xc5, 0x5a};
    Block ciphertext = aes.encrypt_block(plaintext);
    Block recovered = aes.decrypt_block(expected);
    bool kat = ciphertext == expected && recovered == plaintext;
    std::cout << "FIPS-197 KAT: pt=" << to_hex(plaintext)
              << "\n              ct=" << to_hex(ciphertext)
              << "\n              expected=" << to_hex(expected)
              << "\n              round-trip=" << to_hex(recovered)
              << "\nResult: " << (kat ? "OK" : "FAILED") << "\n\n";
    if (!kat) return 1;

    std::cout << "--- Round trips and padding boundaries ---\n";
    bool all_ok = true;
    all_ok &= round_trip("empty", from_string(""), aes, iv);
    all_ok &= round_trip("short", from_string("A"), aes, iv);
    all_ok &= round_trip("15 bytes", from_string("123456789012345"), aes, iv);
    all_ok &= round_trip("16 bytes", from_string("0123456789abcdef"), aes, iv);
    all_ok &= round_trip("17 bytes", from_string("0123456789abcdefg"), aes, iv);
    all_ok &= round_trip("31 bytes", from_string(std::string(31, 'x')), aes, iv);
    all_ok &= round_trip("32 bytes", from_string(std::string(32, 'x')), aes, iv);
    all_ok &= round_trip("33 bytes", from_string(std::string(33, 'x')), aes, iv);
    all_ok &= round_trip("unicode-free text", from_string("KiSB lab 3 variant 5"), aes, iv);

    std::cout << "\nPadding table (B = 16):\n";
    for (size_t len : {size_t(0), size_t(1), size_t(15), size_t(16),
                       size_t(17), size_t(31), size_t(32), size_t(33)}) {
        Bytes data(len, 0x41);
        Bytes padded = add_pkcs7(data);
        size_t pad = padded.size() - len;
        std::cout << "  L=" << len << " -> pad=" << pad
                  << ", padded length=" << padded.size()
                  << ", last byte=0x" << std::hex << static_cast<int>(padded.back())
                  << std::dec << '\n';
    }

    std::cout << "\n--- Pattern leakage: ECB vs CBC ---\n";
    Bytes pattern;
    for (int i = 0; i < 4; ++i) {
        Bytes block = from_string("AAAAAAAAAAAAAAAA");
        pattern.insert(pattern.end(), block.begin(), block.end());
    }
    Bytes ecb_pattern = ecb_encrypt(pattern, aes);
    Bytes cbc_pattern = cbc_encrypt(pattern, aes, iv);
    print_blocks(ecb_pattern, 4, "ECB ciphertext blocks (identical plaintext blocks):");
    print_blocks(cbc_pattern, 4, "CBC ciphertext blocks (same plaintext, same IV):");
    size_t ecb_unique = 1;
    for (size_t b = 1; b < 4; ++b) {
        ecb_unique += block_at(ecb_pattern, b * 16) != block_at(ecb_pattern, 0);
    }
    size_t cbc_unique = 1;
    for (size_t b = 1; b < 4; ++b) {
        bool seen = false;
        for (size_t j = 0; j < b; ++j) {
            seen = seen || block_at(cbc_pattern, b * 16) == block_at(cbc_pattern, j * 16);
        }
        cbc_unique += !seen;
    }
    std::cout << "  unique ECB blocks: " << ecb_unique << "/4\n"
              << "  unique CBC blocks: " << cbc_unique << "/4\n";
    all_ok &= ecb_unique == 1 && cbc_unique == 4;

    std::cout << "\n--- Padding oracle resistance ---\n";
    Bytes secret = from_string("Variant 5: padding oracle demo");
    Bytes secret_ct = cbc_encrypt(secret, aes, iv);
    UnpadResult honest = cbc_decrypt(secret_ct, aes, iv);
    std::cout << "  Honest CBC decryption: " << (honest.ok ? "OK" : "FAIL")
              << ", plaintext=\"" << (honest.ok ? as_string(honest.plaintext) : "") << "\"\n";
    all_ok &= honest.ok && honest.plaintext == secret;

    std::mt19937 rng(5);
    std::map<std::string, int> unsafe_reasons;
    int safe_ok_count = 0;
    const int trials = 256;
    for (int t = 0; t < trials; ++t) {
        Bytes corrupted = secret_ct;
        uint8_t mask = static_cast<uint8_t>(1 + (rng() % 255));
        corrupted.back() = static_cast<uint8_t>(corrupted.back() ^ mask);
        Bytes raw = cbc_decrypt_raw(corrupted, aes, iv);
        UnsafeUnpadResult unsafe_result = remove_pkcs7_unsafe(raw);
        UnpadResult safe_result = remove_pkcs7_secure(raw);
        ++unsafe_reasons[unsafe_result.reason];
        safe_ok_count += safe_result.ok ? 1 : 0;
    }
    std::cout << "  Corrupted last ciphertext byte, " << trials << " trials:\n";
    for (const auto& entry : unsafe_reasons) {
        std::cout << "    unsafe reason \"" << entry.first << "\": " << entry.second << '\n';
    }
    std::cout << "    secure unpadding accepted: " << safe_ok_count << "/" << trials
              << " (only random chance of valid padding; no reason is exposed)\n";
    all_ok &= safe_ok_count <= 2;

    Block bad_iv = iv;
    bad_iv[0] = static_cast<uint8_t>(bad_iv[0] ^ 0x01);
    Bytes raw_good = cbc_decrypt_raw(secret_ct, aes, iv);
    Bytes raw_bad = cbc_decrypt_raw(secret_ct, aes, bad_iv);
    size_t changed_bytes = 0;
    for (size_t i = 0; i < raw_good.size(); ++i) changed_bytes += raw_good[i] != raw_bad[i];
    std::cout << "\n  IV bit flip changes " << changed_bytes << " plaintext byte(s), all in block 1\n";
    all_ok &= changed_bytes == 1;

    std::cout << "\nOverall: " << (all_ok ? "ALL TESTS PASSED" : "SOME TESTS FAILED") << '\n';
    return all_ok ? 0 : 1;
}
