#include "belt.hpp"
#include "modes.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
using namespace lab3;

unsigned checks = 0;
unsigned failures = 0;

void check(bool condition, const char* name) {
    ++checks;
    if (!condition) {
        ++failures;
        std::fprintf(stderr, "FAIL: %s\n", name);
    }
}

constexpr unsigned digit(char c) {
    return c >= 'a' ? static_cast<unsigned>(c - 'a' + 10)
                    : static_cast<unsigned>(c - '0');
}

template <std::size_t N>
constexpr auto hex(const char (&s)[N]) {
    static_assert(N % 2 == 1, "Even number of hex characters required");
    std::array<Byte, (N - 1) / 2> bytes{};
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        bytes[i] = static_cast<Byte>(16U * digit(s[2 * i]) + digit(s[2 * i + 1]));
    }
    return bytes;
}

constexpr auto key = hex("e9dee72c8f0c0fa62ddb49f46f73964706075316ed247a3739cba38303a98bf6");
constexpr auto plain = hex("b194bac80a08f53b366d008e584a5de4");
constexpr auto encrypted = hex("69cca1c93557c9e3d66bc3e0fa88fa6e");

void block_vectors() {
    // Wrong word order, S-box, or key schedule changes the published ciphertext.
    const Belt cipher(key);
    check(cipher.encrypt_block(plain) == encrypted, "BelT Appendix A block encrypt");
    // This separate vector catches an incorrect inverse even if a round trip passes.
    const Belt inverse(hex("92bd9b1ce5d141015445fbc95e4d0ef2682080aa227d642f2687f93490405511"));
    check(inverse.decrypt_block(hex("e12bdc1ae28257ec703fccf095ee8df1")) ==
          hex("0dc5300600cab840b38448e5e993f421"), "BelT Appendix A block decrypt");
}

void padding() {
    std::array<Byte, 48> bytes{};
    constexpr std::size_t lengths[] = {0, 1, 15, 16, 17, 32};
    for (const auto n : lengths) {
        bytes.fill(0xa5);
        const auto padded = pkcs7_pad(bytes.data(), n, bytes.data(), bytes.size());
        const auto expected = (n / 16 + 1) * 16;
        check(padded.ok && padded.size == expected, "PKCS7 padded size");
        check(bytes[n] == expected - n && bytes[expected - 1] == expected - n,
              "PKCS7 pad bytes");
        const auto unpadded = pkcs7_unpad(bytes.data(), expected);
        check(unpadded.ok && unpadded.size == n, "PKCS7 unpad");
    }
    bytes.fill(0x10);
    bytes[0] = 0x01;
    check(!pkcs7_unpad(bytes.data(), 16).ok, "PKCS7 rejects an early bad pad byte");
    bytes[15] = 0;
    check(!pkcs7_unpad(bytes.data(), 16).ok, "PKCS7 rejects zero pad");
    bytes[15] = 17;
    check(!pkcs7_unpad(bytes.data(), 16).ok, "PKCS7 rejects pad larger than block");
    check(!pkcs7_unpad(bytes.data(), 15).ok, "PKCS7 rejects partial block");
    check(!pkcs7_pad(nullptr, 0, bytes.data(), 15).ok, "PKCS7 checks capacity");
}

