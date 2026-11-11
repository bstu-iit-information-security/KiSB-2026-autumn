#include <iostream>
#include <fstream>
#include <vector>
#include <string>

using namespace std;

const unsigned char S[256] = {
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
};

const unsigned char RCON[10] = { 1,2,4,8,16,32,64,128,27,54 };

unsigned char gf(unsigned char a, unsigned char b) {
    unsigned char result = 0;
    for (int i = 0; i < 8; i++) {
        if (b & 1) result ^= a;
        bool high = (a & 128) != 0;
        a <<= 1;
        if (high) a ^= 0x1b;
        b >>= 1;
    }
    return result;
}

class AES128 {
    unsigned char keys[176];
    unsigned char inverse_s[256];

    void add_key(unsigned char state[16], int round) const {
        for (int i = 0; i < 16; i++) state[i] ^= keys[round * 16 + i];
    }

    void sub_bytes(unsigned char state[16], bool inverse) const {
        for (int i = 0; i < 16; i++) state[i] = inverse ? inverse_s[state[i]] : S[state[i]];
    }

    void shift_rows(unsigned char state[16], bool inverse) const {
        unsigned char copy[16];
        for (int i = 0; i < 16; i++) copy[i] = state[i];
        for (int row = 0; row < 4; row++) {
            for (int col = 0; col < 4; col++) {
                int from = inverse ? (col - row + 4) % 4 : (col + row) % 4;
                state[4 * col + row] = copy[4 * from + row];
            }
        }
    }

    void mix_columns(unsigned char state[16], bool inverse) const {
        for (int col = 0; col < 4; col++) {
            unsigned char a = state[4 * col];
            unsigned char b = state[4 * col + 1];
            unsigned char c = state[4 * col + 2];
            unsigned char d = state[4 * col + 3];
            if (inverse) {
                state[4 * col] = gf(a, 14) ^ gf(b, 11) ^ gf(c, 13) ^ gf(d, 9);
                state[4 * col + 1] = gf(a, 9) ^ gf(b, 14) ^ gf(c, 11) ^ gf(d, 13);
                state[4 * col + 2] = gf(a, 13) ^ gf(b, 9) ^ gf(c, 14) ^ gf(d, 11);
                state[4 * col + 3] = gf(a, 11) ^ gf(b, 13) ^ gf(c, 9) ^ gf(d, 14);
            }
            else {
                state[4 * col] = gf(a, 2) ^ gf(b, 3) ^ c ^ d;
                state[4 * col + 1] = a ^ gf(b, 2) ^ gf(c, 3) ^ d;
                state[4 * col + 2] = a ^ b ^ gf(c, 2) ^ gf(d, 3);
                state[4 * col + 3] = gf(a, 3) ^ b ^ c ^ gf(d, 2);
            }
        }
    }

public:
    AES128(const unsigned char key[16]) {
        for (int i = 0; i < 256; i++) inverse_s[S[i]] = i;
        for (int i = 0; i < 16; i++) keys[i] = key[i];
        for (int word = 4; word < 44; word++) {
            unsigned char temp[4];
            for (int j = 0; j < 4; j++) temp[j] = keys[4 * (word - 1) + j];
            if (word % 4 == 0) {
                unsigned char first = temp[0];
                temp[0] = S[temp[1]] ^ RCON[word / 4 - 1];
                temp[1] = S[temp[2]];
                temp[2] = S[temp[3]];
                temp[3] = S[first];
            }
            for (int j = 0; j < 4; j++) keys[4 * word + j] = keys[4 * (word - 4) + j] ^ temp[j];
        }
    }

    void encrypt_block(const unsigned char input[16], unsigned char output[16]) const {
        unsigned char state[16];
        for (int i = 0; i < 16; i++) state[i] = input[i];
        add_key(state, 0);
        for (int round = 1; round <= 9; round++) {
            sub_bytes(state, false);
            shift_rows(state, false);
            mix_columns(state, false);
            add_key(state, round);
        }
        sub_bytes(state, false);
        shift_rows(state, false);
        add_key(state, 10);
        for (int i = 0; i < 16; i++) output[i] = state[i];
    }

    void decrypt_block(const unsigned char input[16], unsigned char output[16]) const {
        unsigned char state[16];
        for (int i = 0; i < 16; i++) state[i] = input[i];
        add_key(state, 10);
        for (int round = 9; round >= 1; round--) {
            shift_rows(state, true);
            sub_bytes(state, true);
            add_key(state, round);
            mix_columns(state, true);
        }
        shift_rows(state, true);
        sub_bytes(state, true);
        add_key(state, 0);
        for (int i = 0; i < 16; i++) output[i] = state[i];
    }
};

void add_padding(vector<unsigned char>& data) {
    int count = 16 - data.size() % 16;
    for (int i = 0; i < count; i++) data.push_back(count);
}

bool remove_padding(vector<unsigned char>& data) {
    if (data.empty() || data.size() % 16 != 0) return false;
    int count = data.back();
    if (count < 1 || count > 16) return false;
    for (int i = 0; i < count; i++) {
        if (data[data.size() - 1 - i] != count) return false;
    }
    data.resize(data.size() - count);
    return true;
}

vector<unsigned char> encrypt_ecb(vector<unsigned char> data, const AES128& aes) {
    add_padding(data);
    vector<unsigned char> result(data.size());
    for (int pos = 0; pos < (int)data.size(); pos += 16) {
        aes.encrypt_block(&data[pos], &result[pos]);
    }
    return result;
}

