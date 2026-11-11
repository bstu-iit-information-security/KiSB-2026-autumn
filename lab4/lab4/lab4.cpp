#include <iostream>
#include <iomanip>
#include <cstdint>
#include <cstring>

// ============================================================================
// БАЗОВАЯ ДЛИННАЯ АРИФМЕТИКА (256-бит на uint32_t, полная совместимость с MSVC)
// ============================================================================
struct UInt256 {
    uint32_t d[8] = { 0 }; // Little-endian представление (8 x 32-bit)

    static UInt256 from_hex(const char* hex) {
        UInt256 r;
        size_t len = std::strlen(hex);
        for (size_t i = 0; i < len; ++i) {
            char c = hex[len - 1 - i];
            uint32_t v = 0;
            if (c >= '0' && c <= '9') v = c - '0';
            else if (c >= 'a' && c <= 'f') v = c - 'a' + 10;
            else if (c >= 'A' && c <= 'F') v = c - 'A' + 10;

            size_t limb = i / 8;
            size_t shift = (i % 8) * 4;
            if (limb < 8) {
                r.d[limb] |= (v << shift);
            }
        }
        return r;
    }

    void print_hex() const {
        std::ios state(nullptr);
        state.copyfmt(std::cout);
        for (int i = 7; i >= 0; --i) {
            std::cout << std::hex << std::setw(8) << std::setfill('0') << d[i];
        }
        std::cout.copyfmt(state);
    }

    bool is_zero() const {
        uint32_t acc = 0;
        for (int i = 0; i < 8; ++i) acc |= d[i];
        return acc == 0;
    }

    bool get_bit(size_t idx) const {
        if (idx >= 256) return false;
        return (d[idx / 32] >> (idx % 32)) & 1U;
    }
};

bool operator==(const UInt256& a, const UInt256& b) {
    for (int i = 0; i < 8; ++i) {
        if (a.d[i] != b.d[i]) return false;
    }
    return true;
}

bool operator!=(const UInt256& a, const UInt256& b) {
    return !(a == b);
}

bool operator>=(const UInt256& a, const UInt256& b) {
    for (int i = 7; i >= 0; --i) {
        if (a.d[i] > b.d[i]) return true;
        if (a.d[i] < b.d[i]) return false;
    }
    return true;
}

struct UInt512 {
    uint32_t d[16] = { 0 };
};

UInt256 sub_raw(const UInt256& a, const UInt256& b, uint32_t& borrow) {
    UInt256 r;
    borrow = 0;
    for (size_t i = 0; i < 8; ++i) {
        int64_t diff = (int64_t)a.d[i] - b.d[i] - borrow;
        if (diff < 0) {
            diff += (1ULL << 32);
            borrow = 1;
        }
        else {
            borrow = 0;
        }
        r.d[i] = (uint32_t)diff;
    }
    return r;
}

UInt256 add_raw(const UInt256& a, const UInt256& b, uint32_t& carry) {
    UInt256 r;
    carry = 0;
    for (size_t i = 0; i < 8; ++i) {
        uint64_t sum = (uint64_t)a.d[i] + b.d[i] + carry;
        r.d[i] = (uint32_t)sum;
        carry = (uint32_t)(sum >> 32);
    }
    return r;
}

UInt256 mod_add(const UInt256& a, const UInt256& b, const UInt256& m) {
    uint32_t carry = 0;
    UInt256 res = add_raw(a, b, carry);
    if (carry || res >= m) {
        uint32_t b_out = 0;
        res = sub_raw(res, m, b_out);
    }
    return res;
}

UInt256 mod_sub(const UInt256& a, const UInt256& b, const UInt256& m) {
    if (a >= b) {
        uint32_t borrow = 0;
        return sub_raw(a, b, borrow);
    }
    else {
        uint32_t carry = 0, borrow = 0;
        UInt256 t = add_raw(a, m, carry);
        return sub_raw(t, b, borrow);
    }
}

