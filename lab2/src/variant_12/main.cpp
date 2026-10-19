#ifdef _MSC_VER
#define _CRT_SECURE_NO_WARNINGS
#endif

#include <inttypes.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

namespace {

    constexpr unsigned int kMaxMessageBytes = 256U;
    constexpr unsigned int kMaxInfoBits = kMaxMessageBytes * 8U;
    constexpr unsigned int kMaxHammingRows = 16U;
    constexpr unsigned int kMaxCodeBits = kMaxInfoBits + kMaxHammingRows;
    constexpr unsigned int kMaxSplits = 8U;
    constexpr unsigned int kMaxInjectedErrors = 8U;
    constexpr unsigned int kTrials = 10000U;
    constexpr unsigned int kMaxStatisticsErrors = 4U;
    constexpr uint64_t kDefaultSeed = 12ULL;
    constexpr char kDefaultMessagePath[] = "message.txt";
    constexpr char kReportPath[] = "lab2_output.txt";
    // "КиСБ lab2!" in Windows-1251; used when message.txt is missing.
    constexpr char kDefaultMessage[] = "\xCA\xE8\xD1\xC1 lab2!";

    FILE* g_report = nullptr;

    void emit(const char* format, ...) {
        va_list args;
        va_start(args, format);
        if (g_report != nullptr) {
            va_list copy;
            va_copy(copy, args);
            vfprintf(g_report, format, copy);
            va_end(copy);
        }
        vprintf(format, args);
        va_end(args);
    }

    // ---------------------------------------------------------------- helpers

    struct SplitMix64 {
        uint64_t state;

        uint64_t next() {
            state += 0x9E3779B97F4A7C15ULL;
            uint64_t value = state;
            value = (value ^ (value >> 30U)) * 0xBF58476D1CE4E5B9ULL;
            value = (value ^ (value >> 27U)) * 0x94D049BB133111EBULL;
            return value ^ (value >> 31U);
        }

        unsigned int below(unsigned int bound) {
            return static_cast<unsigned int>(((next() >> 32U) * bound) >> 32U);
        }
    };

    unsigned int popcount64(uint64_t value) {
        value = value - ((value >> 1U) & 0x5555555555555555ULL);
        value = (value & 0x3333333333333333ULL) + ((value >> 2U) & 0x3333333333333333ULL);
        value = (value + (value >> 4U)) & 0x0F0F0F0F0F0F0F0FULL;
        return static_cast<unsigned int>((value * 0x0101010101010101ULL) >> 56U);
    }

    unsigned int parity64(uint64_t value) {
        value ^= value >> 32U;
        value ^= value >> 16U;
        value ^= value >> 8U;
        value ^= value >> 4U;
        value ^= value >> 2U;
        value ^= value >> 1U;
        return static_cast<unsigned int>(value & 1ULL);
    }

    // Distinct random positions in [0, n), sorted ascending.
    void pick_positions(SplitMix64& rng, unsigned int n, unsigned int count, unsigned int* positions) {
        for (unsigned int i = 0U; i < count; ++i) {
            bool repeated = true;
            while (repeated) {
                positions[i] = rng.below(n);
                repeated = false;
                for (unsigned int j = 0U; j < i; ++j) {
                    repeated = repeated || positions[j] == positions[i];
                }
            }
        }
        for (unsigned int i = 1U; i < count; ++i) {
            const unsigned int value = positions[i];
            unsigned int j = i;
            while (j > 0U && positions[j - 1U] > value) {
                positions[j] = positions[j - 1U];
                --j;
            }
            positions[j] = value;
        }
    }

    void emit_positions(const unsigned int* positions, unsigned int count) {
        if (count == 0U) {
            emit("none");
        }
        for (unsigned int i = 0U; i < count; ++i) {
            emit("%s%u", i == 0U ? "" : ", ", positions[i] + 1U);
        }
    }

    // Split points insert '|' between parts of a word (X_k | X_r ...).
    struct BitLayout {
        unsigned int splits[kMaxSplits];
        unsigned int count;
    };

    unsigned int separators_before(const BitLayout& layout, unsigned int index) {
        unsigned int result = 0U;
        for (unsigned int i = 0U; i < layout.count; ++i) {
            result += static_cast<unsigned int>(layout.splits[i] <= index);
        }
        return result;
    }

    void emit_bits(const char* label, const uint8_t* bits, unsigned int count, const BitLayout& layout) {
        static char line[kMaxCodeBits + kMaxSplits + 1U];
        unsigned int length = 0U;
        unsigned int split = 0U;
        for (unsigned int i = 0U; i < count; ++i) {
            while (split < layout.count && layout.splits[split] == i) {
                line[length++] = '|';
                ++split;
            }
            line[length++] = static_cast<char>('0' + bits[i]);
        }
        line[length] = '\0';
        emit("  %-6s %s\n", label, line);
    }

    void emit_marker(const unsigned int* positions, unsigned int count, unsigned int width,
        const BitLayout& layout) {
        static char line[kMaxCodeBits + kMaxSplits + 1U];
        if (count == 0U) {
            return;
        }
        const unsigned int length = width + layout.count;
        memset(line, ' ', length);
        for (unsigned int i = 0U; i < count; ++i) {
            line[positions[i] + separators_before(layout, positions[i])] = '^';
        }
        unsigned int end = length;
        while (end > 0U && line[end - 1U] == ' ') {
            --end;
        }
        line[end] = '\0';
        emit("  %-6s %s\n", "", line);
    }

    // ---------------------------------------------------------------- message

    struct Message {
        uint8_t bytes[kMaxMessageBytes];
        unsigned int length;
    };

