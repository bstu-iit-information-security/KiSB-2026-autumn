#include "curve.h"

const BigNum CURVE_P = FromHex("7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffed");
const BigNum CURVE_A = FromHex("7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffec");
const BigNum CURVE_D = FromHex("52036cee2b6ffe738cc740797779e89800700a4d4141d8ab75eb4dca135978a3");
const BigNum CURVE_Q = FromHex("1000000000000000000000000000000014def9dea2f79cd65812631a5cf5d3ed");
const BigNum BASE_X  = FromHex("216936d3cd6e53fec0a4e231fdd6dc5c692cc7609525a7b2c9562d608f25d51a");
const BigNum BASE_Y  = FromHex("6666666666666666666666666666666666666666666666666666666666666658");

static unsigned long long addCount = 0;

static BigNum FieldAdd(const BigNum& a, const BigNum& b) { return AddMod(a, b, CURVE_P); }
static BigNum FieldSub(const BigNum& a, const BigNum& b) { return SubMod(a, b, CURVE_P); }
static BigNum FieldMul(const BigNum& a, const BigNum& b) { return MulMod(a, b, CURVE_P); }

Point FromAffine(const AffinePoint& point) {
    Point r;
    r.X = point.x;
    r.Y = point.y;
    r.Z = FromUint(1);
    return r;
}

Point BasePoint() {
    AffinePoint g;
    g.x = BASE_X;
    g.y = BASE_Y;
    return FromAffine(g);
}

Point Neutral() {
    AffinePoint o;
    o.x = Zero();
    o.y = FromUint(1);
    return FromAffine(o);
}

// Единственная инверсия — при переходе обратно к (x, y)
AffinePoint ToAffine(const Point& point) {
    BigNum zInverse = InvMod(point.Z, CURVE_P);
    AffinePoint r;
    r.x = FieldMul(point.X, zInverse);
    r.y = FieldMul(point.Y, zInverse);
    return r;
}

bool IsOnCurve(const AffinePoint& point) {
    if (!IsLess(point.x, CURVE_P) || !IsLess(point.y, CURVE_P))
        return false;
    BigNum x2 = FieldMul(point.x, point.x);
    BigNum y2 = FieldMul(point.y, point.y);
    BigNum left = FieldAdd(FieldMul(CURVE_A, x2), y2);
    BigNum right = FieldAdd(FromUint(1), FieldMul(CURVE_D, FieldMul(x2, y2)));
    return IsEqual(left, right);
}

// X1/Z1 = X2/Z2 и Y1/Z1 = Y2/Z2  <=>  X1*Z2 = X2*Z1 и Y1*Z2 = Y2*Z1
bool IsSamePoint(const Point& p1, const Point& p2) {
    bool sameX = IsEqual(FieldMul(p1.X, p2.Z), FieldMul(p2.X, p1.Z));
    bool sameY = IsEqual(FieldMul(p1.Y, p2.Z), FieldMul(p2.Y, p1.Z));
    return sameX && sameY;
}

// Единая формула сложения в проективных координатах (п. 4.2 методички).
// Подходит и для P1 != P2, и для P1 = P2, и для O: ни одной проверки не нужно.
Point Add(const Point& p1, const Point& p2) {
    ++addCount;
    BigNum A = FieldMul(p1.Z, p2.Z);
    BigNum B = FieldMul(A, A);
    BigNum C = FieldMul(p1.X, p2.X);
    BigNum D = FieldMul(p1.Y, p2.Y);
    BigNum E = FieldMul(CURVE_D, FieldMul(C, D));
    BigNum BminusE = FieldSub(B, E);
    BigNum BplusE = FieldAdd(B, E);

    BigNum sumProduct = FieldMul(FieldAdd(p1.X, p1.Y), FieldAdd(p2.X, p2.Y));
    BigNum xPart = FieldSub(FieldSub(sumProduct, C), D);   // X1*Y2 + Y1*X2
    BigNum yPart = FieldSub(D, FieldMul(CURVE_A, C));      // Y1*Y2 - a*X1*X2

    Point r;
    r.X = FieldMul(FieldMul(A, xPart), BminusE);
    r.Y = FieldMul(FieldMul(A, yPart), BplusE);
    r.Z = FieldMul(BminusE, BplusE);
    return r;
}

Point Double(const Point& point) {
    return Add(point, point);
}

Point Negate(const Point& point) {
    Point r = point;
    r.X = FieldSub(Zero(), point.X);
    return r;
}

// Классический Double-and-Add. Ветвление по битам k, поэтому только
// для открытых скаляров (проверка подписи). Для секретов — SecureMultiply.
Point Multiply(const BigNum& k, const Point& point) {
    Point result = Neutral();
    for (int bit = 255; bit >= 0; --bit) {
        result = Double(result);
        if (GetBit(k, bit))
            result = Add(result, point);
    }
    return result;
}

void Encode(const AffinePoint& point, std::uint8_t out[32]) {
    ToBytesLE(point.y, out, 32);
    out[31] |= static_cast<std::uint8_t>(GetBit(point.x, 0) << 7);
}

unsigned long long GetAddCount() {
    return addCount;
}

void ResetAddCount() {
    addCount = 0;
}
