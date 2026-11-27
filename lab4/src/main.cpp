#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

#include "bignum.h"
#include "curve.h"
#include "protocols.h"
#include "secure.h"
#include "sha512.h"

#ifdef _WIN32
#include <windows.h>
#endif

using Bytes = std::vector<std::uint8_t>;

static Bytes HexToBytes(const std::string& hex) {
    Bytes bytes;
    for (std::size_t i = 0; i + 1 < hex.size(); i += 2)
        bytes.push_back(static_cast<std::uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
    return bytes;
}

static std::string BytesToHex(const std::uint8_t* bytes, std::size_t count) {
    const char* digits = "0123456789abcdef";
    std::string s;
    for (std::size_t i = 0; i < count; ++i) {
        s += digits[bytes[i] >> 4];
        s += digits[bytes[i] & 0xF];
    }
    return s;
}

static const char* YesNo(bool value) {
    return value ? "да" : "нет";
}

static void PrintPoint(const std::string& name, const AffinePoint& point) {
    std::cout << "  " << name << ".x = " << ToHex(point.x) << "\n";
    std::cout << "  " << name << ".y = " << ToHex(point.y) << "\n";
}

static void TestCurve() {
    std::cout << "=== 1. Параметры Ed25519 и единая формула сложения ===\n";
    std::cout << "  p   = " << ToHex(CURVE_P) << "\n";
    std::cout << "  a   = " << ToHex(CURVE_A) << "  (-1 mod p)\n";
    std::cout << "  d   = " << ToHex(CURVE_D) << "\n";
    std::cout << "  q   = " << ToHex(CURVE_Q) << "\n";
    std::cout << "  G.x = " << ToHex(BASE_X) << "\n";
    std::cout << "  G.y = " << ToHex(BASE_Y) << "\n";

    Point G = BasePoint();
    Point doubled = Add(G, G);
    std::cout << "G лежит на кривой:            " << YesNo(IsOnCurve(ToAffine(G))) << "\n";
    std::cout << "G + O = G:                    " << YesNo(IsSamePoint(Add(G, Neutral()), G)) << "\n";
    std::cout << "G + (-G) = O:                 " << YesNo(IsSamePoint(Add(G, Negate(G)), Neutral())) << "\n";
    std::cout << "2G = Add(G, G) лежит на кривой: " << YesNo(IsOnCurve(ToAffine(doubled))) << "\n";
    PrintPoint("2G", ToAffine(doubled));
    std::cout << "q * G = O:                    " << YesNo(IsSamePoint(Multiply(CURVE_Q, G), Neutral())) << "\n\n";
}

static void TestSha512() {
    std::cout << "=== 2. SHA-512, контрольный пример FIPS 180-4 ===\n";
    Bytes message = HexToBytes("616263");  // "abc"
    const char* expected = "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
                           "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f";
    std::uint8_t digest[64];
    Sha512 hash;
    hash.Update(message.data(), message.size());
    hash.Final(digest);
    std::string result = BytesToHex(digest, 64);
    std::cout << "Сообщение 616263 (\"abc\")\n";
    std::cout << "  получено:  " << result << "\n";
    std::cout << "  ожидалось: " << expected << "\n";
    std::cout << "результат: " << (result == expected ? "совпадает" : "НЕ совпадает") << "\n\n";
}

static void TestEcdh() {
    std::cout << "=== 3. Протокол ECDH ===\n";
    EcdhKeyPair alice = EcdhGenerateKeyPair();
    EcdhKeyPair bob = EcdhGenerateKeyPair();
    std::cout << "Алиса:\n  d_A   = " << ToHex(alice.d) << "\n";
    PrintPoint("Q_A", alice.Q);
    std::cout << "Боб:\n  d_B   = " << ToHex(bob.d) << "\n";
    PrintPoint("Q_B", bob.Q);

    BigNum secretAlice = EcdhSharedSecret(alice.d, bob.Q);
    BigNum secretBob = EcdhSharedSecret(bob.d, alice.Q);
    std::cout << "K у Алисы = x(d_A * Q_B) = " << ToHex(secretAlice) << "\n";
    std::cout << "K у Боба  = x(d_B * Q_A) = " << ToHex(secretBob) << "\n";
    std::cout << "результат: " << (IsEqual(secretAlice, secretBob) ? "общий секрет совпадает" : "секреты РАЗНЫЕ")
              << "\n\n";
}

struct RfcVector {
    const char* seed;
    const char* message;
    const char* publicKey;
    const char* signature;
};

static const RfcVector RFC_VECTORS[3] = {
    {"9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60", "",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"},
    {"4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb", "72",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"},
    {"c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7", "af82",
     "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"}};

static void TestEd25519() {
    std::cout << "=== 4. Ed25519: подпись и проверка, контрольные примеры RFC 8032 ===\n";
    for (int t = 0; t < 3; ++t) {
        const RfcVector& vector = RFC_VECTORS[t];
        Bytes seed = HexToBytes(vector.seed);
        Bytes message = HexToBytes(vector.message);
        std::cout << "Тест " << t + 1 << ": seed = " << vector.seed << "\n";
        std::cout << "  сообщение (" << message.size() << " байт) = " << vector.message << "\n";

        Ed25519Keys keys = Ed25519KeysFromSeed(seed.data());
        PrintPoint("A", keys.A);
        std::string encodedA = BytesToHex(keys.encodedA, 32);
        std::cout << "  A сжатый: " << encodedA << " — "
                  << (encodedA == vector.publicKey ? "совпадает с RFC" : "НЕ совпадает с RFC") << "\n";

        Signature signature = Ed25519Sign(keys, message.data(), message.size());
        PrintPoint("R", signature.R);
        std::cout << "  S   = " << ToHex(signature.S) << "\n";
        std::uint8_t encoded[64];
        EncodeSignature(signature, encoded);
        std::string encodedSignature = BytesToHex(encoded, 64);
        std::cout << "  подпись R||S: " << encodedSignature << "\n";
        std::cout << "  совпадает с RFC: " << YesNo(encodedSignature == vector.signature) << "\n";
        std::cout << "  проверка S*G = R + h*A: "
                  << (Ed25519Verify(keys.A, signature, message.data(), message.size()) ? "подпись верна"
                                                                                        : "подпись отклонена")
                  << "\n";
    }
    std::cout << "\n";
}

static void TestTamperedSignature() {
    std::cout << "=== 5. Искажение одного байта S ===\n";
    const RfcVector& vector = RFC_VECTORS[2];
    Bytes seed = HexToBytes(vector.seed);
    Bytes message = HexToBytes(vector.message);
    Ed25519Keys keys = Ed25519KeysFromSeed(seed.data());
    Signature signature = Ed25519Sign(keys, message.data(), message.size());

    Signature tampered = signature;
    std::uint8_t bytesS[32];
    ToBytesLE(tampered.S, bytesS, 32);
    bytesS[0] ^= 0x01;  // младший байт S, число остаётся меньше q
    tampered.S = FromBytesLE(bytesS, 32);

    std::cout << "Подпись теста 3 RFC, сообщение " << vector.message << "\n";
    std::cout << "  S исходный:  " << ToHex(signature.S) << "\n";
    std::cout << "  S искажённый: " << ToHex(tampered.S) << "\n";
    std::cout << "  проверка исходной:   "
              << (Ed25519Verify(keys.A, signature, message.data(), message.size()) ? "верна" : "отклонена") << "\n";
    std::cout << "  проверка искажённой: "
              << (Ed25519Verify(keys.A, tampered, message.data(), message.size()) ? "верна" : "отклонена") << "\n\n";
}

static void CountAdds(const std::string& name, const BigNum& k) {
    Point G = BasePoint();
    ResetAddCount();
    Point classic = Multiply(k, G);
    unsigned long long classicCount = GetAddCount();
    ResetAddCount();
    Point secure = SecureMultiply(k, G);
    unsigned long long secureCount = GetAddCount();
    std::cout << "  " << name << ": Multiply — " << classicCount << ", SecureMultiply — " << secureCount
              << ", результаты равны: " << YesNo(IsSamePoint(classic, secure)) << "\n";
}

static void TestOperationCount() {
    std::cout << "=== 6. Число вызовов Add при вычислении k * G ===\n";
    BigNum qMinusOne;
    Sub(CURVE_Q, FromUint(1), qMinusOne);
    CountAdds("k = 1       ", FromUint(1));
    CountAdds("k = q - 1   ", qMinusOne);
    CountAdds("k случайное ", RandomScalar());
}

int main() {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    TestCurve();
    TestSha512();
    TestEcdh();
    TestEd25519();
    TestTamperedSignature();
    TestOperationCount();
    return 0;
}
