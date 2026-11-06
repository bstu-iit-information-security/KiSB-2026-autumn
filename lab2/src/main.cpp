#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif

#include "hamming.hpp"
#include "iterative.hpp"

// ---------------------------------------------------------------- ввод и вывод

int read_int(const char* prompt, int low, int high, int fallback) {
    while (true) {
        std::cout << prompt << " [" << low << ".." << high << ", Enter = " << fallback << "]: ";
        char line[64] = {};
        if (!std::cin.getline(line, sizeof line)) {
            if (std::cin.eof()) return fallback;
            std::cin.clear();
            std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
            continue;
        }
        if (line[0] == '\0' || line[0] == '\r') return fallback;
        char* end = nullptr;
        const long value = std::strtol(line, &end, 10);
        if (end != line && (*end == '\0' || *end == '\r') && value >= low && value <= high)
            return static_cast<int>(value);
        std::cout << "  Некорректный ввод.\n";
    }
}

void print_bits(std::ostream& out, const std::uint8_t* bits, int count, int group = 8) {
    for (int i = 0; i < count; ++i) {
        if (group > 0 && i > 0 && i % group == 0) out << ' ';
        out << static_cast<int>(bits[i]);
    }
}

void print_positions(std::ostream& out, const Bits& vector, int n) {
    bool first = true;
    for (int j = 0; j < n; ++j)
        if (vector[j]) {
            out << (first ? "" : ", ") << j;
            first = false;
        }
    if (first) out << "нет";
}

void print_matrix(std::ostream& out, const LinearCode& code) {
    for (int i = 0; i < code.r; ++i) {
        out << "  ";
        print_bits(out, code.H[i].data(), code.k);
        out << " | ";
        print_bits(out, code.H[i].data() + code.k, code.r, 0);
        out << '\n';
    }
}

// ---------------------------------------------------------------- часть 1: код Хемминга

constexpr int kMaxMessageBytes = 32;

struct Message {
    std::array<unsigned char, kMaxMessageBytes> bytes{};
    int length = 0;
};

// Файл читается побайтно (UTF-8): латиница, цифры и знаки — 1 байт, кириллица — 2 байта.
bool load_message(Message& message) {
    const char* paths[] = {"message.txt", "src/message.txt"};
    for (const char* path : paths) {
        std::ifstream in(path, std::ios::binary);
        if (!in) continue;
        char buffer[kMaxMessageBytes + 8] = {};
        in.read(buffer, sizeof buffer);
        int end = static_cast<int>(in.gcount());
        int start = 0;
        if (end >= 3 && static_cast<unsigned char>(buffer[0]) == 0xEF) start = 3;  // BOM
        while (end > start && (buffer[end - 1] == '\n' || buffer[end - 1] == '\r')) --end;
        message.length = end - start;
        if (message.length < 2 || message.length > kMaxMessageBytes) {
            std::cout << "Сообщение должно занимать от 2 до " << kMaxMessageBytes << " байт.\n";
            return false;
        }
        for (int i = 0; i < message.length; ++i) message.bytes[i] = buffer[start + i];
        return true;
    }
    std::cout << "Файл message.txt не найден.\n";
    return false;
}

Bits message_bits(const Message& message) {
    Bits bits{};
    for (int j = 0; j < message.length * 8; ++j)
        bits[j] = static_cast<std::uint8_t>((message.bytes[j / 8] >> (7 - j % 8)) & 1);
    return bits;
}

void print_text(std::ostream& out, const Bits& bits, int k) {
    out << '"';
    for (int byte = 0; byte < k / 8; ++byte) {
        unsigned value = 0;
        for (int b = 0; b < 8; ++b) value = (value << 1) | bits[byte * 8 + b];
        out << static_cast<char>(value);
    }
    out << '"';
}