void ecb() {
    constexpr auto input = hex("b194bac80a08f53b366d008e584a5de4"
                               "8504fa9d1bb6c7ac252e72c202fdce0d"
                               "5be3d61217b96181fe6786ad716b890b");
    constexpr auto expected = hex("69cca1c93557c9e3d66bc3e0fa88fa6e"
                                  "5f23102ef109710775017f73806da9dc"
                                  "46fb2ed2ce771f26dcb5e5d1569f9ab0");
    const Belt cipher(key);
    std::array<Byte, 64> output{};
    const auto enc = ecb_encrypt(cipher, input.data(), input.size(), output.data(), output.size());
    check(enc.ok && enc.size == 64 && std::memcmp(output.data(), expected.data(), expected.size()) == 0,
          "ECB first three blocks match BelT Appendix A");
    std::array<Byte, 48> decoded{};
    const auto dec = ecb_decrypt(cipher, output.data(), output.size(), decoded.data(), decoded.size());
    check(dec.ok && dec.size == decoded.size() && decoded == input, "ECB full round trip");
    for (const std::size_t n : {0U, 15U, 16U, 17U}) {
        std::memcpy(output.data(), input.data(), n);
        const auto in_place = ecb_encrypt(cipher, output.data(), n, output.data(), output.size());
        const auto restored = ecb_decrypt(cipher, output.data(), in_place.size, output.data(), n);
        check(in_place.ok && restored.ok && restored.size == n
              && std::memcmp(output.data(), input.data(), n) == 0, "ECB in-place edge length");
    }
    const Block invalid = cipher.encrypt_block(Block{});
    decoded.fill(0x5a);
    check(!ecb_decrypt(cipher, invalid.data(), invalid.size(), decoded.data(), decoded.size()).ok
          && decoded.front() == 0x5a && decoded.back() == 0x5a, "ECB rejects pad without writing");
    check(!ecb_decrypt(cipher, invalid.data(), 15, decoded.data(), decoded.size()).ok,
          "ECB rejects a partial ciphertext block");
    check(!ecb_encrypt(cipher, input.data(), 16, output.data(), 16).ok, "ECB checks capacity");
    const auto empty = ecb_encrypt(cipher, nullptr, 0, output.data(), output.size());
    check(empty.ok && ecb_decrypt(cipher, output.data(), empty.size, nullptr, 0).ok,
          "ECB allows empty input and output");
}

void ofb() {
    constexpr auto expected = hex("69cca1c93557c9e3d66bc3e0fa88fa6e"
                                  "940bdf6a8870ebc3d3b2fc2fe3c473d1"
                                  "0dc86e4b44");
    const Belt cipher(key);
    std::array<Byte, expected.size()> zeros{};
    auto output = zeros;
    OfbStream ordinary(cipher, plain);
    check(ordinary.apply(nullptr, nullptr, 0), "OFB empty message");
    check(!ordinary.apply(nullptr, output.data(), 1), "OFB rejects null input");
    check(ordinary.apply(zeros.data(), output.data(), output.size()) && output == expected,
          "OFB derived gamma fixture, including partial block");

    OfbStream cached(cipher, plain);
    output.fill(0);
    check(!cached.prepare(OfbStream::cache_capacity + 1), "OFB checks cache capacity");
    check(cached.apply(output.data(), output.data(), 3) && cached.prepare(21)
          && !cached.prepare(1), "OFB prepares after a partial block");
    check(cached.apply(output.data() + 3, output.data() + 3, 10)
          && cached.apply(output.data() + 13, output.data() + 13, 24) && output == expected,
          "OFB chunked cache plus fallback matches ordinary");
    OfbStream inverse(cipher, plain);
    check(inverse.prepare(output.size()) && inverse.apply(output.data(), output.data(), output.size())
          && output == zeros, "OFB cached in-place decryption");

    std::array<Byte, OfbStream::cache_capacity + 19> input{};
    auto regular = input;
    auto prepared = input;
    input.fill(0xa5);
    OfbStream large(cipher, plain), large_cached(cipher, plain);
    check(large.apply(input.data(), regular.data(), input.size())
          && large_cached.prepare(OfbStream::cache_capacity)
          && large_cached.apply(input.data(), prepared.data(), prepared.size())
          && prepared == regular, "OFB crosses a full cache boundary");
}
}

int main(int argc, char** argv) {
    if (argc > 2) return EXIT_FAILURE;
    if (argc == 1 || std::strcmp(argv[1], "block") == 0) block_vectors();
    else if (std::strcmp(argv[1], "modes") == 0) {
        padding();
        ecb();
        ofb();
    } else return EXIT_FAILURE;
    std::printf("Checks: %u; failures: %u\n", checks, failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
