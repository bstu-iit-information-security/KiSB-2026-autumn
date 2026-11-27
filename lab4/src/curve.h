#pragma once
#include <cstdint>

#include "bignum.h"

// Модуль 1. Скрученная кривая Эдвардса Ed25519: a*x^2 + y^2 = 1 + d*x^2*y^2 (mod p)

// Точка в проективных координатах: x = X / Z, y = Y / Z
struct Point {
    BigNum X, Y, Z;
};

struct AffinePoint {
    BigNum x, y;
};

extern const BigNum CURVE_P;   // модуль поля p = 2^255 - 19
extern const BigNum CURVE_A;   // a = -1 mod p
extern const BigNum CURVE_D;   // d = -121665 / 121666 mod p
extern const BigNum CURVE_Q;   // порядок базовой точки q
extern const BigNum BASE_X;    // координаты базовой точки G
extern const BigNum BASE_Y;

Point BasePoint();
Point Neutral();  // нейтральный элемент O = (0, 1)

Point FromAffine(const AffinePoint& point);
AffinePoint ToAffine(const Point& point);
bool IsOnCurve(const AffinePoint& point);
bool IsSamePoint(const Point& p1, const Point& p2);

Point Add(const Point& p1, const Point& p2);
Point Double(const Point& point);
Point Negate(const Point& point);
Point Multiply(const BigNum& k, const Point& point);

// Сжатая запись точки по RFC 8032: 32 байта y (младший байт первым),
// старший бит последнего байта — младший бит x
void Encode(const AffinePoint& point, std::uint8_t out[32]);

unsigned long long GetAddCount();
void ResetAddCount();