UInt512 mul_256x256(const UInt256& a, const UInt256& b) {
    UInt512 r;
    for (size_t i = 0; i < 8; ++i) {
        uint64_t carry = 0;
        for (size_t j = 0; j < 8; ++j) {
            uint64_t cur = (uint64_t)a.d[i] * b.d[j] + r.d[i + j] + carry;
            r.d[i + j] = (uint32_t)cur;
            carry = cur >> 32;
        }
        r.d[i + 8] += (uint32_t)carry;
    }
    return r;
}

UInt256 mod_reduce(UInt512 a, const UInt256& m) {
    for (int i = 511; i >= 256; --i) {
        size_t limb = i / 32;
        size_t bit = i % 32;
        if ((a.d[limb] >> bit) & 1U) {
            size_t shift = i - 256;
            UInt512 sub_m;
            size_t m_limb = shift / 32;
            size_t m_bit = shift % 32;
            for (size_t k = 0; k < 8; ++k) {
                uint32_t low = m.d[k] << m_bit;
                uint32_t high = m_bit ? (m.d[k] >> (32 - m_bit)) : 0;
                sub_m.d[m_limb + k] |= low;
                if (m_bit && m_limb + k + 1 < 16) sub_m.d[m_limb + k + 1] |= high;
            }
            int64_t borrow = 0;
            for (size_t k = 0; k < 16; ++k) {
                int64_t diff = (int64_t)a.d[k] - sub_m.d[k] - borrow;
                if (diff < 0) {
                    diff += (1ULL << 32);
                    borrow = 1;
                }
                else {
                    borrow = 0;
                }
                a.d[k] = (uint32_t)diff;
            }
        }
    }
    UInt256 res;
    for (size_t i = 0; i < 8; ++i) res.d[i] = a.d[i];
    while (res >= m) {
        uint32_t b = 0;
        res = sub_raw(res, m, b);
    }
    return res;
}

UInt256 mod_mul(const UInt256& a, const UInt256& b, const UInt256& m) {
    UInt512 prod = mul_256x256(a, b);
    return mod_reduce(prod, m);
}

// ============================================================================
// МОДУЛЬ 3. CONSTANT-TIME ОПТИМИЗАЦИЯ (Инверсия по FLT: a^(m-2))
// ============================================================================
namespace ConstantTimeCore {
    UInt256 mod_inv_flt(const UInt256& base, const UInt256& mod) {
        uint32_t b = 0;
        UInt256 two; two.d[0] = 2;
        UInt256 exp = sub_raw(mod, two, b);

        UInt256 res; res.d[0] = 1;
        UInt256 cur = base;

        for (size_t i = 0; i < 256; ++i) {
            if (exp.get_bit(i)) {
                res = mod_mul(res, cur, mod);
            }
            cur = mod_mul(cur, cur, mod);
        }
        return res;
    }
}

// ============================================================================
// МОДУЛЬ 1. АЛГЕБРА ЭЛЛИПТИЧЕСКИХ КРИВЫХ (Вейерштрасс, Аффинные координаты)
// ============================================================================
namespace EllipticCurveAlgebra {
    struct CurveParams {
        UInt256 p, a, b, q, Gx, Gy;
    };

    struct Point {
        UInt256 x, y;
        bool is_infinity = false;

        static Point infinity() {
            Point p;
            p.is_infinity = true;
            return p;
        }
    };

    CurveParams get_secp256k1() {
        CurveParams c;
        c.p = UInt256::from_hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F");
        c.a = UInt256::from_hex("0000000000000000000000000000000000000000000000000000000000000000");
        c.b = UInt256::from_hex("0000000000000000000000000000000000000000000000000000000000000007");
        c.q = UInt256::from_hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141");
        c.Gx = UInt256::from_hex("79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798");
        c.Gy = UInt256::from_hex("483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8");
        return c;
    }

