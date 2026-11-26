#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif

#include "belt.h"
#include "modes.h"

#include <bitset>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace std;

namespace {

string to_hex(const uint8_t* data, size_t n) {
    ostringstream out;
    for (size_t i = 0; i < n; ++i)
        out << (i ? " " : "") << hex << uppercase << setw(2) << setfill('0')
            << static_cast<int>(data[i]);
    return out.str();
}

void print_blocks(const Bytes& data) {
    for (size_t pos = 0; pos < data.size(); pos += BLOCK_SIZE) {
        size_t n = min(BLOCK_SIZE, data.size() - pos);
        cout << "    блок " << pos / BLOCK_SIZE + 1 << ": " << to_hex(&data[pos], n) << "\n";
    }
}

Bytes to_bytes(const string& s) {
    return Bytes(s.begin(), s.end());
}

// Непечатаемые байты заменяются точкой
string to_text(const Bytes& data) {
    string s;
    for (uint8_t byte : data)
        s += (byte >= 32 && byte <= 126) ? static_cast<char>(byte) : '.';
    return s;
}

int count_diff_bits(const uint8_t* x, const uint8_t* y, size_t n) {
    int count = 0;
    for (size_t i = 0; i < n; ++i)
        count += static_cast<int>(bitset<8>(x[i] ^ y[i]).count());
    return count;
}

Block random_iv() {
    random_device rd;
    Block iv;
    for (auto& byte : iv)
        byte = static_cast<uint8_t>(rd() & 0xFF);
    return iv;
}

// Ключи и блоки из контрольных примеров СТБ 34.101.31 (приложение А)
const Key ENC_KEY = {
    0xE9, 0xDE, 0xE7, 0x2C, 0x8F, 0x0C, 0x0F, 0xA6, 0x2D, 0xDB, 0x49, 0xF4, 0x6F, 0x73, 0x96, 0x47,
    0x06, 0x07, 0x53, 0x16, 0xED, 0x24, 0x7A, 0x37, 0x39, 0xCB, 0xA3, 0x83, 0x03, 0xA9, 0x8B, 0xF6};
const Block ENC_X = {0xB1, 0x94, 0xBA, 0xC8, 0x0A, 0x08, 0xF5, 0x3B,
                     0x36, 0x6D, 0x00, 0x8E, 0x58, 0x4A, 0x5D, 0xE4};
const Block ENC_Y = {0x69, 0xCC, 0xA1, 0xC9, 0x35, 0x57, 0xC9, 0xE3,
                     0xD6, 0x6B, 0xC3, 0xE0, 0xFA, 0x88, 0xFA, 0x6E};

const Key DEC_KEY = {
    0x92, 0xBD, 0x9B, 0x1C, 0xE5, 0xD1, 0x41, 0x01, 0x54, 0x45, 0xFB, 0xC9, 0x5E, 0x4D, 0x0E, 0xF2,
    0x68, 0x20, 0x80, 0xAA, 0x22, 0x7D, 0x64, 0x2F, 0x26, 0x87, 0xF9, 0x34, 0x90, 0x40, 0x55, 0x11};
const Block DEC_Y = {0xE1, 0x2B, 0xDC, 0x1A, 0xE2, 0x82, 0x57, 0xEC,
                     0x70, 0x3F, 0xCC, 0xF0, 0x95, 0xEE, 0x8D, 0xF1};
const Block DEC_X = {0x0D, 0xC5, 0x30, 0x06, 0x00, 0xCA, 0xB8, 0x40,
                     0xB3, 0x84, 0x48, 0xE5, 0xE9, 0x93, 0xF4, 0x21};

void test_vectors() {
    cout << "=== 1. Контрольные примеры СТБ 34.101.31 ===\n";

    Block y = encrypt_block(ENC_X, ENC_KEY);
    cout << "  Зашифрование: X = " << to_hex(ENC_X.data(), BLOCK_SIZE) << "\n"
         << "    получено  Y = " << to_hex(y.data(), BLOCK_SIZE) << "\n"
         << "    ожидалось Y = " << to_hex(ENC_Y.data(), BLOCK_SIZE) << "\n"
         << "    результат: " << (y == ENC_Y ? "совпадает" : "НЕ СОВПАДАЕТ") << "\n";

    Block x = decrypt_block(DEC_Y, DEC_KEY);
    cout << "  Расшифрование: Y = " << to_hex(DEC_Y.data(), BLOCK_SIZE) << "\n"
         << "    получено  X = " << to_hex(x.data(), BLOCK_SIZE) << "\n"
         << "    ожидалось X = " << to_hex(DEC_X.data(), BLOCK_SIZE) << "\n"
         << "    результат: " << (x == DEC_X ? "совпадает" : "НЕ СОВПАДАЕТ") << "\n";
}

void demo_messages(const Key& key) {
    cout << "\n=== 2. Шифрование строк, дополнение PKCS#7 ===\n";
    const string messages[] = {"Short msg", "Exactly 16 bytes", "This message is longer than one block"};

    for (const string& text : messages) {
        Bytes plain = to_bytes(text);
        cout << "\nСообщение: \"" << text << "\" (" << plain.size() << " байт)\n";

        Bytes padded = pkcs7_pad(plain);
        size_t k = padded.size() - plain.size();
        cout << "  PKCS#7: добавлено " << k << " байт со значением " << k << ", последний блок:\n"
             << "    " << to_hex(&padded[padded.size() - BLOCK_SIZE], BLOCK_SIZE) << "\n";

        Bytes ecb = ecb_encrypt(plain, key);
        Bytes ecb_plain = ecb_decrypt(ecb, key);
        cout << "  ECB, шифротекст (" << ecb.size() << " байт):\n";
        print_blocks(ecb);
        cout << "  ECB, расшифровано: \"" << to_text(ecb_plain) << "\" — "
             << (ecb_plain == plain ? "совпадает" : "НЕ СОВПАДАЕТ") << "\n";

        Block iv = random_iv();
        Bytes ofb = ofb_crypt(plain, key, iv);
        Bytes ofb_plain = ofb_crypt(ofb, key, iv);
        cout << "  OFB, IV = " << to_hex(iv.data(), BLOCK_SIZE) << "\n"
             << "  OFB, шифротекст (" << ofb.size() << " байт):\n";
        print_blocks(ofb);
        cout << "  OFB, расшифровано: \"" << to_text(ofb_plain) << "\" — "
             << (ofb_plain == plain ? "совпадает" : "НЕ СОВПАДАЕТ") << "\n";
    }
}

void demo_patterns(const Key& key) {
    cout << "\n=== 3. Данные с повторяющимися блоками: ECB и OFB ===\n";
    const string block_a(BLOCK_SIZE, 'A');
    const string block_b(BLOCK_SIZE, 'B');
    Bytes plain = to_bytes(block_a + block_a + block_b + block_a);

    cout << "  Открытый текст (блоки 1, 2, 4 одинаковые):\n";
    print_blocks(plain);

    cout << "  ECB:\n";
    print_blocks(ecb_encrypt(plain, key));

    Block iv = random_iv();
    cout << "  OFB, IV = " << to_hex(iv.data(), BLOCK_SIZE) << ":\n";
    print_blocks(ofb_crypt(plain, key, iv));
}

void print_damage(const string& mode, const Bytes& original, const Bytes& received) {
    cout << "  " << mode << ", расшифровано: \"" << to_text(received) << "\"\n";
    for (size_t pos = 0; pos < original.size(); pos += BLOCK_SIZE)
        cout << "    блок " << pos / BLOCK_SIZE + 1 << ": изменено "
             << count_diff_bits(&original[pos], &received[pos], BLOCK_SIZE) << " бит из 128\n";
}

void demo_bit_flip(const Key& key) {
    cout << "\n=== 4. Изменение одного бита шифротекста ===\n";
    Bytes plain = to_bytes("Transfer 100 BYN to account 4021 Kisel M.S. 2026");
    const size_t byte_index = 9;
    const uint8_t bit_mask = 0x08;

    cout << "  Открытый текст: \"" << to_text(plain) << "\" (" << plain.size() << " байт)\n"
         << "  В шифротексте инвертируется бит 3 (маска 0x08) байта " << byte_index
         << " — блок " << byte_index / BLOCK_SIZE + 1 << "\n";

    Bytes ecb = ecb_encrypt(plain, key);
    ecb[byte_index] ^= bit_mask;
    print_damage("ECB", plain, ecb_decrypt(ecb, key));

    Block iv = random_iv();
    Bytes ofb = ofb_crypt(plain, key, iv);
    ofb[byte_index] ^= bit_mask;
    print_damage("OFB", plain, ofb_crypt(ofb, key, iv));
}

} // namespace

int main() {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    try {
        test_vectors();
        demo_messages(ENC_KEY);
        demo_patterns(ENC_KEY);
        demo_bit_flip(ENC_KEY);
    } catch (const exception& e) {
        cerr << "Ошибка: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