    uint8_t unicode_to_cp1251(uint32_t code_point) {
        if (code_point < 0x80U) {
            return static_cast<uint8_t>(code_point);
        }
        if (code_point >= 0x410U && code_point <= 0x44FU) {
            return static_cast<uint8_t>(code_point - 0x410U + 0xC0U);
        }
        if (code_point == 0x401U) {
            return 0xA8U;
        }
        if (code_point == 0x451U) {
            return 0xB8U;
        }
        if (code_point == 0x2116U) {
            return 0xB9U;
        }
        return static_cast<uint8_t>('?');
    }

    // UTF-8 text -> Windows-1251, so every Russian or English symbol is 8 bits.
    bool utf8_to_message(const uint8_t* text, unsigned int length, Message& message) {
        message.length = 0U;
        unsigned int i = 0U;
        if (length >= 3U && text[0] == 0xEFU && text[1] == 0xBBU && text[2] == 0xBFU) {
            i = 3U;
        }
        while (length > i && (text[length - 1U] == '\n' || text[length - 1U] == '\r')) {
            --length;
        }
        while (i < length) {
            const uint8_t lead = text[i];
            uint32_t code_point = lead;
            unsigned int extra = 0U;
            if (lead >= 0xF0U) {
                code_point = lead & 0x07U;
                extra = 3U;
            }
            else if (lead >= 0xE0U) {
                code_point = lead & 0x0FU;
                extra = 2U;
            }
            else if (lead >= 0xC0U) {
                code_point = lead & 0x1FU;
                extra = 1U;
            }
            else if (lead >= 0x80U) {
                code_point = '?';
            }
            ++i;
            for (unsigned int j = 0U; j < extra && i < length; ++j, ++i) {
                code_point = (code_point << 6U) | (text[i] & 0x3FU);
            }
            if (message.length == kMaxMessageBytes) {
                return false;
            }
            message.bytes[message.length++] = unicode_to_cp1251(code_point);
        }
        return true;
    }

    void emit_cp1251(const uint8_t* bytes, unsigned int length) {
        for (unsigned int i = 0U; i < length; ++i) {
            const uint8_t value = bytes[i];
            uint32_t code_point = value;
            if (value >= 0xC0U) {
                code_point = 0x410U + (value - 0xC0U);
            }
            else if (value == 0xA8U) {
                code_point = 0x401U;
            }
            else if (value == 0xB8U) {
                code_point = 0x451U;
            }
            else if (value == 0xB9U) {
                code_point = 0x2116U;
            }
            else if (value >= 0x80U || value < 0x20U) {
                code_point = '?';
            }
            char utf8[4] = { 0, 0, 0, 0 };
            if (code_point < 0x80U) {
                utf8[0] = static_cast<char>(code_point);
            }
            else if (code_point < 0x800U) {
                utf8[0] = static_cast<char>(0xC0U | (code_point >> 6U));
                utf8[1] = static_cast<char>(0x80U | (code_point & 0x3FU));
            }
            else {
                utf8[0] = static_cast<char>(0xE0U | (code_point >> 12U));
                utf8[1] = static_cast<char>(0x80U | ((code_point >> 6U) & 0x3FU));
                utf8[2] = static_cast<char>(0x80U | (code_point & 0x3FU));
            }
            emit("%s", utf8);
        }
    }

    bool load_message(const char* path, Message& message, bool& from_file) {
        static uint8_t buffer[kMaxMessageBytes * 4U + 4U];
        FILE* file = fopen(path, "rb");
        from_file = file != nullptr;
        if (file == nullptr) {
            const unsigned int length = static_cast<unsigned int>(sizeof(kDefaultMessage) - 1U);
            memcpy(message.bytes, kDefaultMessage, length);
            message.length = length;
            return true;
        }
        const size_t length = fread(buffer, 1U, sizeof(buffer), file);
        const bool fits = feof(file) != 0;
        fclose(file);
        return fits && utf8_to_message(buffer, static_cast<unsigned int>(length), message);
    }

    void message_to_bits(const Message& message, uint8_t* bits) {
        for (unsigned int i = 0U; i < message.length * 8U; ++i) {
            bits[i] = static_cast<uint8_t>((message.bytes[i / 8U] >> (7U - i % 8U)) & 1U);
        }
    }

    void bits_to_message(const uint8_t* bits, unsigned int length, Message& message) {
        message.length = length;
        for (unsigned int i = 0U; i < length; ++i) {
            uint8_t value = 0U;
            for (unsigned int j = 0U; j < 8U; ++j) {
                value = static_cast<uint8_t>((value << 1U) | bits[i * 8U + j]);
            }
            message.bytes[i] = value;
        }
    }

    // ---------------------------------------------------------- Hamming code

    struct HammingCode {
        unsigned int k;
        unsigned int r;       // rows of H, including the overall parity row for d_min = 4
        unsigned int n;
        unsigned int d_min;
        uint16_t column[kMaxCodeBits];  // bit (r - 1 - row) holds H[row][column]
    };

    unsigned int hamming_check_bits(unsigned int k) {
        unsigned int r = 1U;
        while ((1UL << r) < static_cast<unsigned long>(k) + r + 1UL) {
            ++r;
        }
        return r;
    }

    unsigned long binomial(unsigned int n, unsigned int m) {
        unsigned long value = 1UL;
        for (unsigned int i = 1U; i <= m; ++i) {
            value = value * (n - m + i) / i;
        }
        return value;
    }

