#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

constexpr std::uint8_t kRegisterMask = 0x1FU;
constexpr std::uint32_t kExperimentLengths[] = {31U, 128U, 1024U};

struct Lfsr {
    std::uint8_t state;
    std::uint8_t taps;

    static std::uint8_t parity(std::uint8_t value) {
        value ^= static_cast<std::uint8_t>(value >> 4U);
        value ^= static_cast<std::uint8_t>(value >> 2U);
        value ^= static_cast<std::uint8_t>(value >> 1U);
        return static_cast<std::uint8_t>(value & 1U);
    }

    std::uint8_t next_bit() {
        const std::uint8_t result = static_cast<std::uint8_t>(state & 1U);
        const std::uint8_t feedback = parity(static_cast<std::uint8_t>(state & taps));
        state = static_cast<std::uint8_t>((state >> 1U) | (feedback << 4U));
        return result;
    }
};

struct PolynomialCase {
    const char* polynomial;
    std::uint8_t taps;
};

constexpr PolynomialCase kPolynomials[] = {
    {"x^5 + x^2 + 1", 0x05U},
    {"x^5 + 1", 0x01U},
    {"x^5 + x^4 + x^2 + 1", 0x15U},
};

constexpr std::uint16_t kSmallPrimes[] = {
    3U, 5U, 7U, 11U, 13U, 17U, 19U, 23U, 29U, 31U, 37U, 41U,
    43U, 47U, 53U, 59U, 61U, 67U, 71U, 73U, 79U, 83U, 89U, 97U,
    101U, 103U, 107U, 109U, 113U, 127U, 131U, 137U, 139U, 149U,
    151U, 157U, 163U, 167U, 173U, 179U, 181U, 191U, 193U, 197U,
    199U, 211U, 223U, 227U, 229U, 233U, 239U, 241U, 251U
};

constexpr std::uint64_t kMillerRabinBases[] = {
    2ULL, 325ULL, 9375ULL, 28178ULL, 450775ULL, 9780504ULL, 1795265022ULL
};

struct PrimalityTestCase {
    std::uint64_t number;
    bool expected_prime;
};

constexpr PrimalityTestCase kPrimalityTestCases[] = {
    {2ULL, true}, {97ULL, true}, {1000000007ULL, true},
    {1ULL, false}, {341ULL, false}, {561ULL, false},
    {1105ULL, false}, {341550071728321ULL, false}
};

std::uint32_t period(std::uint8_t taps, std::uint8_t seed) {
    Lfsr generator{seed, taps};
    const std::uint8_t initial = generator.state;
    std::uint32_t value = 0U;
    do {
        static_cast<void>(generator.next_bit());
        ++value;
    } while (generator.state != initial && value <= 31U);
    return value;
}

void print_statistics(std::uint8_t taps, std::uint8_t seed, std::uint32_t length) {
    Lfsr generator{seed, taps};
    std::uint32_t zeroes = 0U;
    std::uint32_t ones = 0U;
    for (std::uint32_t i = 0U; i < length; ++i) {
        if (generator.next_bit() == 0U) {
            ++zeroes;
        } else {
            ++ones;
        }
    }
    const double expected = static_cast<double>(length) / 2.0;
    const double chi_square =
        ((static_cast<double>(zeroes) - expected) * (static_cast<double>(zeroes) - expected) +
         (static_cast<double>(ones) - expected) * (static_cast<double>(ones) - expected)) / expected;
    std::printf("  test length %u: 0 -> %u, 1 -> %u, chi^2 = %.6f\n",
                length, zeroes, ones, chi_square);
}

void print_sequence(std::uint8_t taps, std::uint8_t seed, std::uint32_t length) {
    Lfsr generator{seed, taps};
    std::printf("Sequence (%u bits): ", length);
    for (std::uint32_t i = 0U; i < length; ++i) {
        std::printf("%u", generator.next_bit());
        if ((i + 1U) % 64U == 0U && i + 1U < length) {
            std::printf("\n");
        }
    }
    std::printf("\n");
}

