#include <iostream>
#include <fstream>
#include <vector>
#include <string>

using namespace std;

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

unsigned char rotate_left(unsigned char value, int shift) {
    return (unsigned char)((value << shift) | (value >> (8 - shift)));
}

class AES128 {
    unsigned char keys[176];
    unsigned char S[256];
    unsigned char inverse_s[256];
    unsigned char RCON[10];

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
        for (int i = 0; i < 256; i++) {
            unsigned char inverse = 0;
            if (i != 0) {
                for (int j = 1; j < 256; j++) {
                    if (gf((unsigned char)i, (unsigned char)j) == 1) {
                        inverse = (unsigned char)j;
                        break;
                    }
                }
            }
            S[i] = inverse ^ rotate_left(inverse, 1) ^ rotate_left(inverse, 2) ^
                   rotate_left(inverse, 3) ^ rotate_left(inverse, 4) ^ 0x63;
            inverse_s[S[i]] = i;
        }
        RCON[0] = 1;
        for (int i = 1; i < 10; i++) RCON[i] = gf(RCON[i - 1], 2);
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

