#pragma once

#include "aes.hpp"

#include <string>

struct UnpadResult {
    bool ok = false;
    Bytes plaintext;
};

struct UnsafeUnpadResult {
    bool ok = false;
    std::string reason;
    Bytes plaintext;
};

Bytes add_pkcs7(const Bytes& data);
UnpadResult remove_pkcs7_secure(const Bytes& data);
UnsafeUnpadResult remove_pkcs7_unsafe(const Bytes& data);

Bytes ecb_encrypt(const Bytes& plaintext, const AES128& aes);
Bytes ecb_decrypt_raw(const Bytes& ciphertext, const AES128& aes);
UnpadResult ecb_decrypt(const Bytes& ciphertext, const AES128& aes);

Bytes cbc_encrypt(const Bytes& plaintext, const AES128& aes, const Block& iv);
Bytes cbc_decrypt_raw(const Bytes& ciphertext, const AES128& aes, const Block& iv);
UnpadResult cbc_decrypt(const Bytes& ciphertext, const AES128& aes, const Block& iv);
