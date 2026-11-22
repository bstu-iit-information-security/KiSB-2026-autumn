#include "protocols.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
using namespace lab4;
constexpr std::size_t max_message_bytes = 256;

struct Message {
    std::array<Byte, max_message_bytes> bytes{};
    std::size_t size = 0;
};
struct Vector {
    const char* message;
    const char* hash;
};
constexpr Vector vectors[] = {
    {"b194bac80a08f53b366d008e58",
     "abef9725d4c5a83597a367d14494cc2542f20f659ddfecc961a3ec550cba8c75"},
    {"b194bac80a08f53b366d008e584a5de48504fa9d1bb6c7ac252e72c202fdce0d",
     "749e4c3653aece5e48db4761227742eb6dbe13f4a80f7beff1a9cf8d10ee7786"},
    {"b194bac80a08f53b366d008e584a5de48504fa9d1bb6c7ac252e72c202fdce0d"
     "5be3d61217b96181fe6786ad716b890b",
     "9d02ee446fb6a29fe5c982d4b13af9d3e90861bc4cef27cf306bfb0b174a154a"}
};

bool parse_message(const char* hex, Message& message) {
    const auto length = std::strlen(hex);
    if (length > 2 * message.bytes.size() || length % 2 != 0) return false;
    Message result{};
    result.size = length / 2;
    for (std::size_t i = 0; i < result.size; ++i) {
        const char pair[3] = {hex[2 * i], hex[2 * i + 1], 0};
        UInt256 byte{};
        if (!parse_hex(pair, byte)) return false;
        result.bytes[i] = static_cast<Byte>(byte.words[0]);
    }
    message = result;
    return true;
}

void print_number(const char* name, const UInt256& n) {
    char hex[65]{};
    to_hex(n, hex);
    std::printf("%s %s\n", name, hex);
}

void print_bytes(const char* name, const Byte* bytes, std::size_t size) {
    std::printf("%s ", name);
    for (std::size_t i = 0; i < size; ++i) std::printf("%02x", static_cast<unsigned>(bytes[i]));
    std::putchar('\n');
}

bool signature_demo(const Curve& c, const KeyPair& signer, const Message& message,
                    const char* expected_hash) {
    const auto hash = belt_hash(message.bytes.data(), message.size);
    if (expected_hash) {
        Message expected;
        if (!parse_message(expected_hash, expected) || expected.size != hash.size()
            || std::memcmp(expected.bytes.data(), hash.data(), hash.size()) != 0) return false;
    }
    const auto signature = bign_sign(c, hash, signer.secret, system_entropy());
    if (!signature.ok) return false;
    const bool verified = bign_verify(c, hash, signer.public_key, signature.signature);
    auto corrupt = signature.signature;
    corrupt[16] ^= 1;
    const bool rejected = !bign_verify(c, hash, signer.public_key, corrupt);
    std::printf("\nMessage length %zu bytes\n", message.size);
    print_bytes("M", message.bytes.data(), message.size);
    print_bytes("H", hash.data(), hash.size());
    print_bytes("S0", signature.signature.data(), 16);
    print_bytes("S1", signature.signature.data() + 16, 32);
    std::printf("BIGN signature verification %s\n", verified ? "OK" : "FAIL");
    std::printf("Changed one byte of S1 %s\n", rejected ? "REJECTED" : "FAIL");
    if (expected_hash) std::puts("Published belt-hash vector OK");
    return verified && rejected;
}

