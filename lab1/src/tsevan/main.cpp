// ЛР 1, вариант 12. Цеван К. А.
// Часть 1: LFSR. Часть 2: тест Рабина--Миллера.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <climits>
#include <initializer_list>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#pragma comment(lib, "bcrypt.lib")
#endif

using U64 = std::uint64_t;

struct Lfsr {
    unsigned state, taps;
    Lfsr(unsigned mask, unsigned seed = 1) : state(seed), taps(mask) {}
    unsigned next() {
        unsigned value = state & taps;
        unsigned feedback = 0;
        for (unsigned i = 0; i < 5; ++i)
            feedback ^= (value >> i) & 1u;
        unsigned bit = state & 1u;
        state = (state >> 1) | (feedback << 4);
        return bit;
    }
};

const unsigned MASKS[3] = {5, 1, 21};
const char* POLYNOMIALS[3] = {"x^5+x^2+1", "x^5+1", "x^5+x^4+x^2+1"};

unsigned period(unsigned mask, unsigned seed) {
    Lfsr gen(mask, seed);
    for (unsigned t = 1; t <= 31; ++t) {
        gen.next();
        if (gen.state == seed) return t;
    }
    return 0;
}

// Состояние -- пять битов. Перебор всех 31 ненулевых состояний
// устанавливает максимальность периода и примитивность многочлена.
bool primitive(unsigned mask) {
    bool result = true;
    for (unsigned seed = 1; seed < 32; ++seed)
        result = result & (period(mask, seed) == 31);
    return result;
}

FILE* output_file(const char* folder, const char* name) {
    if (!folder) return nullptr;
    char path[1024];
    if (std::snprintf(path, sizeof(path), "%s/%s", folder, name) >= 1024)
        return nullptr;
    return std::fopen(path, "wb");
}

void statistics(U64 length, const char* folder) {
    FILE* table = output_file(folder, "statistics.csv");
    FILE* correlations = output_file(folder, "autocorrelation.csv");
    if (table) std::fprintf(table, "polynomial,seed,period,primitive,length,zeros,ones,mean,variance,chi2\n");
    if (correlations) std::fprintf(correlations, "polynomial,lag,correlation\n");
    std::printf("ЧАСТЬ 1. LFSR; длина последовательности = %llu; x0 = 00001\n", length);
    std::printf("Частотный критерий: H0 -- P(0)=P(1)=0.5; alpha=0.05; порог chi2=3.841.\n");
    for (unsigned p = 0; p < 3; ++p) {
        Lfsr gen(MASKS[p]);
        U64 ones = 0, xy[20] = {}, sx[20] = {}, sy[20] = {};
        unsigned ring[20] = {};
        for (U64 i = 0; i < length; ++i) {
            unsigned bit = gen.next();
            ones += bit;
            for (unsigned lag = 1; lag <= 20; ++lag) {
                if (i >= lag) {
                    unsigned old = ring[(i - lag) % 20];
                    xy[lag - 1] += bit * old;
                    sx[lag - 1] += bit;
                    sy[lag - 1] += old;
                }
            }
            ring[i % 20] = bit;
        }
        double mean = double(ones) / double(length);
        double variance = mean * (1.0 - mean);
        double diff = 2.0 * double(ones) - double(length);
        double chi2 = diff * diff / double(length);
        unsigned t = period(MASKS[p], 1);
        bool is_primitive = primitive(MASKS[p]);
        std::printf("\n%s: T=%u из 31; примитивный: %s\n", POLYNOMIALS[p], t, is_primitive ? "да" : "нет");
        std::printf("Нулей: %llu; единиц: %llu; M=%.6f; D=%.6f; chi2=%.6f\n", length - ones, ones, mean, variance, chi2);
        if (length >= 10) std::printf("H0 %s.\n", chi2 <= 3.841 ? "не отвергается" : "отвергается");
        else std::printf("Для критерия chi2 нужно хотя бы 10 битов.\n");
        if (table) std::fprintf(table, "%s,1,%u,%u,%llu,%llu,%llu,%.9f,%.9f,%.9f\n", POLYNOMIALS[p], t, unsigned(is_primitive), length, length - ones, ones, mean, variance, chi2);
        std::printf("Автокорреляция, лаги 1..20:");
        for (unsigned lag = 1; lag <= 20; ++lag) {
            if (lag >= length) break;
            double numerator = double(xy[lag - 1]) - mean * double(sx[lag - 1] + sy[lag - 1]) + double(length - lag) * mean * mean;
            double corr = variance == 0 ? 0 : numerator / (double(length) * variance);
            std::printf(" %.3f", corr);
            if (correlations) std::fprintf(correlations, "%s,%u,%.9f\n", POLYNOMIALS[p], lag, corr);
        }
        std::printf("\n");
    }
    if (table) std::fclose(table);
    if (correlations) std::fclose(correlations);
}

