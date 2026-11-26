#pragma once
#include "belt.h"
#include <vector>

using Bytes = std::vector<std::uint8_t>;

Bytes pkcs7_pad(const Bytes& data);
Bytes pkcs7_unpad(const Bytes& data);

Bytes ecb_encrypt(const Bytes& plaintext, const Key& key);
Bytes ecb_decrypt(const Bytes& ciphertext, const Key& key);

// OFB: зашифрование и расшифрование — одна и та же операция (XOR с гаммой)
Bytes ofb_crypt(const Bytes& data, const Key& key, const Block& iv);