// Вектора ошибок выбираются заранее, поэтому вывод в консоль и в файл одинаков.
void print_hamming(std::ostream& out, const Message& message, int d_min, const std::array<Bits, 3>& errors) {
    LinearCode code;
    build_hamming(code, message.length * 8, d_min);
    const int base_r = hamming_check_count(code.k);
    const Bits sent = code.encode(message_bits(message));

    out << "\n=========== КОД ХЕММИНГА, d_min = " << d_min << " ===========\n";
    out << "Сообщение: ";
    print_text(out, sent, code.k);
    out << " (" << message.length << " байт)\n";
    out << "k = " << code.k << ", r = " << code.r << ", n = " << code.n << "  (2^" << base_r << " >= k + "
        << base_r << " + 1)\n";
    out << "Столбцы P' по весу wt:";
    for (int w = 2, used = 0; used < code.k; ++w) {
        const int take = static_cast<int>(std::min<long long>(binomial(base_r, w), code.k - used));
        out << "  wt=" << w << ": C(" << base_r << "," << w << ")=" << binomial(base_r, w) << ", взято " << take;
        used += take;
    }
    out << "\nПроверочная матрица H (" << code.r << " x " << code.n << "):\n";
    print_matrix(out, code);
    out << "X_k  = ";
    print_bits(out, sent.data(), code.k);
    out << "\nX_r  = ";
    print_bits(out, sent.data() + code.k, code.r, 0);
    out << "\nX_n  = ";
    print_bits(out, sent.data(), code.n);
    out << '\n';

    for (int e = 0; e < 3; ++e) {
        const Bits received = xor_bits(sent, errors[e]);
        const Checks recomputed = code.check_bits(received);
        const Checks s = code.syndrome(received);
        const Decoded result = syndrome_decode(code, received);

        out << "\n--- Ошибок: " << e << ", позиции: ";
        print_positions(out, errors[e], code.n);
        out << " ---\nY_n  = ";
        print_bits(out, received.data(), code.n);
        out << "\nY_r  = ";
        print_bits(out, received.data() + code.k, code.r, 0);
        out << "\nY_r' = ";
        print_bits(out, recomputed.data(), code.r, 0);
        out << "\nS    = ";
        print_bits(out, s.data(), code.r, 0);
        out << '\n';

        if (result.status == Status::NoError) {
            out << "S = 0: ошибок не обнаружено.\n";
        } else if (result.status == Status::Corrected) {
            int position = 0;
            while (!result.error[position]) ++position;
            out << "S совпадает со столбцом " << position << " матрицы H: ошибка в бите " << position << ".\nE_n  = ";
            print_bits(out, result.error.data(), code.n);
            out << "\nY_n' = ";
            print_bits(out, result.corrected.data(), code.n);
            out << '\n';
        } else {
            out << "S не совпадает ни с одним столбцом H: обнаружена ошибка кратности >= 2, исправить нельзя.\n";
        }
        const bool restored = result.corrected == sent;
        out << "Совпадает с X_n: " << (restored ? "да" : "нет");
        if (!restored && result.status == Status::Corrected) out << " (ложное исправление)";
        out << "\nДекодированное сообщение: ";
        print_text(out, result.corrected, code.k);
        out << '\n';
    }
}

void hamming_menu(std::mt19937& rng) {
    Message message;
    if (!load_message(message)) return;
    const int mode = read_int("d_min: 1 — 3, 2 — 4, 3 — оба", 1, 3, 3);
    std::ofstream file("hamming_output.txt", std::ios::binary);

    for (int d = 3; d <= 4; ++d) {
        if ((mode == 1 && d == 4) || (mode == 2 && d == 3)) continue;
        const int n = message.length * 8 + hamming_check_count(message.length * 8) + (d == 4 ? 1 : 0);
        const std::array<Bits, 3> errors = {random_errors(n, 0, rng), random_errors(n, 1, rng),
                                            random_errors(n, 2, rng)};
        print_hamming(std::cout, message, d, errors);
        print_hamming(file, message, d, errors);
    }
    std::cout << "\nВывод сохранён в hamming_output.txt\n";
}

// ---------------------------------------------------------------- часть 2: итеративный код

void print_code_summary(const IterativeCode& ic) {
    const Layout& L = ic.layout;
    std::cout << "Матрица " << L.k1 << " x " << L.k2;
    if (L.z > 1) std::cout << " x " << L.z;
    std::cout << ", групп паритетов: " << L.groups << ", r = " << ic.code.r << ", n = " << ic.code.n
              << ", k/n = " << std::fixed << std::setprecision(3) << double(ic.code.k) / ic.code.n
              << std::defaultfloat << '\n';
}

void print_groups(const IterativeCode& ic, const std::uint8_t* bits) {
    for (int g = 0; g < ic.layout.groups; ++g) {
        std::cout << "  " << group_name(ic.layout.group(g)) << ": ";
        print_bits(std::cout, bits + ic.first[g], ic.size[g], 0);
        std::cout << '\n';
    }
}

void choose_layout(Layout& layout) {
    std::cout << "Конфигурации варианта (k = 24):\n";
    for (int i = 0; i < 4; ++i) {
        const VariantRow& v = kVariant[i];
        std::cout << "  " << i + 1 << ") " << v.k1 << " x " << v.k2;
        if (v.z > 1) std::cout << " x " << v.z;
        std::cout << ", групп:";
        for (int o = 0; o < v.option_count; ++o) std::cout << ' ' << v.group_options[o];
        std::cout << '\n';
    }
    const VariantRow& v = kVariant[read_int("Конфигурация", 1, 4, 1) - 1];
    const int low = v.group_options[0];
    const int high = v.group_options[v.option_count - 1];
    layout = Layout{v.k1, v.k2, v.z, read_int("Число групп паритетов", low, high, low)};
}