    Point point_double(const Point& P, const CurveParams& crv) {
        if (P.is_infinity || P.y.is_zero()) return Point::infinity();

        UInt256 three; three.d[0] = 3;
        UInt256 two; two.d[0] = 2;

        UInt256 x_sq = mod_mul(P.x, P.x, crv.p);
        UInt256 num = mod_add(mod_mul(three, x_sq, crv.p), crv.a, crv.p);

        UInt256 den = mod_mul(two, P.y, crv.p);
        UInt256 den_inv = ConstantTimeCore::mod_inv_flt(den, crv.p);
        UInt256 s = mod_mul(num, den_inv, crv.p);

        UInt256 s_sq = mod_mul(s, s, crv.p);
        UInt256 two_x = mod_add(P.x, P.x, crv.p);
        UInt256 x3 = mod_sub(s_sq, two_x, crv.p);

        UInt256 x_diff = mod_sub(P.x, x3, crv.p);
        UInt256 y3 = mod_sub(mod_mul(s, x_diff, crv.p), P.y, crv.p);

        return { x3, y3, false };
    }

    Point point_add(const Point& P, const Point& Q, const CurveParams& crv) {
        if (P.is_infinity) return Q;
        if (Q.is_infinity) return P;
        if (P.x == Q.x) {
            if (P.y == Q.y) return point_double(P, crv);
            return Point::infinity();
        }

        UInt256 dy = mod_sub(Q.y, P.y, crv.p);
        UInt256 dx = mod_sub(Q.x, P.x, crv.p);
        UInt256 dx_inv = ConstantTimeCore::mod_inv_flt(dx, crv.p);
        UInt256 s = mod_mul(dy, dx_inv, crv.p);

        UInt256 s_sq = mod_mul(s, s, crv.p);
        UInt256 x3 = mod_sub(mod_sub(s_sq, P.x, crv.p), Q.x, crv.p);

        UInt256 x_diff = mod_sub(P.x, x3, crv.p);
        UInt256 y3 = mod_sub(mod_mul(s, x_diff, crv.p), P.y, crv.p);

        return { x3, y3, false };
    }

    Point scalar_mul(const UInt256& scalar, const Point& P, const CurveParams& crv) {
        Point res = Point::infinity();
        Point temp = P;
        for (size_t i = 0; i < 256; ++i) {
            if (scalar.get_bit(i)) {
                res = point_add(res, temp, crv);
            }
            temp = point_double(temp, crv);
        }
        return res;
    }
}

// ============================================================================
// МОДУЛЬ 2. КРИПТОГРАФИЧЕСКИЕ ПРОТОКОЛЫ (ECDH и ЭЦП ECDSA)
// ============================================================================
namespace CryptoProtocols {
    using namespace EllipticCurveAlgebra;

    struct KeyPair {
        UInt256 priv;
        Point pub;
    };

    struct Signature {
        UInt256 r;
        UInt256 s;
    };

    KeyPair generate_keys(const UInt256& priv_key, const CurveParams& crv) {
        Point G = { crv.Gx, crv.Gy, false };
        Point pub = scalar_mul(priv_key, G, crv);
        return { priv_key, pub };
    }

    UInt256 compute_ecdh(const UInt256& priv, const Point& other_pub, const CurveParams& crv) {
        Point S = scalar_mul(priv, other_pub, crv);
        return S.x;
    }

    Signature ecdsa_sign(const UInt256& hash, const UInt256& priv, const UInt256& k, const CurveParams& crv) {
        Point G = { crv.Gx, crv.Gy, false };
        Point C = scalar_mul(k, G, crv);

        UInt256 r = C.x;
        while (r >= crv.q) {
            uint32_t b = 0;
            r = sub_raw(r, crv.q, b);
        }

        UInt256 k_inv = ConstantTimeCore::mod_inv_flt(k, crv.q);
        UInt256 rd = mod_mul(r, priv, crv.q);
        UInt256 sum = mod_add(hash, rd, crv.q);
        UInt256 s = mod_mul(k_inv, sum, crv.q);

        return { r, s };
    }

    bool ecdsa_verify(const UInt256& hash, const Point& pub, const Signature& sig, const CurveParams& crv) {
        if (sig.r.is_zero() || sig.r >= crv.q) return false;
        if (sig.s.is_zero() || sig.s >= crv.q) return false;

        Point G = { crv.Gx, crv.Gy, false };
        UInt256 w = ConstantTimeCore::mod_inv_flt(sig.s, crv.q);

        UInt256 u1 = mod_mul(hash, w, crv.q);
        UInt256 u2 = mod_mul(sig.r, w, crv.q);

        Point P1 = scalar_mul(u1, G, crv);
        Point P2 = scalar_mul(u2, pub, crv);
        Point C_prime = point_add(P1, P2, crv);

        if (C_prime.is_infinity) return false;

        UInt256 v = C_prime.x;
        while (v >= crv.q) {
            uint32_t b = 0;
            v = sub_raw(v, crv.q, b);
        }

        return (v == sig.r);
    }
}