    // H = [P' | I]: columns of P' are r-bit numbers of weight 2, 3, ... taken in
    // ascending order (listing 4.2). For d_min = 4 the row of ones from (4.8) is
    // replaced by the sum of all rows, which keeps H in canonical form.
    void build_hamming(HammingCode& code, unsigned int k, unsigned int d_min) {
        const unsigned int r = hamming_check_bits(k);
        unsigned int filled = 0U;
        for (unsigned int weight = 2U; weight <= r && filled < k; ++weight) {
            for (unsigned int value = 3U; value < (1U << r) && filled < k; ++value) {
                if (popcount64(value) == weight) {
                    code.column[filled++] = static_cast<uint16_t>(value);
                }
            }
        }
        for (unsigned int row = 0U; row < r; ++row) {
            code.column[k + row] = static_cast<uint16_t>(1U << (r - 1U - row));
        }
        code.k = k;
        code.r = r;
        code.n = k + r;
        code.d_min = 3U;
        if (d_min == 4U) {
            for (unsigned int j = 0U; j < code.n; ++j) {
                const unsigned int value = code.column[j];
                code.column[j] = static_cast<uint16_t>((value << 1U) | (parity64(value) ^ 1U));
            }
            code.column[code.n] = 1U;
            code.r = r + 1U;
            code.n = k + r + 1U;
            code.d_min = 4U;
        }
    }

    uint16_t hamming_checks(const HammingCode& code, const uint8_t* info) {
        uint16_t checks = 0U;
        for (unsigned int j = 0U; j < code.k; ++j) {
            checks ^= static_cast<uint16_t>(code.column[j] & (0U - static_cast<unsigned int>(info[j])));
        }
        return checks;
    }

    void hamming_encode(const HammingCode& code, const uint8_t* info, uint8_t* word) {
        const uint16_t checks = hamming_checks(code, info);
        for (unsigned int j = 0U; j < code.k; ++j) {
            word[j] = info[j];
        }
        for (unsigned int row = 0U; row < code.r; ++row) {
            word[code.k + row] = static_cast<uint8_t>((checks >> (code.r - 1U - row)) & 1U);
        }
    }

    enum class DecodeStatus { kNoError, kCorrected, kDetected };

    struct HammingDecoding {
        uint16_t received_checks;    // Y_r
        uint16_t recomputed_checks;  // Y_r'
        uint16_t syndrome;           // S = Y_r + Y_r'
        unsigned int position;
        DecodeStatus status;
    };

    // Corrects the word in place; the column search and the bit flip have no
    // data-dependent branches.
    HammingDecoding hamming_decode(const HammingCode& code, uint8_t* word) {
        HammingDecoding result{ 0U, 0U, 0U, 0U, DecodeStatus::kNoError };
        for (unsigned int row = 0U; row < code.r; ++row) {
            result.received_checks = static_cast<uint16_t>((result.received_checks << 1U) | word[code.k + row]);
        }
        result.recomputed_checks = hamming_checks(code, word);
        result.syndrome = static_cast<uint16_t>(result.received_checks ^ result.recomputed_checks);

        unsigned int found = 0U;
        unsigned int position = 0U;
        for (unsigned int j = 0U; j < code.n; ++j) {
            const unsigned int match = static_cast<unsigned int>(code.column[j] == result.syndrome);
            position |= j & (0U - match);
            found |= match;
        }
        for (unsigned int j = 0U; j < code.n; ++j) {
            word[j] ^= static_cast<uint8_t>(found & static_cast<unsigned int>(j == position));
        }
        result.position = position;
        if (result.syndrome == 0U) {
            result.status = DecodeStatus::kNoError;
        }
        else if (found != 0U) {
            result.status = DecodeStatus::kCorrected;
        }
        else {
            result.status = DecodeStatus::kDetected;
        }
        return result;
    }

    void u16_to_bits(uint16_t value, unsigned int width, uint8_t* bits) {
        for (unsigned int i = 0U; i < width; ++i) {
            bits[i] = static_cast<uint8_t>((value >> (width - 1U - i)) & 1U);
        }
    }

    void emit_hamming_matrix(const HammingCode& code) {
        static uint8_t row_bits[kMaxCodeBits];
        const BitLayout layout{ { code.k }, 1U };
        for (unsigned int row = 0U; row < code.r; ++row) {
            for (unsigned int j = 0U; j < code.n; ++j) {
                row_bits[j] = static_cast<uint8_t>((code.column[j] >> (code.r - 1U - row)) & 1U);
            }
            emit_bits(row == 0U ? "H =" : "", row_bits, code.n, layout);
        }
    }

    void emit_hamming_parameters(const HammingCode& code) {
        const unsigned int base_r = code.d_min == 4U ? code.r - 1U : code.r;
        const unsigned int detected = code.d_min % 2U == 0U ? code.d_min / 2U : (code.d_min - 1U) / 2U;
        const unsigned int corrected = code.d_min % 2U == 0U ? (code.d_min - 2U) / 2U : (code.d_min - 1U) / 2U;
        emit("k = %u, r = %u, n = %u, code rate k/n = %.4f\n", code.k, code.r, code.n,
            static_cast<double>(code.k) / static_cast<double>(code.n));
        emit("2^%u = %lu >= k + r + 1 = %u; t_o = %u, t_i = %u (section 4.1.1)\n", base_r,
            1UL << base_r, code.k + base_r + 1U, detected, corrected);
        emit("P' columns:");
        unsigned int remaining = code.k;
        for (unsigned int weight = 2U; weight <= base_r && remaining > 0U; ++weight) {
            const unsigned long available = binomial(base_r, weight);
            const unsigned int used = available < remaining ? static_cast<unsigned int>(available) : remaining;
            emit(" C(%u,%u) = %lu -> %u used;", base_r, weight, available, used);
            remaining -= used;
        }
        emit("\n");
        if (code.d_min == 4U) {
            emit("Overall parity row (4.8) replaced by the sum of all rows (canonical form).\n");
        }
    }

