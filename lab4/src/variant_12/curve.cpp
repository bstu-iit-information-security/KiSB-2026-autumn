#include "curve.hpp"

namespace lab4 {
namespace {
UInt256 parameter(const char* hex) noexcept {
    UInt256 result{};
    parse_hex(hex, result);
    return result;
}
Curve make_curve() noexcept {
    // bign-curve256v1, STB 34.101.45, Appendix B. Numeric hex is big-endian.
    return {
        make_modulus(parameter("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff43")),
        make_modulus(parameter("ffffffffffffffffffffffffffffffffd95c8ed60dfb4dfc7e5abf99263d6607")),
        parameter("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff40"),
        parameter("77ce6c1515f3a8edd2c13aabe4d8fbbe4cf55069978b9253b22e7d6bd69c03f1"),
        {parameter("0000000000000000000000000000000000000000000000000000000000000000"),
         parameter("6bf7fc3cfb16d69f5ce4c9a351d6835d78913966c408f6521e29cf1804516a93"), 0}
    };
}
}

const Curve& bign_curve() noexcept {
    static const Curve curve = make_curve();
    return curve;
}

std::uint32_t point_equal(const Point& a, const Point& b) noexcept {
    const auto both_finite = (a.infinity ^ 1U) & (b.infinity ^ 1U);
    return (a.infinity & b.infinity) | (both_finite & equal(a.x, b.x) & equal(a.y, b.y));
}

std::uint32_t on_curve(const Curve& c, const Point& p) noexcept {
    const auto x2 = mod_mul(p.x, p.x, c.field);
    const auto rhs = mod_add(mod_add(mod_mul(x2, p.x, c.field), mod_mul(c.a, p.x, c.field), c.field),
                             c.b, c.field);
    const auto lhs = mod_mul(p.y, p.y, c.field);
    return p.infinity | equal(lhs, rhs);
}

Point point_select(const Point& a, const Point& b, std::uint32_t choose_b) noexcept {
    const auto mask = 0U - choose_b;
    return {select(a.x, b.x, choose_b), select(a.y, b.y, choose_b),
            a.infinity ^ ((a.infinity ^ b.infinity) & mask)};
}

Point point_add(const Curve& c, const Point& p, const Point& q) noexcept {
    const auto same_x = equal(p.x, q.x);
    const auto same_y = equal(p.y, q.y);
    const auto doubling = same_x & same_y;
    const auto x2 = mod_mul(p.x, p.x, c.field);
    const auto double_numerator = mod_add(mod_add(mod_add(x2, x2, c.field), x2, c.field), c.a, c.field);
    const auto numerator = select(mod_sub(q.y, p.y, c.field), double_numerator, doubling);
    const auto denominator = select(mod_sub(q.x, p.x, c.field), mod_add(p.y, p.y, c.field), doubling);
    const auto slope = mod_mul(numerator, mod_inverse(denominator, c.field), c.field);
    const auto x = mod_sub(mod_sub(mod_mul(slope, slope, c.field), p.x, c.field), q.x, c.field);
    const auto y = mod_sub(mod_mul(slope, mod_sub(p.x, x, c.field), c.field), p.y, c.field);
    const auto vertical = same_x & ((same_y ^ 1U) | (nonzero(p.y) ^ 1U));
    const Point sum = point_select({x, y, 0}, {}, vertical);
    return point_select(point_select(sum, q, p.infinity), p, q.infinity);
}

Point point_double(const Curve& c, const Point& p) noexcept {
    return point_add(c, p, p);
}

Point multiply_public(const Curve& c, const UInt256& scalar, const Point& p) noexcept {
    Point result{};
    for (int i = 255; i >= 0; --i) {
        result = point_double(c, result);
        if (((scalar.words[i / 32] >> (i % 32)) & 1U) != 0) result = point_add(c, result, p);
    }
    return result;
}

bool valid_public_key(const Curve& c, const Point& p) noexcept {
    if (p.infinity != 0 || !less(p.x, c.field.value) || !less(p.y, c.field.value)) return false;
    if (!on_curve(c, p)) return false;
    return multiply_public(c, c.order.value, p).infinity == 1;
}
}
