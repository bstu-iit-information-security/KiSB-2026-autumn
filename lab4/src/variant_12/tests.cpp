#include "arithmetic.hpp"
#include "curve.hpp"
#include "secure.hpp"
#include "protocols.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
using namespace lab4;
unsigned checks = 0;
unsigned failures = 0;
void check(bool value, const char* label) {
    ++checks;
    if (!value) {
        ++failures;
        std::fprintf(stderr, "FAIL %s\n", label);
    }
}
UInt256 number(const char* hex) {
    UInt256 result{};
    check(parse_hex(hex, result), "parse numeric hex");
    return result;
}
UInt256 le_number(const char* hex) {
    Bytes32 bytes{};
    const auto length = std::strlen(hex) / 2;
    check(length <= bytes.size(), "LE fixture fits");
    for (std::size_t i = 0; i < length; ++i) {
        char pair[3] = {hex[2 * i], hex[2 * i + 1], 0};
        UInt256 byte{};
        check(parse_hex(pair, byte), "LE fixture hex byte");
        bytes[i] = static_cast<Byte>(byte.words[0]);
    }
    return from_le(bytes);
}
void arithmetic_tests() {
    const auto prime = number("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff43");
    const auto field = make_modulus(prime);
    const auto one = from_u32(1), two = from_u32(2), seven = from_u32(7);
    const auto minus_one = number("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff42");
    check(equal(mod_add(minus_one, two, field), one) == 1, "modular addition with carry");
    check(equal(mod_sub(one, two, field), minus_one) == 1, "modular subtraction with borrow");
    check(equal(mod_mul(minus_one, minus_one, field), one) == 1, "Montgomery high-limb reduction");
    check(equal(mod_mul(seven, mod_inverse(seven, field), field), one) == 1, "field inversion");
    check(nonzero(mod_inverse({}, field)) == 0, "zero inverse for masked point arithmetic");
    check(equal(from_le(to_le(minus_one)), minus_one) == 1, "integer byte order round trip");
    char text[65]{};
    to_hex(prime, text);
    check(std::strcmp(text, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff43") == 0,
          "raw hex formatting");
    UInt256 invalid{};
    check(!parse_hex("xyz", invalid), "invalid hex rejected");
}
void curve_tests() {
    const auto& c = bign_curve();
    const auto& g = c.generator;
    check(on_curve(c, g) == 1 && g.infinity == 0, "standard generator is on curve");
    const auto doubled = point_double(c, g);
    check(doubled.infinity == 0 && on_curve(c, doubled) == 1, "affine doubling");
    check(point_equal(point_add(c, g, g), doubled) == 1, "addition handles equal points");
    check(point_equal(point_add(c, {}, g), g) == 1, "point at infinity is identity");
    Point inverse{g.x, mod_sub({}, g.y, c.field), 0};
    check(point_add(c, g, inverse).infinity == 1, "opposite points sum to infinity");
    check(multiply_public(c, c.order.value, g).infinity == 1, "generator order q");
    const auto d = le_number("1f66b5b84b7339674533f0329c74f21834281fed0732429e0c79235fc273e269");
    const Point expected{
        le_number("bd1a5650179d79e03fcee49d4c2bd5ddf54ce46d0cf11e4ff87bf7a890857fd0"),
        le_number("7ac6a60361e8c8173491686d461b2826190c2eda5909054a9ab84d2ab9d99a90"), 0};
    MultiplyStats stats;
    const auto actual = multiply_secret(c, d, g, &stats);
    check(point_equal(actual, expected) == 1, "BIGN published public-key vector");
    check(stats.bits == 256 && stats.additions == 256 && stats.doublings == 256,
          "secret scalar uses a fixed schedule");
    check(point_equal(multiply_secret(c, from_u32(3), g), multiply_public(c, from_u32(3), g)) == 1,
          "ladder agrees with double-and-add");
    check(valid_public_key(c, expected) && !valid_public_key(c, {}), "public-key validation");
    Point outside = g;
    outside.x = c.field.value;
    check(!valid_public_key(c, outside), "noncanonical public coordinate rejected");
}
bool failed_entropy(void*, Byte*, std::size_t) { return false; }
void nonce_tests() {
    const auto& order = bign_curve().order;
    NonceBatch batch{};
    const auto none = select_nonce(batch, order);
    check(!none.ok && none.candidates == 100, "all-invalid nonce batch reports failure");
    batch[0] = 7;
    batch[32] = 9;
    const auto first = select_nonce(batch, order);
    check(first.ok && equal(first.value, from_u32(7)) == 1 && first.candidates == 100,
          "first valid nonce selected without early exit");
    batch.fill(0xff);
    for (std::size_t i = batch.size() - 32; i < batch.size(); ++i) batch[i] = 0;
    batch[batch.size() - 32] = 11;
    const auto last = select_nonce(batch, order);
    check(last.ok && equal(last.value, from_u32(11)) == 1 && last.candidates == 100
          && last.limb_comparisons == first.limb_comparisons, "last valid nonce has the same schedule");
    batch.fill(0);
    const auto q = to_le(order.value);
    std::memcpy(batch.data(), q.data(), q.size());
    const auto q_minus_one = mod_sub({}, from_u32(1), order);
    const auto accepted = to_le(q_minus_one);
    std::memcpy(batch.data() + 32, accepted.data(), accepted.size());
    const auto boundary = select_nonce(batch, order);
    check(boundary.ok && equal(boundary.value, q_minus_one), "q is rejected and q-1 accepted");
    check(!generate_nonce(order, {failed_entropy, nullptr}).ok, "entropy failure is explicit");
}

template <std::size_t N>
std::array<Byte, N> raw(const char* hex) {
    check(std::strlen(hex) == N * 2, "byte fixture size");
    std::array<Byte, N> bytes{};
    for (std::size_t i = 0; i < N; ++i) {
        const char pair[3] = {hex[2 * i], hex[2 * i + 1], 0};
        UInt256 value{};
        check(parse_hex(pair, value), "byte fixture hex");
        bytes[i] = static_cast<Byte>(value.words[0]);
    }
    return bytes;
}
bool fixed_entropy(void*, Byte* output, std::size_t size) {
    std::memset(output, 0, size);
    output[0] = 3;
    return true;
}
void protocol_tests() {
    const auto& c = bign_curve();
    const auto message = raw<13>("b194bac80a08f53b366d008e58");
    const auto hash = raw<32>("abef9725d4c5a83597a367d14494cc2542f20f659ddfecc961a3ec550cba8c75");
    check(belt_hash(message.data(), message.size()) == hash, "published belt-hash 13-byte vector");
    const auto aligned = raw<32>("b194bac80a08f53b366d008e584a5de48504fa9d1bb6c7ac252e72c202fdce0d");
    check(belt_hash(aligned.data(), aligned.size()) ==
          raw<32>("749e4c3653aece5e48db4761227742eb6dbe13f4a80f7beff1a9cf8d10ee7786"),
          "published belt-hash aligned vector");
    const auto longer = raw<48>("b194bac80a08f53b366d008e584a5de48504fa9d1bb6c7ac252e72c202fdce0d"
                               "5be3d61217b96181fe6786ad716b890b");
    check(belt_hash(longer.data(), longer.size()) ==
          raw<32>("9d02ee446fb6a29fe5c982d4b13af9d3e90861bc4cef27cf306bfb0b174a154a"),
          "published belt-hash multiblock vector");
    const auto secret = le_number("1f66b5b84b7339674533f0329c74f21834281fed0732429e0c79235fc273e269");
    const auto nonce = le_number("4c0e74b2cd5811ad21f23de7e0fa742c3ed6ec483c461ce15c33a77aa308b7d2");
    const auto pub = multiply_secret(c, secret, c.generator);
    const auto signature = bign_sign_with_nonce(c, hash, secret, nonce);
    const auto expected = raw<48>("e36b7f0377ae4c524027c387fadf1b20ce72f1530b71f2b5fd3a8c584fe2e1ae"
                                 "d20082e30c8af65011f4fb54649dfd3d");
    check(signature.ok && signature.signature == expected, "BIGN published signing vector");
    check(bign_verify(c, hash, pub, expected), "BIGN verifies published signature");
    auto corrupted = expected;
    corrupted[16] ^= 1;  // One byte of S1 (the full-size signature component).
    check(!bign_verify(c, hash, pub, corrupted), "BIGN rejects a changed signature byte");
    auto wrong_hash = hash;
    wrong_hash[0] ^= 1;
    check(!bign_verify(c, wrong_hash, pub, expected), "BIGN binds the message hash");
    check(!bign_verify(c, hash, {}, expected), "BIGN rejects infinity public key");
    auto noncanonical = expected;
    const auto q_bytes = to_le(c.order.value);
    std::memcpy(noncanonical.data() + 16, q_bytes.data(), q_bytes.size());
    check(!bign_verify(c, hash, pub, noncanonical), "BIGN rejects S1 equal to q");
    check(!bign_sign_with_nonce(c, hash, {}, nonce).ok
          && !bign_sign_with_nonce(c, hash, secret, {}).ok, "zero private scalar rejected");

    const auto generated = key_pair(c, {fixed_entropy, nullptr});
    check(generated.ok && equal(generated.secret, from_u32(3)) == 1, "key generation uses the sampler");
    const auto a = ecdh(c, from_u32(3), pub);
    const auto b = ecdh(c, secret, generated.public_key);
    check(a.ok && b.ok && equal(a.x, b.x) == 1, "ECDH parties agree");
    check(equal(a.x, number("5087b5056e065f027fb50355a32f62ba00508ed564953c92dc1a8365eead812d")) == 1,
          "ECDH matches independent integer-arithmetic fixture");
    check(!ecdh(c, secret, {}).ok && !key_pair(c, {failed_entropy, nullptr}).ok,
          "ECDH and key generation reject invalid inputs");
    const auto random_signature = bign_sign(c, hash, secret, {fixed_entropy, nullptr});
    check(random_signature.ok && bign_verify(c, hash, pub, random_signature.signature),
          "normal signing uses fixed-batch nonce selection");
    check(!bign_sign(c, hash, secret, {failed_entropy, nullptr}).ok, "signing propagates RNG failure");
    const auto course = course_sign(c, hash, secret, nonce);
    check(course.ok && course_verify(c, hash, pub, course), "coursework pair equations");
    auto bad_course = course;
    bad_course.s.words[0] ^= 1;
    check(!course_verify(c, hash, pub, bad_course), "coursework pair rejects changed s");
    const auto separate_signature = raw<48>(
        "47a63c8b9c936e94b5fab3d9cbd78366290f3210e163eec8db4e921e8479d413"
        "8f112cc23e6dce65ec5ff21df4231c28");
    check(bign_verify(c, belt_hash(longer.data(), longer.size()), pub, separate_signature),
          "BIGN independent published verification example");
}
}
int main(int argc, char** argv) {
    if (argc != 2) return EXIT_FAILURE;
    if (std::strcmp(argv[1], "arithmetic") == 0) arithmetic_tests();
    else if (std::strcmp(argv[1], "curve") == 0) { curve_tests(); nonce_tests(); }
    else if (std::strcmp(argv[1], "protocols") == 0) protocol_tests();
    else return EXIT_FAILURE;
    std::printf("Checks %u; failures %u\n", checks, failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
