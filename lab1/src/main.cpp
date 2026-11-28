#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

using u64 = unsigned long long;

static std::mt19937_64 rng(0x5A17C0DEULL);


static u64 mod_pow(u64 base, u64 exp, u64 mod) {
    u64 result = 1 % mod;
    base %= mod;
    while (exp) {
        if (exp & 1) result = static_cast<u64>((__uint128_t)result * base % mod);
        base = static_cast<u64>((__uint128_t)base * base % mod);
        exp >>= 1;
    }
    return result;
}

static u64 gcd_u64(u64 a, u64 b) {
    while (b) { u64 t = a % b; a = b; b = t; }
    return a;
}

static bool miller_rabin(u64 n, int rounds) {
    if (n < 2) return false;
    for (u64 p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL, 23ULL, 29ULL, 31ULL, 37ULL}) {
        if (n == p) return true;
        if (n % p == 0) return false;
    }
    u64 d = n - 1;
    int s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    for (int i = 0; i < rounds; ++i) {
        std::uniform_int_distribution<u64> dist(2, n - 2);
        u64 a = dist(rng);
        u64 x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool witness = true;
        for (int r = 1; r < s; ++r) {
            x = static_cast<u64>((__uint128_t)x * x % n);
            if (x == n - 1) { witness = false; break; }
        }
        if (witness) return false;
    }
    return true;
}


struct Params {
    u64 a;
    u64 b;
};

class CongruentialGenerator {
public:
    CongruentialGenerator(u64 modulus, u64 seed, std::vector<Params> set)
        : modulus_(modulus), state_(seed % modulus), B_(std::move(set)) {
        if (B_.empty()) throw std::runtime_error("empty parameter set B");
        for (const auto& p : B_) {
            if (gcd_u64(p.a, modulus_) != 1) {
                throw std::runtime_error("parameter a must be coprime with N");
            }
        }
    }

    u64 next() {
        std::uniform_int_distribution<size_t> pick(0, B_.size() - 1);
        Params p = B_[pick(rng)];
        state_ = static_cast<u64>((__uint128_t)p.a * state_ + p.b) % modulus_;
        return state_;
    }

    std::vector<u64> generate(size_t length) {
        std::vector<u64> out;
        out.reserve(length);
        for (size_t i = 0; i < length; ++i) out.push_back(next());
        return out;
    }

    u64 maximal_period() const {
        u64 period = 1;
        for (const Params& p : B_) {
            u64 x = 0;
            u64 steps = 0;
            do {
                x = (p.a * x + p.b) % modulus_;
                ++steps;
            } while (x != 0 && steps <= modulus_);
            period = period / gcd_u64(period, steps) * steps;
        }
        return period;
    }

    size_t observed_period(size_t limit) {
        std::vector<int> seen(static_cast<size_t>(modulus_), 0);
        CongruentialGenerator copy = *this;
        for (size_t i = 1; i <= limit; ++i) {
            u64 x = copy.next();
            if (seen[static_cast<size_t>(x)]) return i;
            seen[static_cast<size_t>(x)] = 1;
        }
        return limit;
    }

    u64 modulus() const { return modulus_; }
    const std::vector<Params>& params() const { return B_; }

private:
    u64 modulus_;
    u64 state_;
    std::vector<Params> B_;
};

struct Stats {
    double mean = 0.0;
    double variance = 0.0;
    double chi_square = 0.0;
    u64 max_period = 0;
    size_t first_repeat = 0;
};

static Stats test_sequence(CongruentialGenerator& gen, size_t length) {
    std::vector<u64> seq = gen.generate(length);
    const u64 N = gen.modulus();

    double sum = 0.0;
    for (u64 x : seq) sum += static_cast<double>(x);
    double mean = sum / static_cast<double>(length);
    double var = 0.0;
    for (u64 x : seq) {
        double d = static_cast<double>(x) - mean;
        var += d * d;
    }
    var /= static_cast<double>(length);

    std::vector<double> observed(static_cast<size_t>(N), 0.0);
    for (u64 x : seq) ++observed[static_cast<size_t>(x)];
    double expected = static_cast<double>(length) / static_cast<double>(N);
    double chi = 0.0;
    for (double o : observed) {
        double d = o - expected;
        chi += d * d / expected;
    }

    Stats s;
    s.mean = mean;
    s.variance = var;
    s.chi_square = chi;
    s.max_period = gen.maximal_period();
    s.first_repeat = gen.observed_period(100000);
    return s;
}


struct Proof {
    std::vector<u64> known_factors;  
    std::vector<u64> witnesses;      
    bool verified = false;
};

struct PrimeResult {
    u64 prime = 0;
    u64 F = 1;
    u64 r = 0;
    size_t candidates = 0;
    size_t rejected_small = 0;
    size_t rejected_mr = 0;
    double elapsed_ms = 0.0;
    Proof proof;
};

static std::vector<u64> build_factorization(int bits) {
    static const u64 small_primes[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43};
    u64 threshold = 1ULL << (bits / 2 + 1);
    std::vector<u64> factors;
    u64 F = 1;
    size_t i = 0;
    while (F < threshold) {
        u64 q = small_primes[i++ % (sizeof(small_primes) / sizeof(small_primes[0]))];
        F *= q;
        factors.push_back(q);
    }
    return factors;
}

