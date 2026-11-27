#pragma once
#include <cstddef>
#include <cstdint>

#include "bignum.h"
#include "curve.h"

// Модуль 3. Операции с секретными скалярами без ветвлений по их битам

// mask = 0xFFFFFFFF -> ifOne, mask = 0 -> ifZero; координаты выбираются маской
Point SelectPoint(std::uint32_t mask, const Point& ifOne, const Point& ifZero);

// Double-and-Add-Always на единой формуле сложения: на каждый из 256 бит
// ровно два вызова одной и той же функции Add, независимо от значения бита
Point SecureMultiply(const BigNum& k, const Point& point);

void RandomBytes(std::uint8_t* out, std::size_t count);
BigNum RandomScalar();  // случайное число из [1, q - 1]