    void run_hamming_demo(const HammingCode& code, const uint8_t* info, SplitMix64& rng) {
        static uint8_t sent[kMaxCodeBits];
        static uint8_t received[kMaxCodeBits];
        static uint8_t corrected[kMaxCodeBits];
        static uint8_t error_vector[kMaxCodeBits];
        uint8_t check_bits[kMaxHammingRows];
        const BitLayout split{ { code.k }, 1U };
        const BitLayout plain{ { 0U }, 0U };

        emit_hamming_parameters(code);
        emit_hamming_matrix(code);
        hamming_encode(code, info, sent);
        emit_bits("X_k =", sent, code.k, plain);
        emit_bits("X_r =", sent + code.k, code.r, plain);
        emit_bits("X_n =", sent, code.n, split);

        for (unsigned int errors = 0U; errors <= 2U; ++errors) {
            unsigned int positions[kMaxInjectedErrors];
            pick_positions(rng, code.n, errors, positions);
            memcpy(received, sent, code.n);
            for (unsigned int i = 0U; i < errors; ++i) {
                received[positions[i]] ^= 1U;
            }
            emit("\n-- %u error(s), random positions: ", errors);
            emit_positions(positions, errors);
            emit("\n");
            emit_bits("Y_n =", received, code.n, split);
            emit_marker(positions, errors, code.n, split);

            memcpy(corrected, received, code.n);
            const HammingDecoding decoding = hamming_decode(code, corrected);
            emit_bits("Y_k =", received, code.k, plain);
            u16_to_bits(decoding.received_checks, code.r, check_bits);
            emit_bits("Y_r =", check_bits, code.r, plain);
            u16_to_bits(decoding.recomputed_checks, code.r, check_bits);
            emit_bits("Y_r'=", check_bits, code.r, plain);
            u16_to_bits(decoding.syndrome, code.r, check_bits);
            emit_bits("S   =", check_bits, code.r, plain);

            if (decoding.status == DecodeStatus::kDetected) {
                emit("  E_n =  not formed: the syndrome points to no single bit\n");
            }
            else {
                for (unsigned int j = 0U; j < code.n; ++j) {
                    error_vector[j] = static_cast<uint8_t>(corrected[j] ^ received[j]);
                }
                emit_bits("E_n =", error_vector, code.n, split);
                emit_bits("Y+E =", corrected, code.n, split);
            }

            const bool restored = memcmp(corrected, sent, code.n) == 0;
            if (decoding.status == DecodeStatus::kNoError) {
                emit("analysis: S = 0, Y_n is a code word; no error detected.\n");
            }
            else if (decoding.status == DecodeStatus::kCorrected) {
                emit("analysis: S equals column %u of H -> single error in bit %u, corrected.\n",
                    decoding.position + 1U, decoding.position + 1U);
            }
            else if (code.d_min == 4U && parity64(decoding.syndrome) == 0U) {
                emit("analysis: S != 0 and weight(S) is even -> double error detected, cannot be corrected.\n");
            }
            else {
                emit("analysis: S != 0 matches no column of H -> multiple error detected, cannot be corrected.\n");
            }
            if (decoding.status != DecodeStatus::kDetected) {
                emit("Y_n + E_n %s X_n", restored ? "==" : "!=");
                if (!restored) {
                    emit("  (miscorrection: %u errors exceed t_i = 1)", errors);
                }
                emit("\n");
            }
            Message decoded;
            bits_to_message(corrected, code.k / 8U, decoded);
            emit("%s message: \"", decoding.status == DecodeStatus::kDetected ? "received" : "decoded");
            emit_cp1251(decoded.bytes, decoded.length);
            emit("\"\n");
        }
    }

    void run_hamming_statistics(const HammingCode& code, SplitMix64& rng) {
        static uint8_t info[kMaxInfoBits];
        static uint8_t sent[kMaxCodeBits];
        static uint8_t word[kMaxCodeBits];
        emit("\nStatistics, %u random words per row (d_min = %u)\n", kTrials, code.d_min);
        emit("errors  detected  corrected  miscorrected  rejected\n");
        for (unsigned int errors = 0U; errors <= 3U; ++errors) {
            unsigned int detected = 0U;
            unsigned int restored = 0U;
            unsigned int miscorrected = 0U;
            unsigned int rejected = 0U;
            for (unsigned int trial = 0U; trial < kTrials; ++trial) {
                for (unsigned int j = 0U; j < code.k; ++j) {
                    info[j] = static_cast<uint8_t>(rng.next() & 1ULL);
                }
                hamming_encode(code, info, sent);
                memcpy(word, sent, code.n);
                unsigned int positions[kMaxInjectedErrors];
                pick_positions(rng, code.n, errors, positions);
                for (unsigned int i = 0U; i < errors; ++i) {
                    word[positions[i]] ^= 1U;
                }
                const HammingDecoding decoding = hamming_decode(code, word);
                const bool ok = memcmp(word, sent, code.n) == 0;
                detected += static_cast<unsigned int>(decoding.syndrome != 0U);
                restored += static_cast<unsigned int>(ok);
                miscorrected += static_cast<unsigned int>(decoding.status == DecodeStatus::kCorrected && !ok);
                rejected += static_cast<unsigned int>(decoding.status == DecodeStatus::kDetected);
            }
            emit("%6u  %8u  %9u  %12u  %8u\n", errors, detected, restored, miscorrected, rejected);
        }
    }