bool nonce_demo(const Curve& c) {
    NonceBatch first_batch{}, last_batch{}, invalid_batch{};
    first_batch[0] = 7;
    last_batch[last_batch.size() - 32] = 11;
    const auto first = select_nonce(first_batch, c.order);
    const auto last = select_nonce(last_batch, c.order);
    const auto invalid = select_nonce(invalid_batch, c.order);
    std::printf("\nFixed-batch nonce selection\n");
    std::printf("First valid candidate %zu attempts, %zu limb comparisons\n",
                first.candidates, first.limb_comparisons);
    std::printf("Last valid candidate %zu attempts, %zu limb comparisons\n",
                last.candidates, last.limb_comparisons);
    std::printf("All candidates invalid %s after %zu attempts\n",
                invalid.ok ? "FAIL" : "REJECTED", invalid.candidates);
    MultiplyStats small{}, large{};
    const auto one = multiply_secret(c, from_u32(1), c.generator, &small);
    const auto large_scalar = mod_sub(c.order.value, from_u32(1), c.order);
    const auto many = multiply_secret(c, large_scalar, c.generator, &large);
    std::printf("Scalar 1 %zu bits, %zu additions, %zu doublings\n",
                small.bits, small.additions, small.doublings);
    std::printf("Scalar q-1 %zu bits, %zu additions, %zu doublings\n",
                large.bits, large.additions, large.doublings);
    return first.ok && last.ok && !invalid.ok && point_equal(one, c.generator)
        && point_add(c, many, c.generator).infinity == 1;
}

bool course_demo(const Curve& c, const KeyPair& signer) {
    Message message;
    parse_message(vectors[0].message, message);
    const auto hash = belt_hash(message.bytes.data(), message.size);
    const auto nonce = generate_nonce(c.order, system_entropy());
    if (!nonce.ok) return false;
    const auto signature = course_sign(c, hash, signer.secret, nonce.value);
    const bool verified = course_verify(c, hash, signer.public_key, signature);
    auto corrupt = signature;
    corrupt.s.words[0] ^= 1;
    const bool rejected = !course_verify(c, hash, signer.public_key, corrupt);
    std::puts("\nSeparate coursework equations (GOST-style r,s)");
    print_number("r", signature.r);
    print_number("s", signature.s);
    std::printf("Coursework signature %s; changed s %s\n",
                verified ? "OK" : "FAIL", rejected ? "REJECTED" : "FAIL");
    return verified && rejected;
}

bool run(const Message* custom) {
    const auto& c = bign_curve();
    std::puts("Lab 4 | Variant 12 | Yaroma A. I.");
    std::puts("Affine bign-curve256v1 | ECDH | BIGN with belt-hash");
    std::puts("Numbers and coordinates use big-endian hex; byte strings retain byte order.");
    print_number("p", c.field.value);
    print_number("a", c.a);
    print_number("b", c.b);
    print_number("q", c.order.value);
    print_number("Gx", c.generator.x);
    print_number("Gy", c.generator.y);
    const auto alice = key_pair(c, system_entropy());
    const auto bob = key_pair(c, system_entropy());
    if (!alice.ok || !bob.ok) return false;
    print_number("Alice.Qx", alice.public_key.x);
    print_number("Alice.Qy", alice.public_key.y);
    print_number("Bob.Qx", bob.public_key.x);
    print_number("Bob.Qy", bob.public_key.y);
    const auto a = ecdh(c, alice.secret, bob.public_key);
    const auto b = ecdh(c, bob.secret, alice.public_key);
    if (!a.ok || !b.ok || !equal(a.x, b.x)) return false;
    print_number("Alice.SharedX", a.x);
    print_number("Bob.SharedX", b.x);
    std::puts("ECDH shared secrets MATCH");
    if (custom) {
        if (!signature_demo(c, alice, *custom, nullptr)) return false;
    } else {
        for (const auto& vector : vectors) {
            Message message;
            if (!parse_message(vector.message, message)
                || !signature_demo(c, alice, message, vector.hash)) return false;
        }
    }
    return nonce_demo(c) && course_demo(c, alice);
}
}

int main(int argc, char** argv) {
    Message message;
    if (argc > 2 || (argc == 2 && !parse_message(argv[1], message))) {
        std::fprintf(stderr, "Expected one raw hex message, even length, at most 256 bytes.\n");
        return EXIT_FAILURE;
    }
    if (!run(argc == 2 ? &message : nullptr)) {
        std::fprintf(stderr, "FAILED: entropy source, input validation or cryptographic check.\n");
        return EXIT_FAILURE;
    }
    std::puts("\nAll demonstration checks passed.");
    return EXIT_SUCCESS;
}