bool decrypt_ecb(const vector<unsigned char>& data, const AES128& aes, vector<unsigned char>& result) {
    if (data.empty() || data.size() % 16 != 0) return false;
    result.resize(data.size());
    for (int pos = 0; pos < (int)data.size(); pos += 16) {
        aes.decrypt_block(&data[pos], &result[pos]);
    }
    if (!remove_padding(result)) {
        result.clear();
        return false;
    }
    return true;
}

vector<unsigned char> encrypt_cbc(vector<unsigned char> data, const AES128& aes, const unsigned char iv[16]) {
    add_padding(data);
    vector<unsigned char> result(data.size());
    unsigned char previous[16];
    unsigned char block[16];
    for (int i = 0; i < 16; i++) previous[i] = iv[i];
    for (int pos = 0; pos < (int)data.size(); pos += 16) {
        for (int i = 0; i < 16; i++) block[i] = data[pos + i] ^ previous[i];
        aes.encrypt_block(block, &result[pos]);
        for (int i = 0; i < 16; i++) previous[i] = result[pos + i];
    }
    return result;
}

bool decrypt_cbc(const vector<unsigned char>& data, const AES128& aes, const unsigned char iv[16], vector<unsigned char>& result) {
    if (data.empty() || data.size() % 16 != 0) return false;
    result.resize(data.size());
    unsigned char previous[16];
    unsigned char block[16];
    for (int i = 0; i < 16; i++) previous[i] = iv[i];
    for (int pos = 0; pos < (int)data.size(); pos += 16) {
        aes.decrypt_block(&data[pos], block);
        for (int i = 0; i < 16; i++) result[pos + i] = block[i] ^ previous[i];
        for (int i = 0; i < 16; i++) previous[i] = data[pos + i];
    }
    if (!remove_padding(result)) {
        result.clear();
        return false;
    }
    return true;
}

bool read_file(const string& name, vector<unsigned char>& data) {
    ifstream file(name.c_str(), ios::binary);
    if (!file) return false;
    char value;
    while (file.get(value)) data.push_back((unsigned char)value);
    return !file.bad();
}

bool write_file(const string& name, const vector<unsigned char>& data) {
    ofstream file(name.c_str(), ios::binary);
    if (!file) return false;
    for (int i = 0; i < (int)data.size(); i++) file.put((char)data[i]);
    return (bool)file;
}

int main() {
    setlocale(LC_ALL, "rus");

    const string file_name = "sample.txt";
    const string mode = "CBC";
    const unsigned char key[16] = {
        0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
        0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f
    };
    const unsigned char iv[16] = {
        0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,
        0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f
    };

    bool image = file_name.length() >= 4 &&
        file_name.substr(file_name.length() - 4) == ".bmp";
    string encrypted_name = image ? "encrypted.bmp" : "encrypted.bin";
    string decrypted_name = image ? "decrypted.bmp" : "decrypted.txt";
    vector<unsigned char> source;
    if (!read_file(file_name, source)) {
        cerr << "Не удалось открыть " << file_name << '\n';
        return 1;
    }
    if (image && source.size() < 54) {
        cerr << "BMP-файл слишком короткий.\n";
        return 1;
    }

    vector<unsigned char> header, data;
    if (image) {
        header.assign(source.begin(), source.begin() + 54);
        data.assign(source.begin() + 54, source.end());
    }
    else {
        data = source;
    }

    AES128 aes(key);
    vector<unsigned char> encrypted = mode == "CBC" ? encrypt_cbc(data, aes, iv)
        : encrypt_ecb(data, aes);
    vector<unsigned char> output = header;
    output.insert(output.end(), encrypted.begin(), encrypted.end());
    if (image) {
        int file_size = (int)output.size();
        int image_size = (int)encrypted.size();
        for (int i = 0; i < 4; i++) {
            output[2 + i] = (file_size >> (8 * i)) & 255;
            output[34 + i] = (image_size >> (8 * i)) & 255;
        }
    }
    if (!write_file(encrypted_name, output)) {
        cerr << "Не удалось записать шифротекст.\n";
        return 1;
    }

    cout << "Режим " << mode << ". Создан файл " << encrypted_name << ".\n";
    cout << "Измените его при необходимости и нажмите Enter для расшифрования...";
    cin.get();

    vector<unsigned char> changed_file;
    if (!read_file(encrypted_name, changed_file)) {
        cerr << "Не удалось открыть шифротекст.\n";
        return 1;
    }
    vector<unsigned char> changed_data;
    if (image) {
        if (changed_file.size() < 54) return 1;
        changed_data.assign(changed_file.begin() + 54, changed_file.end());
    }
    else {
        changed_data = changed_file;
    }

    vector<unsigned char> decrypted;
    bool valid = mode == "CBC" ? decrypt_cbc(changed_data, aes, iv, decrypted)
        : decrypt_ecb(changed_data, aes, decrypted);
    if (!valid) {
        cerr << "Расшифрование не удалось: неверная длина или PKCS#7.\n";
        return 1;
    }
    output = header;
    output.insert(output.end(), decrypted.begin(), decrypted.end());
    if (!write_file(decrypted_name, output)) {
        cerr << "Не удалось записать результат.\n";
        return 1;
    }
    cout << "Создан файл " << decrypted_name << ".\n";
    return 0;
}