    bool hamming_self_check() {
        // H(7,4) from the textbook: rows 0111100, 1011010, 1101001.
        constexpr uint16_t expected[] = { 3U, 5U, 6U, 7U, 4U, 2U, 1U };
        HammingCode code;
        build_hamming(code, 4U, 3U);
        bool ok = code.n == 7U;
        for (unsigned int j = 0U; j < 7U; ++j) {
            ok = ok && code.column[j] == expected[j];
        }
        return ok;
    }

    // -------------------------------------------------------- iterative code

    constexpr unsigned int kMaxIterativeBits = 64U;
    constexpr unsigned int kMaxIterativeChecks = 64U;
    constexpr unsigned int kVariantInfoBits = 20U;
    constexpr unsigned int kDemoErrors = 3U;

    enum ParityGroup : unsigned int { kRows, kColumns, kDiagonals, kAntiDiagonals, kPlanes, kGroupCount };
    constexpr const char* kGroupNames[] = { "H", "V", "D", "A", "Z" };

    // Table 5.2, variant 2 (k = 20): k1 rows, k2 columns, z planes, parity groups.
    struct VariantRow {
        unsigned int k1;
        unsigned int k2;
        unsigned int z;
        unsigned int max_groups;
    };

    constexpr VariantRow kVariantRows[] = {
        {4U, 5U, 1U, 3U},
        {2U, 10U, 1U, 3U},
        {2U, 5U, 2U, 5U},
        {2U, 2U, 5U, 5U},
    };

    struct IterativeCode {
        unsigned int k1;
        unsigned int k2;
        unsigned int z;
        unsigned int groups;
        bool with_total;      // X_hv: parity of the whole word
        unsigned int span;    // checks per plane in groups D and A
        unsigned int k;
        unsigned int checks;  // without X_hv
        unsigned int r;
        unsigned int n;
        unsigned int group_begin[kGroupCount + 1U];
        uint64_t check_mask[kMaxIterativeChecks];  // info bits of each check
        uint64_t cover[kMaxIterativeBits];         // checks containing each info bit
    };

    struct IterativeWord {
        uint64_t info;
        uint64_t checks;
        unsigned int total;
    };

    unsigned int info_index(const IterativeCode& code, unsigned int plane, unsigned int row, unsigned int col) {
        return (plane * code.k1 + row) * code.k2 + col;
    }

    // 2D codes use plain diagonals (k1 + k2 - 1 checks, fig. 5.3); 3D codes use
    // combined (cyclic) diagonals, max(k1, k2) checks per plane (fig. 5.4).
    unsigned int line_index(const IterativeCode& code, unsigned int group, unsigned int plane,
        unsigned int row, unsigned int col) {
        const bool cyclic = code.z > 1U;
        switch (group) {
        case kRows:
            return plane * code.k1 + row;
        case kColumns:
            return plane * code.k2 + col;
        case kDiagonals:
            return plane * code.span +
                (cyclic ? (col + code.span - row) % code.span : col + code.k1 - 1U - row);
        case kAntiDiagonals:
            return plane * code.span + (cyclic ? (row + col) % code.span : row + col);
        default:
            return row * code.k2 + col;
        }
    }

    bool build_iterative(IterativeCode& code, const VariantRow& variant, unsigned int groups, bool with_total) {
        code.k1 = variant.k1;
        code.k2 = variant.k2;
        code.z = variant.z;
        code.groups = groups;
        code.with_total = with_total;
        code.k = code.k1 * code.k2 * code.z;
        code.span = code.z > 1U ? (code.k1 > code.k2 ? code.k1 : code.k2) : code.k1 + code.k2 - 1U;
        if (code.k > kMaxIterativeBits || groups < 2U || groups > kGroupCount ||
            (code.z == 1U && groups > 3U)) {
            return false;
        }
        const unsigned int lines[kGroupCount] = {
            code.z * code.k1, code.z * code.k2, code.z * code.span, code.z * code.span, code.k1 * code.k2
        };
        code.checks = 0U;
        for (unsigned int group = 0U; group < groups; ++group) {
            code.group_begin[group] = code.checks;
            code.checks += lines[group];
        }
        for (unsigned int group = groups; group <= kGroupCount; ++group) {
            code.group_begin[group] = code.checks;
        }
        if (code.checks > kMaxIterativeChecks) {
            return false;
        }
        code.r = code.checks + static_cast<unsigned int>(with_total);
        code.n = code.k + code.r;
        memset(code.check_mask, 0, sizeof(code.check_mask));
        memset(code.cover, 0, sizeof(code.cover));
        for (unsigned int plane = 0U; plane < code.z; ++plane) {
            for (unsigned int row = 0U; row < code.k1; ++row) {
                for (unsigned int col = 0U; col < code.k2; ++col) {
                    const unsigned int bit = info_index(code, plane, row, col);
                    for (unsigned int group = 0U; group < groups; ++group) {
                        const unsigned int check = code.group_begin[group] + line_index(code, group, plane, row, col);
                        code.check_mask[check] |= 1ULL << bit;
                        code.cover[bit] |= 1ULL << check;
                    }
                }
            }
        }
        return true;
    }

    uint64_t iterative_checks(const IterativeCode& code, uint64_t info) {
        uint64_t checks = 0ULL;
        for (unsigned int check = 0U; check < code.checks; ++check) {
            checks |= static_cast<uint64_t>(parity64(info & code.check_mask[check])) << check;
        }
        return checks;
    }

    IterativeWord iterative_encode(const IterativeCode& code, uint64_t info) {
        IterativeWord word{ info, iterative_checks(code, info), 0U };
        if (code.with_total) {
            word.total = parity64(info) ^ parity64(word.checks);
        }
        return word;
    }

