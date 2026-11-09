// КиСБ, лабораторная работа №1, вариант 8.
// Этап 1: аддитивный генератор x(t+1) = (x(t) + x(t-1)) mod 30.
// Этап 2: генерация простых чисел, тест на основе малой теоремы Ферма.

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

#include <array>
#include <cstdio>
#include <iostream>

#include "additive_generator.hpp"
#include "bignum.hpp"
#include "chi_square.hpp"
#include "fermat_test.hpp"
#include "prime_generator.hpp"

namespace {

// Стартовые значения с максимальным периодом (см. пункт меню 2).
const uint32_t kSeed0 = 0;
const uint32_t kSeed1 = 1;

void print_sequence() {
    std::printf("Длина последовательности: ");
    uint32_t len = 0;
    if (!(std::cin >> len)) return;
    AdditiveGenerator g(kSeed0, kSeed1);
    for (uint32_t i = 0; i < len; ++i) {
        std::printf("%3u", g.next());
        if ((i + 1) % 20 == 0) std::printf("\n");
    }
    std::printf("\n");
}

void seed_search() {
    std::array<uint32_t, kN * kN + 1> hist{};
    for (uint32_t x0 = 0; x0 < kN; ++x0)
        for (uint32_t x1 = 0; x1 < kN; ++x1)
            ++hist[period_of(AdditiveGenerator(x0, x1))];

    const SeedSearchResult r = find_best_seed();
    std::printf("\nПеребор всех %u стартовых пар (x0, x1):\n", kN * kN);
    std::printf("  период   число пар\n");
    for (uint32_t t = 1; t < hist.size(); ++t)
        if (hist[t] != 0) std::printf("  %6u   %9u\n", t, hist[t]);
    std::printf("\nМаксимальный период: %u (пар: %u), первая пара: x0=%u, x1=%u\n",
                r.max_period, r.pairs_with_max, r.best_x0, r.best_x1);
}

void statistics() {
    const AdditiveGenerator g(kSeed0, kSeed1);
    const uint32_t period = period_of(g);

    std::printf("\nЧастоты за один период (%u членов, ожидание %.1f):\n", period,
                static_cast<double>(period) / kN);
    const std::array<uint32_t, kN> f = frequencies(g, period);
    for (uint32_t k = 0; k < kN; ++k) {
        std::printf("  %2u:%u", k, f[k]);
        if ((k + 1) % 10 == 0) std::printf("\n");
    }

    std::printf("\nКритерий Пирсона, x0=%u, x1=%u (крит. значение %.3f):\n",
                kSeed0, kSeed1, kChi2Critical);
    const uint32_t sizes[] = {120, 240, 360, 1000, 10000, 100000};
    for (uint32_t n : sizes) {
        const Chi2Result c = chi_square(g, n);
        std::printf("  n=%6u  chi2=%10.3f  %s\n", n, c.chi2,
                    c.uniform ? "равномерно" : "отвергнуто");
    }

    std::printf("\nКритерий Пирсона для разных стартовых пар, n=1000:\n");
    const uint32_t seeds[][2] = {{0, 0}, {0, 15}, {10, 20}, {6, 12},
                                 {5, 10}, {2, 4},  {0, 1}};
    for (const auto& s : seeds) {
        const AdditiveGenerator gs(s[0], s[1]);
        const Chi2Result c = chi_square(gs, 1000);
        std::printf("  x0=%2u x1=%2u  период=%3u  chi2=%9.1f  %s\n", s[0], s[1],
                    period_of(gs), c.chi2, c.uniform ? "равномерно" : "отвергнуто");
    }
}

void prime_search() {
    std::printf("Разрядность p (16..%d): ", kMaxBits);
    int p = 0;
    if (!(std::cin >> p)) return;
    if (p < 16 || p > kMaxBits) {
        std::printf("Недопустимая разрядность.\n");
        return;
    }
    AdditiveGenerator g(kSeed0, kSeed1);
    RandomBits rnd(g);
    SearchLog log;
    const BigNum prime = generate_prime(rnd, p, log);

    std::printf("\nНайдено простое число (%d бит):\n  %s\n", prime.bit_length(),
                to_dec(prime).c_str());
    std::printf("Лог:\n");
    std::printf("  кандидатов всего:        %u\n", log.candidates);
    std::printf("  отсеяно малыми простыми: %u\n", log.sieved);
    std::printf("  отсеяно тестом Ферма:    %u\n", log.fermat_rejected);
    std::printf("  время просеивания:       %.3f мс\n", log.sieve_ms);
    std::printf("  время теста Ферма:       %.3f мс\n", log.fermat_ms);
    std::printf("  общее время:             %.3f мс\n", log.total_ms);
}

int passed = 0, failed = 0;
void check(bool ok, const char* what) {
    std::printf("  [%s] %s\n", ok ? " ok " : "FAIL", what);
    ++(ok ? passed : failed);
}

void self_test() {
    passed = failed = 0;
    std::printf("\nПроверка корректности:\n");

    // Генератор: 0,1,1,2,3,5,8,13,21,34 mod 30 = 4, ...
    const uint32_t expect[12] = {0, 1, 1, 2, 3, 5, 8, 13, 21, 4, 25, 29};
    AdditiveGenerator g(0, 1);
    bool ok = true;
    for (uint32_t e : expect) ok = ok && g.next() == e;
    check(ok, "первые 12 членов совпадают с ручным расчётом");
    check(period_of(AdditiveGenerator(0, 1)) == 120, "период при (0, 1) равен 120");
    const SeedSearchResult r = find_best_seed();
    check(r.max_period == 120 && r.pairs_with_max == 480,
          "максимальный период 120, достигается на 480 парах");

    // Тест Ферма на известных простых числах.
    AdditiveGenerator g2(kSeed0, kSeed1);
    RandomBits rnd(g2);
    check(fermat_test(BigNum::from_u64(1000000007ULL), 5, rnd), "1000000007 -- простое");
    check(fermat_test(BigNum::from_u64(2305843009213693951ULL), 5, rnd),
          "2^61 - 1 -- простое");
    check(fermat_test(from_hex("7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), 5, rnd),
          "2^127 - 1 -- простое");
    check(fermat_test(from_hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F"),
                      5, rnd),
          "2^256 - 2^32 - 977 (256 бит) -- простое");

    // Тест Ферма на известных составных числах.
    check(!fermat_test(BigNum::from_u64(1000000007ULL * 998244353ULL), 5, rnd),
          "1000000007 * 998244353 -- составное");
    check(!fermat_test(from_hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"), 5, rnd),
          "2^128 - 1 -- составное");

    // 341 = 11 * 31: псевдопростое по основанию 2.
    const BigNum n341 = BigNum::from_u64(341), e340 = BigNum::from_u64(340);
    const BigNum one = BigNum::from_u64(1);
    check(pow_mod(BigNum::from_u64(2), e340, n341) == one &&
              pow_mod(BigNum::from_u64(3), e340, n341) != one,
          "341: 2^340 = 1, но 3^340 != 1 (mod 341)");

    // 561 = 3 * 11 * 17 -- число Кармайкла: сравнение Ферма выполняется
    // для всех взаимно простых оснований, тест Ферма его не различает.
    const BigNum n561 = BigNum::from_u64(561), e560 = BigNum::from_u64(560);
    bool all = true;
    for (uint64_t a = 2; a < 561; ++a) {
        const BigNum A = BigNum::from_u64(a);
        if (gcd(A, n561) == one && pow_mod(A, e560, n561) != one) all = false;
    }
    check(all, "561 (число Кармайкла): a^560 = 1 для всех взаимно простых a");

    check(small_primes()[kSmallPrimesCount - 1] == 1999, "решето: 303 простых, последнее 1999");

    std::printf("Итог: пройдено %d, провалено %d\n", passed, failed);
}

}  // namespace

int main() {
#if defined(_WIN32)
    SetConsoleOutputCP(CP_UTF8);
#endif
    for (;;) {
        std::printf(
            "\n=== КиСБ, ЛР1, вариант 8 ===\n"
            "1 - сгенерировать последовательность\n"
            "2 - подбор стартовых значений (период)\n"
            "3 - частоты и критерий Пирсона\n"
            "4 - генерация простого числа\n"
            "5 - проверка корректности\n"
            "0 - выход\n"
            "Выбор: ");
        int choice = -1;
        if (!(std::cin >> choice) || choice == 0) break;
        switch (choice) {
            case 1: print_sequence(); break;
            case 2: seed_search(); break;
            case 3: statistics(); break;
            case 4: prime_search(); break;
            case 5: self_test(); break;
            default: std::printf("Нет такого пункта.\n");
        }
    }
    return 0;
}
