// ЛР 2. Цеван К. А. Часть 1 -- Хемминг; часть 2 -- вариант 2 таблицы 5.2.
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif

using U64 = std::uint64_t;
constexpr unsigned MAX_BITS = 2080;

unsigned weight(U64 x) {
    x -= (x >> 1) & 0x5555555555555555ULL;
    x = (x & 0x3333333333333333ULL) + ((x >> 2) & 0x3333333333333333ULL);
    x = (x + (x >> 4)) & 0x0f0f0f0f0f0f0f0fULL;
    return unsigned((x * 0x0101010101010101ULL) >> 56);
}

// Фиксированный seed делает случайные позиции ошибок воспроизводимыми.
struct Random {
    U64 state;
    explicit Random(U64 seed = 12) : state(seed) {}
    U64 next() {
        state += 0x9e3779b97f4a7c15ULL;
        U64 z = state;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    unsigned below(unsigned n) {
        U64 threshold = (U64(0) - n) % n, x;
        do { x = next(); } while (x < threshold);
        return unsigned(x % n);
    }
};

void print_bits(const char* name, const unsigned char* bits, unsigned length) {
    std::printf("%s=", name);
    for (unsigned i = 0; i < length; ++i) std::printf("%u", bits[i]);
    std::printf("\n");
}

bool same(const unsigned char* a, const unsigned char* b, unsigned n) {
    unsigned difference = 0;
    for (unsigned i = 0; i < n; ++i) difference |= a[i] ^ b[i];
    return difference == 0;
}

void inject(unsigned char* word, unsigned n, unsigned count,
            unsigned char* error, Random& random) {
    std::memset(error, 0, n);
    unsigned chosen = 0;
    while (chosen < count) {
        unsigned pos = random.below(n);
        if (!error[pos]) { error[pos] = 1; word[pos] ^= 1; ++chosen; }
    }
}

FILE* output_file(const char* folder, const char* name) {
    if (!folder) return nullptr;
    char path[1024];
    if (std::snprintf(path, sizeof(path), "%s/%s", folder, name) >= 1024) return nullptr;
    return std::fopen(path, "wb");
}

struct Hamming {
    unsigned k, r, n, base_r;
    bool extended;
    unsigned columns[MAX_BITS] = {};

    Hamming(unsigned length, bool use_extension) : k(length), extended(use_extension) {
        base_r = 2;
        while ((1u << base_r) < k + base_r + 1) ++base_r;
        r = base_r + unsigned(extended);
        n = k + r;
        unsigned index = 0;
        // Столбцы P': сначала все числа веса 2, затем веса 3 и т.д.
        for (unsigned w = 2; w <= base_r && index < k; ++w)
            for (unsigned value = 1; value < (1u << base_r) && index < k; ++value)
                if (weight(value) == w) {
                    columns[index++] = extended ? (value << 1) | (1u ^ (w & 1u)) : value;
                }
        // Последние r столбцов -- единичная матрица.
        for (unsigned j = 0; j < r; ++j) columns[k + j] = 1u << (r - j - 1);
    }

    unsigned syndrome(const unsigned char* word) const {
        unsigned result = 0;
        for (unsigned i = 0; i < n; ++i)
            result ^= columns[i] & (0u - unsigned(word[i]));
        return result;
    }

    void encode(const unsigned char* data, unsigned char* word) const {
        std::memcpy(word, data, k);
        std::memset(word + k, 0, r);
        unsigned parity = syndrome(word);
        for (unsigned j = 0; j < r; ++j) word[k + j] = (parity >> (r - j - 1)) & 1;
    }

    // Результат: 0 -- без обнаруженных ошибок, 1 -- исправлена одиночная,
    // 2 -- обнаружено, но исправление не выполняется.
    unsigned decode(const unsigned char* received, unsigned char* corrected,
                    unsigned char* error) const {
        unsigned s = syndrome(received);
        bool allowed = s != 0;
        // В канонической расширенной H чётность веса синдрома равна
        // общей проверке чётности принятого слова.
        if (extended) allowed &= (weight(s) & 1u) != 0;
        unsigned matches = 0;
        for (unsigned j = 0; j < n; ++j) matches += unsigned(columns[j] == s);
        allowed &= matches == 1;
        for (unsigned j = 0; j < n; ++j) {
            error[j] = static_cast<unsigned char>(allowed && columns[j] == s);
            corrected[j] = received[j] ^ error[j];
        }
        return s == 0 ? 0 : allowed ? 1 : 2;
    }