// ============================================================================
// ТОЧКА ВХОДА
// ============================================================================
int main() {
    auto curve = EllipticCurveAlgebra::get_secp256k1();

    std::cout << "========================================================\n";
    std::cout << "  LABORATORY WORK #4: ECDH & ECDSA (VARIANT 3)\n";
    std::cout << "========================================================\n\n";

    // 1. ECDH
    std::cout << "--- 1. ECDH KEY EXCHANGE ---\n";
    UInt256 dA = UInt256::from_hex("C90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22");
    UInt256 dB = UInt256::from_hex("0F1A2B3C4D5E6F708192A3B4C5D6E7F80112233445566778899AABBCCDDEEFF0");

    auto alice = CryptoProtocols::generate_keys(dA, curve);
    auto bob = CryptoProtocols::generate_keys(dB, curve);

    std::cout << "[Alice] PubKey.X: "; alice.pub.x.print_hex(); std::cout << "\n";
    std::cout << "[Alice] PubKey.Y: "; alice.pub.y.print_hex(); std::cout << "\n";
    std::cout << "[Bob]   PubKey.X: "; bob.pub.x.print_hex(); std::cout << "\n";
    std::cout << "[Bob]   PubKey.Y: "; bob.pub.y.print_hex(); std::cout << "\n";

    UInt256 secret_alice = CryptoProtocols::compute_ecdh(dA, bob.pub, curve);
    UInt256 secret_bob = CryptoProtocols::compute_ecdh(dB, alice.pub, curve);

    std::cout << "[Alice Shared Secret]: "; secret_alice.print_hex(); std::cout << "\n";
    std::cout << "[Bob   Shared Secret]: "; secret_bob.print_hex(); std::cout << "\n";
    std::cout << "ECDH Status: " << ((secret_alice == secret_bob) ? "KEYS MATCH (SUCCESS)" : "ERROR") << "\n\n";

    // 2. ECDSA SIGN / VERIFY
    std::cout << "--- 2. ECDSA DIGITAL SIGNATURE ---\n";
    UInt256 msg_hash = UInt256::from_hex("4BC564148C32F103DAA8D137F53232157037ACD7B7043BEA73BC401FB2E917B3");
    UInt256 k_ephem = UInt256::from_hex("A61211A7BB3E57662B609F70C5420A41AC3E7938BD9B02E760A39C1DA6D427F6");

    CryptoProtocols::Signature sig = CryptoProtocols::ecdsa_sign(msg_hash, dA, k_ephem, curve);
    std::cout << "[Signature] r: "; sig.r.print_hex(); std::cout << "\n";
    std::cout << "[Signature] s: "; sig.s.print_hex(); std::cout << "\n";

    bool valid = CryptoProtocols::ecdsa_verify(msg_hash, alice.pub, sig, curve);
    std::cout << "Signature verification: " << (valid ? "VALID (SUCCESS)" : "INVALID") << "\n\n";

    // 3. CORRUPTION TEST
    std::cout << "--- 3. CORRUPTION TEST (ALTERING S PARAMETER) ---\n";
    CryptoProtocols::Signature corrupted_sig = sig;
    corrupted_sig.s.d[0] ^= 0xFF;

    std::cout << "[Corrupted Sig] s: "; corrupted_sig.s.print_hex(); std::cout << "\n";
    bool corrupted_valid = CryptoProtocols::ecdsa_verify(msg_hash, alice.pub, corrupted_sig, curve);
    std::cout << "Corrupted signature verification: "
        << (corrupted_valid ? "ERROR: ACCEPTED" : "REJECTED (EXPECTED)") << "\n";
    std::cout << "========================================================\n";

    return 0;
}