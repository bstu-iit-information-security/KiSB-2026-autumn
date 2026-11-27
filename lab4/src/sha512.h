#pragma once
#include <cstddef>
#include <cstdint>

// SHA-512 по FIPS 180-4. Данные можно подавать частями:
// Update(часть 1), Update(часть 2), ..., затем Final.
class Sha512 {
public:
    Sha512();
    void Update(const std::uint8_t* data, std::size_t length);
    void Final(std::uint8_t digest[64]);

private:
    void ProcessBlock(const std::uint8_t block[128]);

    std::uint64_t state[8];
    std::uint8_t buffer[128];
    std::size_t bufferLength;
    std::uint64_t totalLength;
};