// Для a,b<n. Выбор результата маской исключает переполнение a+b.
U64 add_mod(U64 a, U64 b, U64 n) {
    U64 mask = U64(0) - U64(a >= n - b);
    return ((a - (n - b)) & mask) | ((a + b) & ~mask);
}

// Фиксированные 64 шага, без промежуточных динамических контейнеров.
U64 multiply_mod(U64 a, U64 b, U64 n) {
    U64 result = 0;
    for (unsigned i = 0; i < 64; ++i) {
        U64 sum = add_mod(result, a, n);
        U64 mask = U64(0) - ((b >> i) & 1);
        result = (sum & mask) | (result & ~mask);
        a = add_mod(a, a, n);
    }
    return result;
}

U64 power_mod(U64 a, U64 exponent, U64 n) {
    U64 result = 1;
    for (unsigned i = 0; i < 64; ++i) {
        U64 product = multiply_mod(result, a, n);
        U64 mask = U64(0) - ((exponent >> i) & 1);
        result = (product & mask) | (result & ~mask);
        a = multiply_mod(a, a, n);
    }
    return result;
}

bool random_u64(U64& value) {
#ifdef _WIN32
    return BCryptGenRandom(nullptr, reinterpret_cast<PUCHAR>(&value), sizeof(value), BCRYPT_USE_SYSTEM_PREFERRED_RNG) == 0;
#else
    FILE* file = std::fopen("/dev/urandom", "rb");
    if (!file) return false;
    bool ok = std::fread(&value, sizeof(value), 1, file) == 1;
    std::fclose(file);
    return ok;
#endif
}

// Равномерный выбор свидетеля из [2,n-2]. Короткий LFSR не подходит
// для независимых свидетелей, поэтому здесь используется источник ОС.
bool witness(U64 n, U64& a) {
    U64 range = n - 3;
    U64 threshold = (U64(0) - range) % range;
    U64 x;
    do {
        if (!random_u64(x)) return false;
    } while (x < threshold);
    a = 2 + x % range;
    return true;
}

bool miller_round(U64 n, U64 a) {
    U64 d = n - 1;
    unsigned s = 0;
    for (unsigned i = 0; i < 64; ++i) {
        unsigned take = unsigned((d & 1) == 0);
        d >>= take;
        s += take;
    }
    U64 x = power_mod(a % n, d, n);
    bool passed = (x == 1 || x == n - 1);
    for (unsigned r = 1; r < 64; ++r) {
        x = multiply_mod(x, x, n);
        passed = passed | ((r < s) & (x == n - 1));
    }
    return passed;
}

// 1 -- вероятно простое; 0 -- составное; -1 -- ошибка источника ОС.
int miller_rabin(U64 n) {
    if (n < 2) return 0;
    if (n == 2 || n == 3) return 1;
    if ((n & 1) == 0) return 0;
    bool passed = true;
    for (unsigned round = 0; round < 5; ++round) {
        U64 a;
        if (!witness(n, a)) return -1;
        passed = passed & miller_round(n, a);
    }
    return passed ? 1 : 0;
}

unsigned small_primes[54];
unsigned small_count = 0;
void prepare_sieve() {
    small_count = 0;
    for (unsigned p = 2; p < 256; ++p) {
        bool prime = true;
        for (unsigned d = 2; d * d <= p; ++d)
            if (p % d == 0) prime = false;
        if (prime) small_primes[small_count++] = p;
    }
}

bool sieve(U64 n) {
    bool ok = n >= 2;
    for (unsigned i = 0; i < small_count; ++i)
        ok = ok & ((n == small_primes[i]) | (n % small_primes[i] != 0));
    return ok;
}

U64 candidate(Lfsr& gen, unsigned bits) {
    U64 n = 0;
    for (unsigned i = 0; i < bits; ++i) n |= U64(gen.next()) << i;
    return n | (U64(1) << (bits - 1)) | 1;
}

