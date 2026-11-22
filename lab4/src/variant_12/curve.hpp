#pragma once

#include "arithmetic.hpp"

namespace lab4 {
struct Point {
    UInt256 x{};
    UInt256 y{};
    std::uint32_t infinity = 1;
};

struct Curve {
    Modulus field;
    Modulus order;
    UInt256 a;
    UInt256 b;
    Point generator;
};

const Curve& bign_curve() noexcept;
std::uint32_t point_equal(const Point& a, const Point& b) noexcept;
std::uint32_t on_curve(const Curve& curve, const Point& point) noexcept;
Point point_select(const Point& a, const Point& b, std::uint32_t choose_b) noexcept;
Point point_add(const Curve& curve, const Point& a, const Point& b) noexcept;
Point point_double(const Curve& curve, const Point& point) noexcept;
// Branching reference algorithm. Use only with public scalars.
Point multiply_public(const Curve& curve, const UInt256& scalar, const Point& point) noexcept;
bool valid_public_key(const Curve& curve, const Point& point) noexcept;
}