    void print_matrix() const {
        std::printf("H=[P'|I], %u строк, %u столбцов:\n", r, n);
        for (unsigned row = 0; row < r; ++row) {
            for (unsigned col = 0; col < n; ++col) {
                if (col == k) std::printf(" | ");
                std::printf("%u", (columns[col] >> (r - row - 1)) & 1u);
            }
            std::printf("\n");
        }
    }
};

bool read_message(const char* path, unsigned char* data, unsigned& k) {
    FILE* file = std::fopen(path, "rb");
    if (!file) { std::fprintf(stderr, "Не удалось открыть файл сообщения: %s\n", path); return false; }
    unsigned char text[260];
    size_t length = std::fread(text, 1, sizeof(text), file);
    std::fclose(file);
    // Удаляем только UTF-8 BOM. Остальные байты, в том числе переводы строк,
    // являются частью сообщения и восстанавливаются без изменения.
    unsigned start = length >= 3 && text[0] == 239 && text[1] == 187 && text[2] == 191 ? 3 : 0;
    if (length - start < 2 || length - start > 256) {
        std::fprintf(stderr, "Сообщение должно содержать от 2 до 256 байтов (16..2048 бит).\n"); return false;
    }
    k = unsigned(length - start) * 8;
    std::printf("Файл сообщения: %s; байтов: %zu; k=%u бит.\n", path, length - start, k);
    std::printf("Байты сообщения (hex):");
    for (unsigned j = start; j < length; ++j) {
        std::printf(" %02X", text[j]);
        for (unsigned b = 0; b < 8; ++b) data[(j - start) * 8 + b] = (text[j] >> (7 - b)) & 1;
    }
    std::printf("\n");
    return true;
}

bool hamming_demo(const char* message) {
    unsigned char data[MAX_BITS], encoded[MAX_BITS], received[MAX_BITS], error[MAX_BITS];
    unsigned char corrected[MAX_BITS], estimated[MAX_BITS];
    unsigned k;
    if (!read_message(message, data, k)) return false;
    Random random;
    std::printf("\nЧАСТЬ 1. КОД ХЕММИНГА\n");
    for (bool extended : {false, true}) {
        Hamming code(k, extended);
        std::printf("\nd_min=%u; k=%u; r=%u; n=%u\n", extended ? 4 : 3, k, code.r, code.n);
        code.print_matrix();
        code.encode(data, encoded);
        print_bits("X_k", data, k);
        print_bits("X_r", encoded + k, code.r);
        print_bits("X_n", encoded, code.n);
        for (unsigned count = 0; count <= 2; ++count) {
            std::memcpy(received, encoded, code.n);
            inject(received, code.n, count, error, random);
            std::printf("\nВнесено ошибок: %u. Позиции (от 1):", count);
            for (unsigned j = 0; j < code.n; ++j) if (error[j]) std::printf(" %u", j + 1);
            std::printf("\n");
            print_bits("Y_n", received, code.n);
            print_bits("Y_k", received, k);
            print_bits("Y_r", received + k, code.r);
            // Повторно вычисленные проверки Y_r' по принятой информации.
            unsigned char recomputed[MAX_BITS];
            code.encode(received, recomputed);
            print_bits("Y_r'", recomputed + k, code.r);
            unsigned s = code.syndrome(received);
            std::printf("S=");
            for (unsigned j = 0; j < code.r; ++j) std::printf("%u", (s >> (code.r - j - 1)) & 1);
            std::printf("\n");
            unsigned status = code.decode(received, corrected, estimated);
            print_bits("E_n (найденный)", estimated, code.n);
            print_bits("Y_n'", corrected, code.n);
            print_bits("Y_k'", corrected, k);
            std::printf("Решение декодера: %s; совпадение с X_n: %s\n", status == 0 ? "ошибок не обнаружено" : status == 1 ? "одиночная ошибка исправлена" : "ошибка обнаружена, исправление невозможно", same(encoded, corrected, code.n) ? "да" : "нет");
        }
    }
    return true;
}

// Маска из 128 бит хранит строку проверок без динамических контейнеров.
struct Mask {
    U64 lo = 0, hi = 0;
    void set(unsigned bit) { if (bit < 64) lo |= U64(1) << bit; else hi |= U64(1) << (bit - 64); }
    bool bit(unsigned i) const { return i < 64 ? ((lo >> i) & 1) != 0 : ((hi >> (i - 64)) & 1) != 0; }
    Mask operator^(Mask other) const { return {lo ^ other.lo, hi ^ other.hi}; }
    Mask operator&(Mask other) const { return {lo & other.lo, hi & other.hi}; }
    unsigned count() const { return weight(lo) + weight(hi); }
};

struct Iterative {
    unsigned rows, cols, depth, groups, r = 0, n;
    Mask columns[128];
    explicit Iterative(unsigned a, unsigned b, unsigned z, unsigned g)
        : rows(a), cols(b), depth(z), groups(g) {
        // Группы H,V,D,A,Z -- порядок рис. 5.3 и 5.4.
        // В 2D диагонали обычные; в 3D -- циклические на плоскости.
        for (unsigned plane = 0; plane < depth; ++plane) {
            for (unsigned y = 0; y < rows; ++y) {
                for (unsigned x = 0; x < cols; ++x) columns[index(plane, y, x)].set(r);
                ++r;
            }
        }
        for (unsigned plane = 0; plane < depth; ++plane) {
            for (unsigned x = 0; x < cols; ++x) {
                for (unsigned y = 0; y < rows; ++y) columns[index(plane, y, x)].set(r);
                ++r;
            }
        }
        if (groups >= 3) diagonals(false);
        if (groups >= 4) diagonals(true);
        if (groups >= 5)
            for (unsigned y = 0; y < rows; ++y)
                for (unsigned x = 0; x < cols; ++x) {
                    for (unsigned plane = 0; plane < depth; ++plane) columns[index(plane, y, x)].set(r);
                    ++r;
                }
        // В двумерной схеме есть паритет паритетов X_hv (рис. 5.1).
        // Трёхмерная схема содержит только группы рис. 5.4, без
        // дополнительного проверочного разряда сверх этих групп.
        if (depth == 1) {
            for (unsigned i = 0; i < 20; ++i) columns[i].set(r);
            ++r;
        }
        n = 20 + r;
        for (unsigned j = 0; j < r; ++j) {
            columns[20 + j].set(j);
            if (depth == 1) columns[20 + j].set(r - 1);
        }
    }
    unsigned index(unsigned plane, unsigned y, unsigned x) const { return (plane * rows + y) * cols + x; }
    void diagonals(bool reverse) {
        unsigned count = depth == 1 ? rows + cols - 1 : cols;
        for (unsigned plane = 0; plane < depth; ++plane)
            for (unsigned d = 0; d < count; ++d) {
                for (unsigned y = 0; y < rows; ++y)
                    for (unsigned x = 0; x < cols; ++x) {
                        unsigned label = reverse ? x + y : x + rows - 1 - y;
                        if (depth > 1) label = reverse ? (x + y) % cols : (x + cols - y % cols) % cols;
                        if (label == d) columns[index(plane, y, x)].set(r);
                    }
                ++r;
            }
    }
    Mask syndrome(const unsigned char* word) const {
        Mask s;
        for (unsigned j = 0; j < n; ++j) {
            U64 mask = U64(0) - U64(word[j]);
            s.lo ^= columns[j].lo & mask;
            s.hi ^= columns[j].hi & mask;
        }
        return s;
    }
    void encode(const unsigned char* data, unsigned char* word) const {
        std::memcpy(word, data, 20);
        std::memset(word + 20, 0, r);
        Mask parity = syndrome(word);
        for (unsigned j = 0; j < r; ++j) word[20 + j] = parity.bit(j);
        if (depth == 1) {
            unsigned overall = 0;
            for (unsigned j = 0; j + 1 < n; ++j) overall ^= word[j];
            word[n - 1] = static_cast<unsigned char>(overall);
        }
    }
    // Поиск информационных битов, у которых нарушено большинство проверок.
    // После них исправляются проверки. Общая чётность контролирует решение.
    // -1 означает: ошибка обнаружена, надёжного решения нет.
    int decode(const unsigned char* received, unsigned char* corrected) const {
        unsigned char trial[128];
        std::memcpy(trial, received, n);
        Mask initial = syndrome(received), s = initial;
        if (s.count() == 0) { std::memcpy(corrected, received, n); return 0; }
        if (depth == 1 && s.count() == 1 && s.bit(r - 1)) {
            std::memcpy(corrected, received, n); corrected[n - 1] ^= 1; return 1;
        }
        unsigned changes = 0;
        for (unsigned step = 0; step < 20; ++step) {
            int best = -1;
            unsigned best_score = 0;
            for (unsigned i = 0; i < 20; ++i) {
                unsigned failed = (s & columns[i]).count();
                if (depth == 1) failed -= unsigned(s.bit(r - 1));
                if (2 * failed > groups && failed > best_score) { best = int(i); best_score = failed; }
            }
            if (best < 0) break;
            trial[best] ^= 1;
            s = s ^ columns[best];
        }
        // Оставшиеся синдромные единицы относятся к проверочным символам.
        unsigned checks = depth == 1 ? r - 1 : r;
        for (unsigned j = 0; j < checks; ++j) trial[20 + j] ^= static_cast<unsigned char>(s.bit(j));
        for (unsigned i = 0; i < 20 + checks; ++i) changes += trial[i] != received[i];
        bool consistent = depth > 1 || (changes & 1u) == unsigned(initial.bit(r - 1));
        std::memcpy(corrected, consistent ? trial : received, n);
        return consistent ? int(changes) : -1;
    }
    void print_layout(const unsigned char* data) const {
        for (unsigned plane = 0; plane < depth; ++plane) {
            std::printf("Плоскость %u:\n", plane + 1);
            for (unsigned y = 0; y < rows; ++y) {
                for (unsigned x = 0; x < cols; ++x) std::printf("%u ", data[index(plane, y, x)]);
                std::printf("\n");
            }
        }
    }
};

void iterative_experiment(const unsigned char* data, unsigned trials,
                          unsigned max_errors, const char* folder) {
    const unsigned configurations[4][3] = {{4,5,1}, {2,10,1}, {2,5,2}, {2,2,5}};
    FILE* csv = output_file(folder, "iterative.csv");
    if (csv) std::fprintf(csv, "rows,cols,depth,groups,k,r,n,errors,N1,detected,N2,N3,rate_N2,rate_N3\n");
    Random random;
    std::printf("\nЧАСТЬ 2. ИТЕРАТИВНЫЕ КОДЫ; вариант 2 таблицы 5.2; k=20.\n");
    print_bits("X_k", data, 20);
    std::printf("N1 -- испытания; N2 -- верно определена кратность; N3 -- полностью восстановлено X_n.\n");
    for (const auto& config : configurations) {
        unsigned highest = config[2] == 1 ? 3 : 5;
        for (unsigned groups = 2; groups <= highest; ++groups) {
            Iterative code(config[0], config[1], config[2], groups);
            unsigned char encoded[128], received[128], error[128], corrected[128];
            code.encode(data, encoded);
            std::printf("\n%ux%ux%u, групп=%u, r=%u, n=%u, R=k/n=%.6f\n", config[0], config[1], config[2], groups, code.r, code.n, 20.0 / code.n);
            code.print_layout(data);
            print_bits("X_r", encoded + 20, code.r);
            print_bits("X_n", encoded, code.n);
            // Один полный пример передачи с одиночной ошибкой.
            std::memcpy(received, encoded, code.n);
            inject(received, code.n, 1, error, random);
            print_bits("Y_n (пример)", received, code.n);
            code.decode(received, corrected);
            print_bits("Y_n' (пример)", corrected, code.n);
            std::printf("i   N1    обнаружено   N2    N3    N2/N1    N3/N1\n");
            for (unsigned count = 0; count <= max_errors; ++count) {
                unsigned detected = 0, multiplicity = 0, restored = 0;
                for (unsigned test = 0; test < trials; ++test) {
                    std::memcpy(received, encoded, code.n);
                    inject(received, code.n, count, error, random);
                    detected += code.syndrome(received).count() != 0;
                    int estimate = code.decode(received, corrected);
                    multiplicity += estimate == int(count);
                    restored += same(encoded, corrected, code.n);
                }
                std::printf("%u %5u %10u %6u %5u %8.4f %8.4f\n", count, trials, detected, multiplicity, restored, double(multiplicity) / trials, double(restored) / trials);
                if (csv) std::fprintf(csv, "%u,%u,%u,%u,20,%u,%u,%u,%u,%u,%u,%u,%.9f,%.9f\n", config[0], config[1], config[2], groups, code.r, code.n, count, trials, detected, multiplicity, restored, double(multiplicity)/trials, double(restored)/trials);
            }
        }
    }
    if (csv) std::fclose(csv);
}

bool self_test() {
    bool ok = true;
    unsigned cases = 0;
    unsigned char data[MAX_BITS] = {}, encoded[MAX_BITS], received[MAX_BITS];
    unsigned char corrected[MAX_BITS], error[MAX_BITS];
    Hamming example(4, false);
    const unsigned expected[7] = {3, 5, 6, 7, 4, 2, 1};
    for (unsigned j = 0; j < 7; ++j) ok &= example.columns[j] == expected[j];
    for (unsigned k : {4u, 16u, 24u, 64u, 2048u}) {
        for (unsigned j = 0; j < k; ++j) data[j] = (j * 7 + 1) % 2;
        for (bool ext : {false, true}) {
            Hamming code(k, ext);
            code.encode(data, encoded);
            ok &= code.syndrome(encoded) == 0;
            for (unsigned j = 0; j < code.n; ++j) {
                std::memcpy(received, encoded, code.n); received[j] ^= 1;
                ok &= code.decode(received, corrected, error) == 1 && same(encoded, corrected, code.n);
                ++cases;
            }
            if (ext && k <= 64)
                for (unsigned a = 0; a < code.n; ++a)
                    for (unsigned b = a + 1; b < code.n; ++b) {
                        std::memcpy(received, encoded, code.n); received[a] ^= 1; received[b] ^= 1;
                        ok &= code.decode(received, corrected, error) == 2 && same(received, corrected, code.n);
                        ++cases;
                    }
        }
    }
    const unsigned configs[4][3] = {{4,5,1}, {2,10,1}, {2,5,2}, {2,2,5}};
    for (const auto& c : configs)
        for (unsigned g = 2; g <= (c[2] == 1 ? 3u : 5u); ++g) {
            Iterative code(c[0], c[1], c[2], g);
            code.encode(data, encoded);
            ok &= code.n <= 128 && code.syndrome(encoded).count() == 0;
            for (unsigned j = 0; j < code.n; ++j) {
                std::memcpy(received, encoded, code.n); received[j] ^= 1;
                ok &= code.decode(received, corrected) == 1 && same(encoded, corrected, code.n);
                ++cases;
            }
        }
    std::printf("Самопроверка: %s; проверено искажений: %u\n", ok ? "OK" : "ОШИБКА", cases);
    return ok;
}

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8); SetConsoleCP(CP_UTF8);
#endif
    if (argc == 2 && std::strcmp(argv[1], "--self-test") == 0) return self_test() ? 0 : 1;
    const char* message = "message.txt";
    const char* folder = nullptr;
    unsigned trials = 1000, max_errors = 4;
    const char* bits = "11001010111010001101";
    if (argc == 4 && std::strcmp(argv[1], "--report") == 0) { folder = argv[2]; message = argv[3]; }
    else if (argc > 1) {
        if (argc > 5) { std::fprintf(stderr, "Использование: lab2.exe [файл [20бит [кратность [испытания]]]]\n"); return 2; }
        message = argv[1];
        if (argc >= 3) bits = argv[2];
        if (argc >= 4) max_errors = unsigned(std::strtoul(argv[3], nullptr, 10));
        if (argc >= 5) trials = unsigned(std::strtoul(argv[4], nullptr, 10));
    }
    unsigned char data[20];
    if (std::strlen(bits) != 20 || max_errors > 30 || trials < 1 || trials > 100000) {
        std::fprintf(stderr, "Нужны 20 бит; кратность 0..30; испытаний 1..100000.\n"); return 2;
    }
    for (unsigned i = 0; i < 20; ++i) {
        if (bits[i] != '0' && bits[i] != '1') { std::fprintf(stderr, "Слово содержит символы, отличные от 0 и 1.\n"); return 2; }
        data[i] = bits[i] - '0';
    }
    if (folder) {
        FILE* probe = output_file(folder, "iterative.csv");
        if (!probe) { std::fprintf(stderr, "Папка результатов недоступна.\n"); return 2; }
        std::fclose(probe);
    }
    std::printf("ЛАБОРАТОРНАЯ РАБОТА 2. ЦЕВАН К. А. ВАРИАНТ ПО СПИСКУ 12.\n");
    if (!hamming_demo(message)) return 2;
    iterative_experiment(data, trials, max_errors, folder);
    return 0;
}