    void flip_position(const IterativeCode& code, IterativeWord& word, unsigned int position) {
        if (position < code.k) {
            word.info ^= 1ULL << position;
        }
        else if (position < code.k + code.checks) {
            word.checks ^= 1ULL << (position - code.k);
        }
        else {
            word.total ^= 1U;
        }
    }

    struct IterativeDecoding {
        IterativeWord word;      // Y_n'
        uint64_t syndrome;       // failed checks of Y_n
        unsigned int total_syndrome;
        uint64_t flipped_info;
        uint64_t flipped_checks;
        unsigned int flipped_total;
        unsigned int corrections;
        bool rejected;
    };

    // Iterative bit flipping: an information bit is flipped while more than half
    // of its parity groups fail; failed checks that remain point to errors in
    // the check bits themselves. X_hv confirms the parity of the estimated
    // error multiplicity.
    IterativeDecoding iterative_decode(const IterativeCode& code, const IterativeWord& received) {
        IterativeDecoding result{ received, 0ULL, 0U, 0ULL, 0ULL, 0U, 0U, false };
        uint64_t syndrome = received.checks ^ iterative_checks(code, received.info);
        result.syndrome = syndrome;
        if (code.with_total) {
            result.total_syndrome = parity64(received.info) ^ parity64(received.checks) ^ received.total;
        }
        for (unsigned int step = 0U; step < code.k; ++step) {
            unsigned int best_votes = 0U;
            unsigned int best_bit = 0U;
            for (unsigned int bit = 0U; bit < code.k; ++bit) {
                const unsigned int votes = popcount64(syndrome & code.cover[bit]);
                if (votes > best_votes) {
                    best_votes = votes;
                    best_bit = bit;
                }
            }
            if (2U * best_votes <= code.groups) {
                break;
            }
            result.word.info ^= 1ULL << best_bit;
            result.flipped_info ^= 1ULL << best_bit;
            syndrome ^= code.cover[best_bit];
        }
        result.flipped_checks = syndrome;
        result.word.checks ^= syndrome;
        result.corrections = popcount64(result.flipped_info) + popcount64(result.flipped_checks);
        if (code.with_total && result.total_syndrome != (result.corrections & 1U)) {
            if (result.corrections == 0U) {
                result.word.total ^= 1U;
                result.flipped_total = 1U;
                result.corrections = 1U;
            }
            else {
                result.rejected = true;
            }
        }
        return result;
    }

    bool same_word(const IterativeWord& left, const IterativeWord& right) {
        return left.info == right.info && left.checks == right.checks && left.total == right.total;
    }

    // Splits of X_n (info | H | V | ... | X_hv) or, without info bits, of X_r.
    BitLayout iterative_layout(const IterativeCode& code, bool whole_word) {
        BitLayout layout{ {}, 0U };
        const unsigned int offset = whole_word ? code.k : 0U;
        if (whole_word) {
            layout.splits[layout.count++] = code.k;
        }
        for (unsigned int group = 1U; group < code.groups; ++group) {
            layout.splits[layout.count++] = offset + code.group_begin[group];
        }
        if (code.with_total) {
            layout.splits[layout.count++] = offset + code.checks;
        }
        return layout;
    }

    unsigned int word_to_bits(const IterativeCode& code, const IterativeWord& word, uint8_t* bits) {
        for (unsigned int i = 0U; i < code.k; ++i) {
            bits[i] = static_cast<uint8_t>((word.info >> i) & 1ULL);
        }
        for (unsigned int i = 0U; i < code.checks; ++i) {
            bits[code.k + i] = static_cast<uint8_t>((word.checks >> i) & 1ULL);
        }
        if (code.with_total) {
            bits[code.n - 1U] = static_cast<uint8_t>(word.total);
        }
        return code.n;
    }

    unsigned int check_bit(const IterativeCode& code, uint64_t checks, unsigned int group, unsigned int index) {
        return static_cast<unsigned int>((checks >> (code.group_begin[group] + index)) & 1ULL);
    }

    void iterative_name(const IterativeCode& code, char* name, size_t size) {
        if (code.z > 1U) {
            snprintf(name, size, "%ux%ux%u", code.k1, code.k2, code.z);
        }
        else {
            snprintf(name, size, "%ux%u", code.k1, code.k2);
        }
    }

    // Picture in the style of fig. 5.1 / 5.4: information bits, row parities on
    // the right, column parities below, diagonal and plane parities separately.
    void emit_iterative_table(const IterativeCode& code, const IterativeWord& word) {
        for (unsigned int plane = 0U; plane < code.z; ++plane) {
            if (code.z > 1U) {
                emit("  plane %u\n", plane + 1U);
            }
            for (unsigned int row = 0U; row < code.k1; ++row) {
                emit("    ");
                for (unsigned int col = 0U; col < code.k2; ++col) {
                    emit("%u ", static_cast<unsigned int>((word.info >> info_index(code, plane, row, col)) & 1ULL));
                }
                emit("| %u\n", check_bit(code, word.checks, kRows, plane * code.k1 + row));
            }
            emit("    ");
            for (unsigned int col = 0U; col < code.k2; ++col) {
                emit("--");
            }
            emit("+\n    ");
            for (unsigned int col = 0U; col < code.k2; ++col) {
                emit("%u ", check_bit(code, word.checks, kColumns, plane * code.k2 + col));
            }
            emit("  <- V\n");
            for (unsigned int group = kDiagonals; group < code.groups && group <= kAntiDiagonals; ++group) {
                emit("    %s:", kGroupNames[group]);
                for (unsigned int line = 0U; line < code.span; ++line) {
                    emit(" %u", check_bit(code, word.checks, group, plane * code.span + line));
                }
                emit("\n");
            }
        }
        if (code.groups > kPlanes) {
            emit("  Z (parity across planes):\n");
            for (unsigned int row = 0U; row < code.k1; ++row) {
                emit("    ");
                for (unsigned int col = 0U; col < code.k2; ++col) {
                    emit("%u ", check_bit(code, word.checks, kPlanes, row * code.k2 + col));
                }
                emit("\n");
            }
        }
        if (code.with_total) {
            emit("  X_hv = %u\n", word.total);
        }
    }

