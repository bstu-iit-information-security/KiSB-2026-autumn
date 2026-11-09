// Independent exhaustive error patterns; the decoder never receives their positions.
#ifdef _MSC_VER
#define _CRT_SECURE_NO_WARNINGS
#endif
#include <initializer_list>
#define main lab2_demo_main
#include "main.cpp"
#undef main

static unsigned tests = 0U;
static unsigned failures = 0U;
static void expect(bool condition) {
    ++tests;
    failures += static_cast<unsigned>(!condition);
}

int main() {
    expect(hamming_self_check());
    expect(iterative_self_check());
    static uint8_t info[kMaxInfoBits]{};
    static uint8_t sent[kMaxCodeBits]{};
    static uint8_t received[kMaxCodeBits]{};
    static HammingCode h;
    for (unsigned k : {4U, 16U, 80U, 2048U}) {
        for (unsigned d : {3U, 4U}) {
            build_hamming(h, k, d);
            for (unsigned j = 0; j < k; ++j) info[j] = static_cast<uint8_t>((j * 7U + 1U) & 1U);
            hamming_encode(h, info, sent);
            memcpy(received, sent, h.n);
            expect(hamming_decode(h, received).syndrome == 0U);
            for (unsigned j = 0; j < h.n; ++j) {
                memcpy(received, sent, h.n);
                received[j] ^= 1U;
                const auto decoded = hamming_decode(h, received);
                expect(decoded.status == DecodeStatus::kCorrected && memcmp(sent, received, h.n) == 0);
            }
            if (k == 80U) {
                for (unsigned a = 0; a < h.n; ++a) {
                    for (unsigned b = a + 1U; b < h.n; ++b) {
                        memcpy(received, sent, h.n);
                        received[a] ^= 1U;
                        received[b] ^= 1U;
                        const auto decoded = hamming_decode(h, received);
                        expect(decoded.syndrome != 0U);
                        if (d == 4U) expect(decoded.status == DecodeStatus::kDetected);
                    }
                }
            }
        }
    }
    for (const auto& variant : kVariantRows) {
        for (unsigned groups = 2U; groups <= variant.max_groups; ++groups) {
            for (unsigned total = 0U; total < 2U; ++total) {
                IterativeCode code{};
                expect(build_iterative(code, variant, groups, total != 0U));
                for (uint64_t value : {0ULL, 0xFFFFFULL, 0x539A6ULL}) {
                    const auto original = iterative_encode(code, value);
                    expect(same_word(iterative_decode(code, original).word, original));
                    for (unsigned bit = 0; bit < code.n; ++bit) {
                        auto damaged = original;
                        flip_position(code, damaged, bit);
                        const auto decoded = iterative_decode(code, damaged);
                        expect(!decoded.rejected && decoded.corrections == 1U && same_word(decoded.word, original));
                    }
                }
                SplitMix64 rng{12U};
                for (unsigned trial = 0U; trial < 1000U; ++trial) {
                    const auto original = iterative_encode(code, rng.next() & 0xFFFFFULL);
                    auto damaged = original;
                    unsigned positions[4];
                    pick_positions(rng, code.n, 4U, positions);
                    for (unsigned j : positions) flip_position(code, damaged, j);
                    const auto decoded = iterative_decode(code, damaged);
                    if (decoded.rejected) expect(same_word(decoded.word, damaged));
                    else {
                        const auto check = iterative_encode(code, decoded.word.info);
                        expect(same_word(decoded.word, check));
                    }
                }
            }
        }
    }
    // Four information errors at the corners of a rectangle escape H/V checks.
    IterativeCode code{};
    build_iterative(code, kVariantRows[0], 2U, false);
    auto damaged = iterative_encode(code, 0U);
    for (unsigned bit : {0U, 1U, 5U, 6U}) flip_position(code, damaged, bit);
    expect(iterative_decode(code, damaged).syndrome == 0U);
    printf("Assertions: %u; failures: %u\n", tests, failures);
    return failures == 0U ? 0 : 1;
}