std::uint64_t select_u64(std::uint64_t when_zero, std::uint64_t when_one, std::uint64_t bit) {
    const std::uint64_t mask = 0ULL - (bit & 1ULL);
    return (when_zero & ~mask) | (when_one & mask);
}

std::uint64_t add_mod(std::uint64_t left, std::uint64_t right, std::uint64_t modulus) {
    const std::uint64_t sum = left + right;
    const std::uint64_t reduced = sum - modulus;
    const std::uint64_t overflow = static_cast<std::uint64_t>(sum < left);
    const std::uint64_t at_least_modulus = static_cast<std::uint64_t>(sum >= modulus);
    return select_u64(sum, reduced, overflow | at_least_modulus);
}

// Exactly 64 iterations: no wide integer type and no dynamic memory are used.
std::uint64_t multiply_mod(std::uint64_t left, std::uint64_t right, std::uint64_t modulus) {
    std::uint64_t result = 0ULL;
    left %= modulus;
    for (unsigned int i = 0U; i < 64U; ++i) {
        const std::uint64_t candidate = add_mod(result, left, modulus);
        result = select_u64(result, candidate, right & 1ULL);
        left = add_mod(left, left, modulus);
        right >>= 1U;
    }
    return result;
}

// Fixed-length square-and-multiply for a 64-bit exponent.
std::uint64_t power_mod(std::uint64_t base, std::uint64_t exponent, std::uint64_t modulus) {
    std::uint64_t result = 1ULL % modulus;
    base %= modulus;
    for (unsigned int i = 0U; i < 64U; ++i) {
        const std::uint64_t product = multiply_mod(result, base, modulus);
        result = select_u64(result, product, exponent & 1ULL);
        base = multiply_mod(base, base, modulus);
        exponent >>= 1U;
    }
    return result;
}

bool miller_rabin_64(std::uint64_t number) {
    if (number < 2ULL) {
        return false;
    }
    if ((number & 1ULL) == 0ULL) {
        return number == 2ULL;
    }

    std::uint64_t odd_part = number - 1ULL;
    unsigned int twos = 0U;
    while ((odd_part & 1ULL) == 0ULL) {
        odd_part >>= 1U;
        ++twos;
    }

    for (std::uint64_t base : kMillerRabinBases) {
        if ((base % number) == 0ULL) {
            continue;
        }
        std::uint64_t value = power_mod(base, odd_part, number);
        if (value == 1ULL || value == number - 1ULL) {
            continue;
        }
        bool witness_passed = false;
        for (unsigned int r = 1U; r < twos; ++r) {
            value = multiply_mod(value, value, number);
            if (value == number - 1ULL) {
                witness_passed = true;
            }
        }
        if (!witness_passed) {
            return false;
        }
    }
    return true;
}

std::uint64_t lfsr_word(Lfsr& generator, unsigned int bits) {
    std::uint64_t value = 0ULL;
    for (unsigned int i = 0U; i < bits; ++i) {
        value = (value << 1U) | static_cast<std::uint64_t>(generator.next_bit());
    }
    return value;
}

bool removed_by_small_prime(std::uint64_t candidate) {
    bool composite = false;
    for (std::uint16_t prime : kSmallPrimes) {
        composite = composite || ((candidate % prime) == 0ULL && candidate != prime);
    }
    return composite;
}

struct PrimeSearchResult {
    std::uint64_t prime;
    std::uint32_t candidates;
    std::uint32_t removed_by_sieve;
    std::uint32_t removed_by_miller_rabin;
};

