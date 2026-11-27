#include "secure.h"

#include <random>

Point SelectPoint(std::uint32_t mask, const Point& ifOne, const Point& ifZero) {
    Point r;
    r.X = Select(mask, ifOne.X, ifZero.X);
    r.Y = Select(mask, ifOne.Y, ifZero.Y);
    r.Z = Select(mask, ifOne.Z, ifZero.Z);
    return r;
}

Point SecureMultiply(const BigNum& k, const Point& point) {
    Point result = Neutral();
    for (int bit = 255; bit >= 0; --bit) {
        result = Add(result, result);                   // удвоение
        Point withPoint = Add(result, point);           // сложение выполняется всегда
        std::uint32_t mask = 0 - GetBit(k, bit);        // 0x00000000 или 0xFFFFFFFF
        result = SelectPoint(mask, withPoint, result);
    }
    return result;
}

void RandomBytes(std::uint8_t* out, std::size_t count) {
    std::random_device device;
    for (std::size_t i = 0; i < count; ++i)
        out[i] = static_cast<std::uint8_t>(device());
}

// 512 случайных бит, приведённых по модулю q: смещение распределения
// порядка 2^-259, им можно пренебречь (так же получают r в Ed25519)
BigNum RandomScalar() {
    BigNum k;
    do {
        std::uint8_t bytes[64];
        RandomBytes(bytes, 64);
        k = Mod(FromBytesLE(bytes, 64), CURVE_Q);
    } while (IsEqual(k, Zero()));
    return k;
}