static bool pocklington(u64 p, u64 F, const std::vector<u64>& factors,
                        std::vector<u64>& witnesses) {
    if ((p - 1) % F != 0 || F * F <= p) return false;
    std::vector<u64> distinct = factors;
    std::sort(distinct.begin(), distinct.end());
    distinct.erase(std::unique(distinct.begin(), distinct.end()), distinct.end());

    witnesses.clear();
    for (u64 q : distinct) {
        u64 exponent = (p - 1) / q;
        u64 witness = 0;
        for (u64 a = 2; a < 1000; ++a) {
            if (mod_pow(a, p - 1, p) != 1) return false;  
            if (gcd_u64(mod_pow(a, exponent, p) - 1, p) == 1) {
                witness = a;
                break;
            }
        }
        if (witness == 0) return false;
        witnesses.push_back(witness);
    }
    return true;
}

static bool small_divisor(u64 n) {
    for (u64 p : {3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL, 23ULL, 29ULL,
                  31ULL, 37ULL, 41ULL, 43ULL, 47ULL, 53ULL, 59ULL, 61ULL,
                  67ULL, 71ULL, 73ULL, 79ULL, 83ULL, 89ULL, 97ULL}) {
        if (n % p == 0) return true;
    }
    return false;
}

static PrimeResult mihailescu_prime(int bits) {
    auto start = std::chrono::high_resolution_clock::now();
    PrimeResult res;
    std::vector<u64> factors = build_factorization(bits);
    u64 F = 1;
    for (u64 q : factors) F *= q;
    res.F = F;
    res.proof.known_factors = factors;

    u64 low = 1ULL << (bits - 1);
    u64 high = (1ULL << bits) - 1;
    u64 r_min = (low - 1) / F + 1;
    u64 r_max = high / F;
    if (r_min > r_max) throw std::runtime_error("bad F for requested bit length");

    std::uniform_int_distribution<u64> dist(r_min, r_max);
    u64 r = dist(rng) | 1ULL;
    for (;;) {
        if (r > r_max) r = r_min | 1ULL;
        u64 p = r * F + 1;
        ++res.candidates;

        if (p >= low && p <= high && !small_divisor(p)) {
            if (miller_rabin(p, 5)) {
                std::vector<u64> witnesses;
                if (pocklington(p, F, factors, witnesses)) {
                    res.prime = p;
                    res.r = r;
                    res.proof.witnesses = witnesses;
                    res.proof.verified = true;
                    break;
                }
            } else {
                ++res.rejected_mr;
            }
        } else {
            ++res.rejected_small;
        }
        r += 2;
    }
    auto stop = std::chrono::high_resolution_clock::now();
    res.elapsed_ms = std::chrono::duration<double, std::milli>(stop - start).count();
    return res;
}


static void self_tests() {
    bool ok = miller_rabin(1000003ULL, 8) && !miller_rabin(1000001ULL, 8) &&
              miller_rabin(2147483647ULL, 8) && !miller_rabin(3215031751ULL, 8);
    std::cout << "self-test Miller-Rabin: " << (ok ? "OK" : "FAILED") << '\n';

    std::vector<u64> w;
    bool proof_ok = pocklington(1000003ULL, 1000002ULL, {2ULL, 3ULL, 166667ULL}, w) ||
                    pocklington(65537ULL, 65536ULL, {2ULL}, w);
    std::cout << "self-test Pocklington:  " << (proof_ok ? "OK" : "FAILED") << '\n';

    CongruentialGenerator g(15, 1, {{1, 1}, {1, 2}, {1, 4}});
    auto seq = g.generate(1000);
    bool in_range = std::all_of(seq.begin(), seq.end(), [](u64 x) { return x < 15; });
    std::cout << "self-test generator:    " << (in_range ? "OK" : "FAILED") << '\n';
}

static void print_stats(const std::string& title, const Stats& s) {
    std::cout << "  " << title << '\n'
              << "    mean = " << std::fixed << std::setprecision(4) << s.mean
              << ", variance = " << s.variance << '\n'
              << "    chi-square (df=14, crit=23.685) = " << s.chi_square
              << " -> " << (s.chi_square < 23.685 ? "uniform" : "NOT uniform") << '\n'
              << "    maximal period = " << s.max_period
              << ", first repeat in sample = " << s.first_repeat << '\n';
}

int main() {
    std::cout << "=== Lab 1, variant 5 ===\n\n";
    self_tests();

    std::cout << "\n--- Stage 1: congruential generator with random parameters ---\n";
    CongruentialGenerator b3(15, 7, {{1, 1}, {1, 2}, {1, 4}});
    CongruentialGenerator b5(15, 7, {{1, 1}, {1, 2}, {1, 4}, {1, 7}, {1, 8}});

    for (size_t len : {size_t(1500), size_t(15000), size_t(150000)}) {
        std::cout << "length = " << len << '\n';
        CongruentialGenerator c3 = b3, c5 = b5;
        print_stats("|B|=3", test_sequence(c3, len));
        print_stats("|B|=5", test_sequence(c5, len));
    }

    std::cout << "\n--- Stage 2: Mihailescu provable prime generator ---\n";
    for (int bits : {16, 24, 30}) {
        PrimeResult p = mihailescu_prime(bits);
        std::cout << "bits = " << bits << '\n'
                  << "  p = " << p.prime << " (bits = " << (64 - __builtin_clzll(p.prime)) << ")\n"
                  << "  F = " << p.F << ", r = " << p.r << '\n'
                  << "  factorization of F:";
        for (u64 q : p.proof.known_factors) std::cout << ' ' << q;
        std::cout << "\n  Pocklington witnesses:";
        for (u64 a : p.proof.witnesses) std::cout << ' ' << a;
        std::cout << "\n  candidates = " << p.candidates
                  << ", small-prime rejects = " << p.rejected_small
                  << ", Miller-Rabin rejects = " << p.rejected_mr
                  << ", time = " << std::fixed << std::setprecision(3) << p.elapsed_ms << " ms"
                  << ", proof = " << (p.proof.verified ? "OK" : "FAILED") << '\n';
    }
    return 0;
}