PrimeSearchResult find_prime(Lfsr& generator, unsigned int bits) {
    PrimeSearchResult result{0ULL, 0U, 0U, 0U};
    const std::uint64_t bit_mask = (1ULL << bits) - 1ULL;
    for (;;) {
        // A degree-5 LFSR has only 31 states.  A Weyl counter prevents the
        // short LFSR cycle from repeating the same p-bit candidate forever;
        // the LFSR remains the source of the pseudorandom bit mask.
        const std::uint64_t stream_word = lfsr_word(generator, bits);
        const std::uint64_t weyl_word =
            static_cast<std::uint64_t>(result.candidates) * 0x9E3779B97F4A7C15ULL;
        std::uint64_t candidate = (stream_word ^ weyl_word) & bit_mask;
        candidate |= (1ULL << (bits - 1U));
        candidate |= 1ULL;
        ++result.candidates;
        if (removed_by_small_prime(candidate)) {
            ++result.removed_by_sieve;
            continue;
        }
        if (!miller_rabin_64(candidate)) {
            ++result.removed_by_miller_rabin;
            continue;
        }
        result.prime = candidate;
        return result;
    }
}

bool run_primality_self_checks() {
    bool all_passed = true;
    for (const PrimalityTestCase& item : kPrimalityTestCases) {
        const bool actual = miller_rabin_64(item.number);
        const bool passed = actual == item.expected_prime;
        std::printf("n = %" PRIu64 ": %s%s\n", item.number,
                    actual ? "prime" : "composite", passed ? "" : " (ERROR)");
        all_passed = all_passed && passed;
    }
    return all_passed;
}

void print_usage(const char* program) {
    std::printf("Usage: %s [bit_length 8..63]\n", program);
    std::printf("       %s --sequence [length 1..4096]\n", program);
}

}  // namespace

int main(int argc, char* argv[]) {
    unsigned int bit_length = 40U;
    if (argc == 3 && std::strcmp(argv[1], "--sequence") == 0) {
        const unsigned long parsed = std::strtoul(argv[2], nullptr, 10);
        if (parsed < 1UL || parsed > 4096UL) {
            print_usage(argv[0]);
            return 1;
        }
        print_sequence(kPolynomials[0].taps, 0x10U, static_cast<std::uint32_t>(parsed));
        return 0;
    }
    if (argc == 2) {
        const unsigned long parsed = std::strtoul(argv[1], nullptr, 10);
        if (parsed < 8UL || parsed > 63UL) {
            print_usage(argv[0]);
            return 1;
        }
        bit_length = static_cast<unsigned int>(parsed);
    } else if (argc > 2) {
        print_usage(argv[0]);
        return 1;
    }

    constexpr std::uint8_t seed = 0x10U;  // Non-zero state: 10000.
    std::printf("Laboratory work 1, variant 12\n");
    std::printf("LFSR seed: 10000; maximum possible period for degree 5: 31\n\n");

    for (const PolynomialCase& item : kPolynomials) {
        const std::uint32_t observed_period = period(item.taps, seed);
        std::printf("f(x) = %-24s period = %u; %s\n", item.polynomial, observed_period,
                    observed_period == 31U ? "primitive" : "not primitive");
        for (std::uint32_t length : kExperimentLengths) {
            print_statistics(item.taps, seed, length);
        }
    }

    std::printf("\nMiller-Rabin self-checks\n");
    const bool self_checks_passed = run_primality_self_checks();
    std::printf("self-check result: %s\n", self_checks_passed ? "PASS" : "FAIL");

    std::printf("\nPrime generation (%u bit candidates)\n", bit_length);
    Lfsr generator{seed, kPolynomials[0].taps};
    const PrimeSearchResult result = find_prime(generator, bit_length);
    std::printf("prime = %" PRIu64 " (0x%" PRIX64 ")\n", result.prime, result.prime);
    std::printf("candidates: %u; sieve rejected: %u; Miller-Rabin rejected: %u\n",
                result.candidates, result.removed_by_sieve, result.removed_by_miller_rabin);
    std::printf("Miller-Rabin bases are deterministic for all unsigned 64-bit inputs.\n");
    return 0;
}