bool generate_primes(unsigned bits, unsigned count, FILE* csv) {
    Lfsr gen(MASKS[0]);
    U64 maximum = bits == 64 ? UINT64_MAX : (U64(1) << bits) - 1;
    std::printf("\nЧАСТЬ 2. %u-битовые числа, пять раундов Рабина--Миллера\n", bits);
    for (unsigned i = 0; i < count; ++i) {
        U64 start = candidate(gen, bits), n = start, tried = 0, sieved = 0, rejected = 0;
        auto begin = std::chrono::steady_clock::now();
        bool found = false;
        while (tried < 1000000) {
            ++tried;
            if (!sieve(n)) ++sieved;
            else {
                int result = miller_rabin(n);
                if (result < 0) { std::fprintf(stderr, "Не удалось получить случайного свидетеля.\n"); return false; }
                if (result == 1) { found = true; break; }
                ++rejected;
            }
            if (n > maximum - 2) n = (U64(1) << (bits - 1)) | 1;
            else n += 2;
        }
        if (!found) { std::fprintf(stderr, "Превышен предел поиска.\n"); return false; }
        double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - begin).count();
        std::printf("n=%llu; начало=%llu; бит=%u; кандидатов=%llu; сито=%llu; тест=%llu; время=%.6f с\n", n, start, bits, tried, sieved, rejected, seconds);
        if (csv) std::fprintf(csv, "%u,%u,%llu,%llu,%llu,%llu,%llu,%.9f\n", bits, i + 1, start, n, tried, sieved, rejected, seconds);
    }
    return true;
}

bool self_test() {
    bool ok = true;
    unsigned expected[3] = {31, 5, 15};
    for (unsigned i = 0; i < 3; ++i) ok &= period(MASKS[i], 1) == expected[i];
    ok &= primitive(5) && !primitive(1) && !primitive(21);
    // Независимое точное пробное деление для малых чисел.
    for (U64 n = 5; n < 2000; n += 2) {
        bool exact = true, tested = true;
        for (U64 d = 2; d * d <= n; ++d) if (n % d == 0) exact = false;
        for (U64 a = 2; a <= 20 && a < n - 1; ++a) tested &= miller_round(n, a);
        ok &= tested == exact;
    }
    const U64 primes[] = {2, 3, 5, 251, 65537, 4294967291ULL, 18446744073709551557ULL};
    for (U64 n : primes) ok &= miller_rabin(n) == 1;
    const U64 composites[] = {0, 1, 4, 9, 25, 341, 561, 1105, 1729, 3215031751ULL};
    for (U64 n : composites) {
        bool prime = n >= 2 && (n & 1);
        if (prime) for (U64 a : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL}) prime &= miller_round(n, a);
        ok &= !prime;
    }
    for (unsigned bits = 3; bits <= 64; ++bits) {
        Lfsr gen(5);
        U64 n = candidate(gen, bits);
        ok &= (n & 1) && (n >> (bits - 1)) == 1;
    }
    ok &= sieve(2) && sieve(251) && !sieve(1) && !sieve(9);
    ok &= multiply_mod(UINT64_MAX - 1, UINT64_MAX - 1, UINT64_MAX) == 1;
    std::printf("Самопроверка: %s\n", ok ? "OK" : "ОШИБКА");
    return ok;
}

bool parse_number(const char* text, U64& value) {
    if (!text || !*text || *text == '-') return false;
    char* end = nullptr;
    value = std::strtoull(text, &end, 10);
    return end && !*end;
}

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif
    prepare_sieve();
    if (argc == 2 && std::strcmp(argv[1], "--self-test") == 0) return self_test() ? 0 : 1;
    bool report = argc == 3 && std::strcmp(argv[1], "--report") == 0;
    U64 length = 10000, bits = 64;
    const char* folder = report ? argv[2] : nullptr;
    if (!report && argc > 1) {
        if (argc != 3 || !parse_number(argv[1], length) || !parse_number(argv[2], bits)) {
            std::fprintf(stderr, "Использование: lab1.exe [длина битность] | --self-test | --report папка\n"); return 2;
        }
    }
    if (length < 1 || length > 100000000 || bits < 3 || bits > 64) {
        std::fprintf(stderr, "Длина: 1..100000000; битность: 3..64.\n"); return 2;
    }
    std::printf("ЛАБОРАТОРНАЯ РАБОТА 1. ВАРИАНТ 12. ЦЕВАН К. А.\n\n");
    statistics(length, folder);
    FILE* csv = output_file(folder, "primes.csv");
    if (folder && !csv) { std::fprintf(stderr, "Папка результатов недоступна.\n"); return 2; }
    if (csv) std::fprintf(csv, "bits,index,start,prime,candidates,sieved,test_rejected,seconds\n");
    bool ok = true;
    if (report) for (unsigned p : {16u, 32u, 64u}) ok &= generate_primes(p, 3, csv);
    else ok = generate_primes(unsigned(bits), 3, csv);
    if (csv) std::fclose(csv);
    std::printf("\nПять независимых раундов дают границу ошибки <= 1/1024 для фиксированного составного кандидата.\n");
    return ok ? 0 : 1;
}