    void run_iterative_demo(const IterativeCode& code, uint64_t info, SplitMix64& rng) {
        static uint8_t bits[kMaxIterativeBits + kMaxIterativeChecks + 1U];
        const BitLayout word_layout = iterative_layout(code, true);
        const BitLayout check_layout = iterative_layout(code, false);
        const BitLayout plain{ { 0U }, 0U };

        char name[16];
        iterative_name(code, name, sizeof(name));
        emit("\n=== %s (k1 = %u, k2 = %u, z = %u), groups:", name, code.k1, code.k2, code.z);
        for (unsigned int group = 0U; group < code.groups; ++group) {
            emit(" %s", kGroupNames[group]);
        }
        emit("%s ===\n", code.with_total ? " + X_hv" : "");
        emit("k = %u, r = %u, n = %u, rate k/n = %.4f\n", code.k, code.r, code.n,
            static_cast<double>(code.k) / static_cast<double>(code.n));

        const IterativeWord sent = iterative_encode(code, info);
        emit_iterative_table(code, sent);
        word_to_bits(code, sent, bits);
        emit_bits("X_k =", bits, code.k, plain);
        emit_bits("X_r =", bits + code.k, code.r, check_layout);
        emit_bits("X_n =", bits, code.n, word_layout);

        for (unsigned int errors = 1U; errors <= kDemoErrors; ++errors) {
            unsigned int positions[kMaxInjectedErrors];
            pick_positions(rng, code.n, errors, positions);
            IterativeWord received = sent;
            for (unsigned int i = 0U; i < errors; ++i) {
                flip_position(code, received, positions[i]);
            }
            const IterativeDecoding decoding = iterative_decode(code, received);

            emit("-- %u error(s) at ", errors);
            emit_positions(positions, errors);
            emit("\n");
            word_to_bits(code, received, bits);
            emit_bits("Y_n =", bits, code.n, word_layout);
            emit_marker(positions, errors, code.n, word_layout);
            IterativeWord syndrome_word{ 0ULL, decoding.syndrome, decoding.total_syndrome };
            word_to_bits(code, syndrome_word, bits);
            emit_bits("S   =", bits + code.k, code.r, check_layout);

            unsigned int found[kMaxIterativeBits + kMaxIterativeChecks + 1U];
            unsigned int found_count = 0U;
            for (unsigned int i = 0U; i < code.k; ++i) {
                if (((decoding.flipped_info >> i) & 1ULL) != 0ULL) {
                    found[found_count++] = i;
                }
            }
            for (unsigned int i = 0U; i < code.checks; ++i) {
                if (((decoding.flipped_checks >> i) & 1ULL) != 0ULL) {
                    found[found_count++] = code.k + i;
                }
            }
            if (decoding.flipped_total != 0U) {
                found[found_count++] = code.n - 1U;
            }
            word_to_bits(code, decoding.word, bits);
            emit_bits("Y_n'=", bits, code.n, word_layout);
            emit_marker(found, found_count, code.n, word_layout);
            emit("located: ");
            emit_positions(found, found_count);
            if (decoding.rejected) {
                emit(" -> X_hv contradicts the estimate: error detected, not corrected");
            }
            emit("; X_n %s Y_n'\n", same_word(decoding.word, sent) ? "==" : "!=");
        }
    }

    struct IterativeStatistics {
        unsigned int generated;  // N1
        unsigned int detected;
        unsigned int multiplicity;  // N2
        unsigned int corrected;  // N3
        unsigned int rejected;   // detected, but left uncorrected
    };

    IterativeStatistics measure_iterative(const IterativeCode& code, unsigned int errors, SplitMix64& rng) {
        IterativeStatistics result{ kTrials, 0U, 0U, 0U, 0U };
        const uint64_t info_mask = code.k == 64U ? ~0ULL : (1ULL << code.k) - 1ULL;
        for (unsigned int trial = 0U; trial < kTrials; ++trial) {
            const IterativeWord sent = iterative_encode(code, rng.next() & info_mask);
            IterativeWord received = sent;
            unsigned int positions[kMaxInjectedErrors];
            pick_positions(rng, code.n, errors, positions);
            for (unsigned int i = 0U; i < errors; ++i) {
                flip_position(code, received, positions[i]);
            }
            const IterativeDecoding decoding = iterative_decode(code, received);
            result.detected += static_cast<unsigned int>(decoding.syndrome != 0ULL || decoding.total_syndrome != 0U);
            result.multiplicity += static_cast<unsigned int>(!decoding.rejected && decoding.corrections == errors);
            result.corrected += static_cast<unsigned int>(!decoding.rejected && same_word(decoding.word, sent));
            result.rejected += static_cast<unsigned int>(decoding.rejected);
        }
        return result;
    }

