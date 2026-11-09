#include "belt.hpp"
#include "modes.hpp"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
using namespace lab3;

// Fixed public inputs for this demonstration only.
constexpr Key demo_key = {
    0xe9, 0xde, 0xe7, 0x2c, 0x8f, 0x0c, 0x0f, 0xa6, 0x2d, 0xdb, 0x49, 0xf4, 0x6f, 0x73, 0x96, 0x47,
    0x06, 0x07, 0x53, 0x16, 0xed, 0x24, 0x7a, 0x37, 0x39, 0xcb, 0xa3, 0x83, 0x03, 0xa9, 0x8b, 0xf6
};
constexpr Block iv = {
    0xb1, 0x94, 0xba, 0xc8, 0x0a, 0x08, 0xf5, 0x3b, 0x36, 0x6d, 0x00, 0x8e, 0x58, 0x4a, 0x5d, 0xe4
};

void print_hex(const Byte* data, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) std::printf("%02x", static_cast<unsigned>(data[i]));
    std::putchar('\n');
}

bool demo_message(const Key& key, const char* text) {
    const auto n = std::strlen(text);
    const auto* input = reinterpret_cast<const Byte*>(text);
    std::array<Byte, 48> ecb{}, ofb{}, decoded{};
    const auto enc = ecb_encrypt(key, input, n, ecb.data(), ecb.size());
    if (!enc.ok) return false;
    const auto dec = ecb_decrypt(key, ecb.data(), enc.size, decoded.data(), decoded.size());
    const bool ecb_ok = dec.ok && dec.size == n && std::memcmp(input, decoded.data(), n) == 0;

    Block message_iv = iv;
    message_iv.back() ^= static_cast<Byte>(n);
    OfbStream sender(key, message_iv), receiver(key, message_iv);
    const bool ofb_ok = sender.apply(input, ofb.data(), n)
        && receiver.apply(ofb.data(), decoded.data(), n)
        && std::memcmp(input, decoded.data(), n) == 0;
    std::printf("Message %zu bytes: %s\n", n, text);
    std::printf("  ECB %zu bytes, pad %zu, restore %s: ", enc.size, enc.size - n, ecb_ok ? "OK" : "FAIL");
    print_hex(ecb.data(), enc.size);
    std::printf("  OFB %zu bytes, restore %s: ", n, ofb_ok ? "OK" : "FAIL");
    print_hex(ofb.data(), n);
    return ecb_ok && ofb_ok;
}

std::size_t show_groups(const char* name, const Byte* bytes) {
    constexpr std::size_t block_size = Block{}.size();
    std::array<const Byte*, 16> representatives{};
    std::size_t unique = 0;
    std::printf("%s groups:", name);
    for (std::size_t i = 0; i < representatives.size(); ++i) {
        const Byte* block = bytes + i * block_size;
        std::size_t group = 0;
        while (group < unique && std::memcmp(block, representatives[group], block_size) != 0) ++group;
        if (group == unique) representatives[unique++] = block;
        std::printf(" %zX", group);
    }
    std::printf(" | distinct %zu/16\n", unique);
    return unique;
}

bool demo_pattern(const Key& key) {
    constexpr std::size_t block_size = Block{}.size();
    constexpr char layout[] = "AAAABBBBAAAABBBB";
    std::array<Byte, 16 * block_size> input{}, ofb{};
    std::array<Byte, 17 * block_size> ecb{};
    for (std::size_t i = 0; i < 16; ++i) {
        std::fill_n(input.data() + i * block_size, block_size, static_cast<Byte>(layout[i]));
    }
    Block pattern_iv = iv;
    pattern_iv.back() ^= 0x80;
    OfbStream stream(key, pattern_iv);
    if (!ecb_encrypt(key, input.data(), input.size(), ecb.data(), ecb.size()).ok
        || !stream.apply(input.data(), ofb.data(), ofb.size())) return false;
    std::puts("\nBlock equality groups (first 16 blocks, excluding ECB padding):");
    const auto plain_count = show_groups("Plain", input.data());
    const auto ecb_count = show_groups("ECB", ecb.data());
    const auto ofb_count = show_groups("OFB", ofb.data());
    return plain_count == 2 && ecb_count == 2 && ofb_count == 16;
}

using Clock = std::chrono::steady_clock;
double microseconds(Clock::duration duration) {
    return std::chrono::duration<double, std::micro>(duration).count();
}

bool benchmark(const Key& key) {
    constexpr std::size_t length = OfbStream::cache_capacity;
    constexpr std::size_t repeats = 7;
    std::array<Byte, length> input{}, regular{}, cached{};
    for (std::size_t i = 0; i < input.size(); ++i) input[i] = static_cast<Byte>(i % 256);
    std::array<double, repeats> ordinary_time{}, prepare_time{}, online_time{}, total_time{};
    for (std::size_t i = 0; i <= repeats; ++i) {
        Block benchmark_iv = iv;
        benchmark_iv.back() ^= static_cast<Byte>(0xa0U + i);
        OfbStream direct(key, benchmark_iv), prepared(key, benchmark_iv);
        const auto a = Clock::now();
        const bool direct_ok = direct.apply(input.data(), regular.data(), length);
        const auto b = Clock::now();
        const bool prep_ok = prepared.prepare(length);
        const auto c = Clock::now();
        const bool cached_ok = prepared.apply(input.data(), cached.data(), length);
        const auto d = Clock::now();
        if (!direct_ok || !prep_ok || !cached_ok || regular != cached) return false;
        if (i == 0) continue;  // Warm-up.
        ordinary_time[i - 1] = microseconds(b - a);
        prepare_time[i - 1] = microseconds(c - b);
        online_time[i - 1] = microseconds(d - c);
        total_time[i - 1] = microseconds(d - b);
    }
    const auto median = [](auto& times) {
        std::sort(times.begin(), times.end());
        return times[times.size() / 2];
    };
    std::printf("\nOFB benchmark, %zu bytes, median of %zu trials, us\n", length, repeats);
    std::printf("  Ordinary: %.3f\n  Prepare: %.3f\n  Online XOR: %.3f\n  Prepare + XOR: %.3f\n",
                median(ordinary_time), median(prepare_time), median(online_time), median(total_time));
    std::puts("  Ciphertexts identical in every trial: OK");
    return true;
}
}

int main() {
    std::puts("Lab 3 | Variant 12 | BelT, ECB + OFB");
    const bool ok = demo_message(demo_key, "BelT demo!")
        && demo_message(demo_key, "Sixteen-byte msg")
        && demo_message(demo_key, "This message is longer than one block.")
        && demo_pattern(demo_key)
        && benchmark(demo_key);
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