void iterative_demo(std::mt19937& rng) {
    Layout layout{};
    choose_layout(layout);
    IterativeCode ic;
    build_iterative(ic, layout);
    const LinearCode& code = ic.code;
    const int errors_count = read_int("Сколько ошибок внести", 0, code.n, 1);

    const Bits sent = code.encode(random_info(code.k, rng));
    const Bits injected = random_errors(code.n, errors_count, rng);
    const Bits received = xor_bits(sent, injected);
    const Checks s = code.syndrome(received);
    const Decoded result = bit_flip_decode(code, received);

    std::cout << "\n=========== ИТЕРАТИВНЫЙ КОД ===========\n";
    print_code_summary(ic);
    std::cout << "X_k в матрице:\n";
    for (int p = 0; p < layout.z; ++p) {
        if (layout.z > 1) std::cout << "  плоскость " << p << ":\n";
        for (int row = 0; row < layout.k1; ++row) {
            std::cout << "    ";
            for (int col = 0; col < layout.k2; ++col) std::cout << int(sent[layout.index(p, row, col)]) << ' ';
            std::cout << '\n';
        }
    }
    std::cout << "Проверочные символы:\n";
    print_groups(ic, sent.data() + code.k);
    std::cout << "X_n  = ";
    print_bits(std::cout, sent.data(), code.n);
    std::cout << "\nОшибки в позициях: ";
    print_positions(std::cout, injected, code.n);
    std::cout << "\nY_n  = ";
    print_bits(std::cout, received.data(), code.n);
    std::cout << "\nНарушенные проверки (синдром по группам):\n";
    print_groups(ic, s.data());

    if (result.status == Status::Uncorrectable)
        std::cout << "Ошибка обнаружена, но исправить её не удалось.\n";
    std::cout << "Найденные ошибки E_n: ";
    print_positions(std::cout, result.error, code.n);
    std::cout << "\nY_n' = ";
    print_bits(std::cout, result.corrected.data(), code.n);
    std::cout << "\nКратность: внесено " << errors_count << ", определено "
              << (result.status == Status::Uncorrectable ? 0 : result.error_weight)
              << "; Y_n' совпадает с X_n: " << (result.corrected == sent ? "да" : "нет") << '\n';
}

void statistics(std::mt19937& rng) {
    const int trials = 1000;
    std::cout << "\nN1 = " << trials << " слов на каждую кратность ошибки i\n";
    for (const VariantRow& v : kVariant)
        for (int o = 0; o < v.option_count; ++o) {
            IterativeCode ic;
            build_iterative(ic, Layout{v.k1, v.k2, v.z, v.group_options[o]});
            std::cout << '\n';
            print_code_summary(ic);
            std::cout << "  i |   N2 |   N3 | N2/N1 | N3/N1\n";
            for (int errors_count = 1; errors_count <= 4; ++errors_count) {
                int n2 = 0, n3 = 0;
                for (int t = 0; t < trials; ++t) {
                    const Bits sent = ic.code.encode(random_info(ic.code.k, rng));
                    const Bits received = xor_bits(sent, random_errors(ic.code.n, errors_count, rng));
                    const Decoded result = bit_flip_decode(ic.code, received);
                    if (result.status != Status::Uncorrectable && result.error_weight == errors_count) ++n2;
                    if (result.corrected == sent) ++n3;
                }
                std::cout << std::fixed << std::setprecision(3) << "  " << errors_count << " | " << std::setw(4) << n2
                          << " | " << std::setw(4) << n3 << " | " << double(n2) / trials << " | "
                          << double(n3) / trials << std::defaultfloat << '\n';
            }
        }
}

int main() {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif
    std::mt19937 rng(std::random_device{}());
    std::cout << "КиСБ, ЛР №2: код Хемминга и итеративные коды. Вариант 8\n";
    while (true) {
        std::cout << "\n1 — код Хемминга (сообщение из message.txt)\n"
                     "2 — итеративный код: одно слово\n"
                     "3 — итеративный код: статистика N2/N1, N3/N1\n"
                     "0 — выход\n";
        const int choice = read_int("Пункт", 0, 3, 0);
        if (choice == 0) break;
        if (choice == 1) hamming_menu(rng);
        if (choice == 2) iterative_demo(rng);
        if (choice == 3) statistics(rng);
    }
    return 0;
}
