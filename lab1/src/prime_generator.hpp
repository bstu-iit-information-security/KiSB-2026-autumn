#pragma once
// Этап 2: генерация простого числа по схеме из задания:
//   1) случайное p-битовое число n;
//   2) старший и младший биты устанавливаются в 1;
//   3) проверка делимости на малые простые (< 2000);
//   4) пять раундов теста Ферма; при провале -- следующий кандидат.

#include <array>
#include <chrono>
#include <cstdint>

#include "bignum.hpp"
#include "fermat_test.hpp"

const uint32_t kSieveLimit = 2000;
const int kSmallPrimesCount = 303;  // количество простых чисел меньше 2000

// Таблица малых простых -- решето Эратосфена.
inline std::array<uint32_t, kSmallPrimesCount> small_primes() {
    std::array<bool, kSieveLimit> composite{};
    std::array<uint32_t, kSmallPrimesCount> primes{};
    int count = 0;
    for (uint32_t i = 2; i < kSieveLimit; ++i) {
        if (composite[i]) continue;
        primes[count++] = i;
        for (uint32_t j = i * i; j < kSieveLimit; j += i) composite[j] = true;
    }
    return primes;
}

inline bool divisible_by_small_prime(const BigNum& n,
                                     const std::array<uint32_t, kSmallPrimesCount>& primes) {
    for (uint32_t p : primes)
        if (mod_small(n, p) == 0 && n != BigNum::from_u64(p)) return true;
    return false;
}

// Случайный p-битовый нечётный кандидат.
inline BigNum random_candidate(RandomBits& rnd, int p) {
    BigNum x;
    for (int i = 0; i < (p + 31) / 32; ++i) x.w[i] = rnd.next32();
    for (int i = p; i < kLimbs * 32; ++i) x.w[i / 32] &= ~(1u << (i % 32));
    x.set_bit(p - 1);  // старший бит -- число ровно p-битовое
    x.set_bit(0);      // младший бит -- число нечётное
    return x;
}

struct SearchLog {
    uint32_t candidates = 0;       // всего кандидатов
    uint32_t sieved = 0;           // отсеяно малыми простыми
    uint32_t fermat_rejected = 0;  // отсеяно тестом Ферма
    double sieve_ms = 0.0;
    double fermat_ms = 0.0;
    double total_ms = 0.0;
};

inline BigNum generate_prime(RandomBits& rnd, int p, SearchLog& log) {
    using clock = std::chrono::steady_clock;
    const auto start = clock::now();
    const std::array<uint32_t, kSmallPrimesCount> primes = small_primes();
    const BigNum two = BigNum::from_u64(2);

    BigNum n = random_candidate(rnd, p);
    for (;;) {
        ++log.candidates;

        const auto t0 = clock::now();
        const bool divisible = divisible_by_small_prime(n, primes);
        const auto t1 = clock::now();
        log.sieve_ms += std::chrono::duration<double, std::milli>(t1 - t0).count();

        if (divisible) {
            ++log.sieved;
        } else {
            const bool prime = fermat_test(n, 5, rnd);
            const auto t2 = clock::now();
            log.fermat_ms += std::chrono::duration<double, std::milli>(t2 - t1).count();
            if (prime) {
                log.total_ms = std::chrono::duration<double, std::milli>(t2 - start).count();
                return n;
            }
            ++log.fermat_rejected;
        }

        // Следующий кандидат -- следующее нечётное число
        // (методичка допускает последовательный перебор).
        add(n, two, n);
        if (n.bit_length() > p) n = random_candidate(rnd, p);
    }
}