    void run_iterative_statistics(SplitMix64& rng) {
        emit("\nCorrecting ability: N1 = %u words per cell; N2/N1 = multiplicity identified, "
            "N3/N1 = all errors corrected, Rj/N1 = detected but not corrected\n", kTrials);
        emit("layout  groups  X_hv   r   n  rate  ");
        for (unsigned int errors = 1U; errors <= kMaxStatisticsErrors; ++errors) {
            emit("| i=%u N2/N1 N3/N1 Rj/N1 ", errors);
        }
        emit("\n");
        for (const VariantRow& variant : kVariantRows) {
            for (unsigned int groups = 2U; groups <= variant.max_groups; ++groups) {
                for (unsigned int total = 0U; total <= 1U; ++total) {
                    IterativeCode code;
                    if (!build_iterative(code, variant, groups, total != 0U)) {
                        continue;
                    }
                    char name[16];
                    iterative_name(code, name, sizeof(name));
                    emit("%-7s %6u  %4s %3u %3u %5.3f ", name, groups, total != 0U ? "yes" : "no",
                        code.r, code.n, static_cast<double>(code.k) / static_cast<double>(code.n));
                    for (unsigned int errors = 1U; errors <= kMaxStatisticsErrors; ++errors) {
                        const IterativeStatistics stats = measure_iterative(code, errors, rng);
                        emit("|     %5.3f %5.3f %5.3f ",
                            static_cast<double>(stats.multiplicity) / stats.generated,
                            static_cast<double>(stats.corrected) / stats.generated,
                            static_cast<double>(stats.rejected) / stats.generated);
                    }
                    emit("\n");
                }
            }
        }
    }

    bool iterative_self_check() {
        // Fig. 5.1: X_k = 011101111 in a 3x3 table -> X_h, X_v, X_hv = 0010011.
        constexpr VariantRow example{ 3U, 3U, 1U, 2U };
        constexpr char bits[] = "011101111";
        IterativeCode code;
        if (!build_iterative(code, example, 2U, true)) {
            return false;
        }
        uint64_t info = 0ULL;
        for (unsigned int i = 0U; i < 9U; ++i) {
            info |= static_cast<uint64_t>(bits[i] - '0') << i;
        }
        const IterativeWord word = iterative_encode(code, info);
        return word.checks == 0x24ULL && word.total == 1U;  // H = 001, V = 001
    }

    bool parse_bits(const char* text, unsigned int expected, uint64_t& value) {
        if (strlen(text) != expected) {
            return false;
        }
        value = 0ULL;
        for (unsigned int i = 0U; i < expected; ++i) {
            if (text[i] != '0' && text[i] != '1') {
                return false;
            }
            value |= static_cast<uint64_t>(text[i] - '0') << i;
        }
        return true;
    }

    void print_usage(const char* program) {
        printf("Usage: %s [message_file [seed [X_k as %u bits]]]\n", program, kVariantInfoBits);
    }

}  // namespace

int main(int argc, char* argv[]) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    if (argc > 4) {
        print_usage(argv[0]);
        return 1;
    }
    const char* message_path = argc > 1 ? argv[1] : kDefaultMessagePath;
    const uint64_t seed = argc > 2 ? strtoull(argv[2], nullptr, 10) : kDefaultSeed;

    static Message message;
    bool from_file = false;
    if (!load_message(message_path, message, from_file)) {
        printf("Message file %s is longer than %u symbols.\n", message_path, kMaxMessageBytes);
        return 1;
    }
    if (message.length < 2U) {
        printf("The message must contain at least 2 symbols (16 bits).\n");
        return 1;
    }
    static uint8_t message_bits[kMaxInfoBits];
    message_to_bits(message, message_bits);

    uint64_t iterative_info = 0ULL;
    if (argc > 3) {
        if (!parse_bits(argv[3], kVariantInfoBits, iterative_info)) {
            print_usage(argv[0]);
            return 1;
        }
    }
    else {
        for (unsigned int i = 0U; i < kVariantInfoBits && i < message.length * 8U; ++i) {
            iterative_info |= static_cast<uint64_t>(message_bits[i]) << i;
        }
    }

    g_report = fopen(kReportPath, "w");
    emit("Laboratory work 2, variant 12 (table 5.2 variant 2, k = %u)\n", kVariantInfoBits);
    emit("Message source: %s; seed = %" PRIu64 "; report file: %s\n",
        from_file ? message_path : "built-in default", seed, g_report != nullptr ? kReportPath : "(not written)");
    emit("Message: \"");
    emit_cp1251(message.bytes, message.length);
    emit("\" (%u symbols, Windows-1251, %u bits)\n", message.length, message.length * 8U);
    emit("Self-checks: textbook H(7,4) %s; fig. 5.1 iterative example %s\n",
        hamming_self_check() ? "PASS" : "FAIL", iterative_self_check() ? "PASS" : "FAIL");

    static HammingCode hamming;
    for (unsigned int d_min = 3U; d_min <= 4U; ++d_min) {
        SplitMix64 rng{ seed + d_min };
        build_hamming(hamming, message.length * 8U, d_min);
        emit("\n================ Part 1. Hamming code, d_min = %u ================\n", d_min);
        run_hamming_demo(hamming, message_bits, rng);
        run_hamming_statistics(hamming, rng);
    }

    emit("\n================ Part 2. Iterative codes, k = %u ================\n", kVariantInfoBits);
    SplitMix64 rng{ seed };
    for (const VariantRow& variant : kVariantRows) {
        IterativeCode code;
        if (build_iterative(code, variant, variant.max_groups, true)) {
            run_iterative_demo(code, iterative_info, rng);
        }
    }
    run_iterative_statistics(rng);

    if (g_report != nullptr) {
        fclose(g_report);
    }
    return 0;
}
