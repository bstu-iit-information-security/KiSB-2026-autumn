#include "modes.hpp"

#include <algorithm>

namespace {

uint8_t ct_eq(uint8_t a, uint8_t b) {
    uint8_t diff = static_cast<uint8_t>(a ^ b);
    return static_cast<uint8_t>((diff | static_cast<uint8_t>(0 - diff)) >> 7 ? 0x00 : 0xFF);
}

}  

Bytes add_pkcs7(const Bytes& data) {
    size_t pad = 16 - (data.size() % 16);  
    Bytes out = data;
    out.insert(out.end(), pad, static_cast<uint8_t>(pad));
    return out;
}

UnpadResult remove_pkcs7_secure(const Bytes& data) {
    UnpadResult result;
    if (data.empty() || data.size() % 16 != 0) return result;

    uint8_t last = data.back();
    uint8_t found = 0;
    uint8_t pad = 0;
    for (unsigned candidate = 1; candidate <= 16; ++candidate) {
        uint8_t ok = ct_eq(last, static_cast<uint8_t>(candidate));
        for (unsigned i = 1; i <= 16; ++i) {
            uint8_t in_range = i <= candidate ? 0xFF : 0x00;
            uint8_t match = ct_eq(data[data.size() - i], static_cast<uint8_t>(candidate));
            ok = static_cast<uint8_t>(ok & ((in_range & match) | (~in_range & 0xFF)));
        }
        uint8_t valid_bit = static_cast<uint8_t>(ok >> 7);  
        uint8_t mask = static_cast<uint8_t>(0 - valid_bit);  
        found = static_cast<uint8_t>(found | valid_bit);
        pad = static_cast<uint8_t>(pad | (static_cast<uint8_t>(candidate) & mask));
    }

    if (found == 0 || pad == 0 || pad > data.size()) return result;
    result.plaintext.assign(data.begin(), data.end() - pad);
    result.ok = true;
    return result;
}

UnsafeUnpadResult remove_pkcs7_unsafe(const Bytes& data) {
    UnsafeUnpadResult result;
    if (data.empty() || data.size() % 16 != 0) {
        result.reason = "bad length";
        return result;
    }
    unsigned pad = data.back();
    if (pad < 1 || pad > 16) {
        result.reason = "bad padding byte";
        return result;
    }
    for (unsigned i = 0; i < pad; ++i) {
        if (data[data.size() - 1 - i] != pad) {
            result.reason = "padding bytes differ";
            return result;
        }
    }
    result.plaintext.assign(data.begin(), data.end() - pad);
    result.reason = "ok";
    result.ok = true;
    return result;
}

Bytes ecb_encrypt(const Bytes& plaintext, const AES128& aes) {
    Bytes padded = add_pkcs7(plaintext);
    Bytes out(padded.size());
    for (size_t pos = 0; pos < padded.size(); pos += 16) {
        Block encrypted = aes.encrypt_block(block_at(padded, pos));
        std::copy(encrypted.begin(), encrypted.end(), out.begin() + pos);
    }
    return out;
}

Bytes ecb_decrypt_raw(const Bytes& ciphertext, const AES128& aes) {
    Bytes out(ciphertext.size());
    for (size_t pos = 0; pos < ciphertext.size(); pos += 16) {
        Block decrypted = aes.decrypt_block(block_at(ciphertext, pos));
        std::copy(decrypted.begin(), decrypted.end(), out.begin() + pos);
    }
    return out;
}

UnpadResult ecb_decrypt(const Bytes& ciphertext, const AES128& aes) {
    return remove_pkcs7_secure(ecb_decrypt_raw(ciphertext, aes));
}

Bytes cbc_encrypt(const Bytes& plaintext, const AES128& aes, const Block& iv) {
    Bytes padded = add_pkcs7(plaintext);
    Bytes out(padded.size());
    Block previous = iv;
    for (size_t pos = 0; pos < padded.size(); pos += 16) {
        Block xored = xor_blocks(block_at(padded, pos), previous);
        Block encrypted = aes.encrypt_block(xored);
        std::copy(encrypted.begin(), encrypted.end(), out.begin() + pos);
        previous = encrypted;
    }
    return out;
}

Bytes cbc_decrypt_raw(const Bytes& ciphertext, const AES128& aes, const Block& iv) {
    Bytes out(ciphertext.size());
    Block previous = iv;
    for (size_t pos = 0; pos < ciphertext.size(); pos += 16) {
        Block block = block_at(ciphertext, pos);
        Block decrypted = aes.decrypt_block(block);
        Block plaintext = xor_blocks(decrypted, previous);
        std::copy(plaintext.begin(), plaintext.end(), out.begin() + pos);
        previous = block;
    }
    return out;
}

UnpadResult cbc_decrypt(const Bytes& ciphertext, const AES128& aes, const Block& iv) {
    return remove_pkcs7_secure(cbc_decrypt_raw(ciphertext, aes, iv));
}
