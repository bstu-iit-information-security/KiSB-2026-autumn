#include "modes.h"
#include <algorithm>
#include <stdexcept>

namespace {

Block read_block(const Bytes& data, std::size_t pos) {
    Block block;
    std::copy(data.begin() + pos, data.begin() + pos + BLOCK_SIZE, block.begin());
    return block;
}

void write_block(Bytes& data, std::size_t pos, const Block& block) {
    std::copy(block.begin(), block.end(), data.begin() + pos);
}

} // namespace

Bytes pkcs7_pad(const Bytes& data) {
    std::size_t k = BLOCK_SIZE - data.size() % BLOCK_SIZE;  // всегда от 1 до 16
    Bytes padded = data;
    padded.insert(padded.end(), k, static_cast<std::uint8_t>(k));
    return padded;
}

Bytes pkcs7_unpad(const Bytes& data) {
    if (data.empty() || data.size() % BLOCK_SIZE != 0)
        throw std::runtime_error("PKCS#7: длина данных не кратна размеру блока");

    std::size_t k = data.back();
    if (k < 1 || k > BLOCK_SIZE)
        throw std::runtime_error("PKCS#7: недопустимое значение дополнения");

    for (std::size_t i = data.size() - k; i < data.size(); ++i)
        if (data[i] != k)
            throw std::runtime_error("PKCS#7: байты дополнения повреждены");

    return Bytes(data.begin(), data.end() - k);
}

Bytes ecb_encrypt(const Bytes& plaintext, const Key& key) {
    Bytes padded = pkcs7_pad(plaintext);
    Bytes ciphertext(padded.size());
    for (std::size_t pos = 0; pos < padded.size(); pos += BLOCK_SIZE)
        write_block(ciphertext, pos, encrypt_block(read_block(padded, pos), key));
    return ciphertext;
}

Bytes ecb_decrypt(const Bytes& ciphertext, const Key& key) {
    if (ciphertext.empty() || ciphertext.size() % BLOCK_SIZE != 0)
        throw std::runtime_error("ECB: длина шифротекста не кратна 16 байтам");

    Bytes padded(ciphertext.size());
    for (std::size_t pos = 0; pos < ciphertext.size(); pos += BLOCK_SIZE)
        write_block(padded, pos, decrypt_block(read_block(ciphertext, pos), key));
    return pkcs7_unpad(padded);
}

// I_0 = IV, I_i = E_K(I_{i-1}); от последнего блока гаммы берётся столько байт,
// сколько осталось в сообщении, поэтому дополнение не нужно
Bytes ofb_crypt(const Bytes& data, const Key& key, const Block& iv) {
    Bytes result(data.size());
    Block gamma = iv;
    for (std::size_t pos = 0; pos < data.size(); pos += BLOCK_SIZE) {
        gamma = encrypt_block(gamma, key);
        std::size_t n = std::min(BLOCK_SIZE, data.size() - pos);
        for (std::size_t j = 0; j < n; ++j)
            result[pos + j] = data[pos + j] ^ gamma[j];
    }
    return result;
}
