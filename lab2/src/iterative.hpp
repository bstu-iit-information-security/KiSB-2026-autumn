#pragma once
#include "linear_code.hpp"

enum class Group { Horizontal, Vertical, Depth, DiagonalSum, DiagonalDiff };

inline const char* group_name(Group g) {
    switch (g) {
    case Group::Horizontal:   return "X_h (строки)";
    case Group::Vertical:     return "X_v (столбцы)";
    case Group::Depth:        return "X_z (по оси z)";
    case Group::DiagonalSum:  return "X_d1 (диагонали i+j)";
    case Group::DiagonalDiff: return "X_d2 (диагонали j-i)";
    }
    return "?";
}

// Слово X_k записывается построчно в матрицу k1 x k2, плоскости идут по оси z.
struct Layout {
    int k1, k2, z;
    int groups;

    int index(int plane, int row, int col) const { return plane * k1 * k2 + row * k2 + col; }

    // Порядок групп: в двумерной матрице h, v, диагонали; в трёхмерной третья — ось z.
    Group group(int g) const {
        static const Group flat[] = {Group::Horizontal, Group::Vertical, Group::DiagonalSum, Group::DiagonalDiff};
        static const Group cube[] = {Group::Horizontal, Group::Vertical, Group::Depth, Group::DiagonalSum,
                                     Group::DiagonalDiff};
        return z == 1 ? flat[g] : cube[g];
    }
};

// Табл. 5.2, вариант 8 - 5 = 3, k = 24. В методичке третья строка 3 x 3 x 4 (= 36) —
// опечатка, принято 3 x 2 x 4.
struct VariantRow {
    int k1, k2, z;
    int group_options[4];
    int option_count;
};
constexpr VariantRow kVariant[] = {
    {4, 6, 1, {2, 3}, 2},
    {3, 8, 1, {2, 3}, 2},
    {3, 2, 4, {2, 3, 4, 5}, 4},
    {6, 2, 2, {2, 3, 4, 5}, 4},
};

struct IterativeCode {
    Layout layout{};
    LinearCode code;
    std::array<int, 5> first{};  // первая строка H каждой группы
    std::array<int, 5> size{};   // число проверок в группе
};

inline void build_iterative(IterativeCode& ic, const Layout& L) {
    ic = IterativeCode{};
    ic.layout = L;
    LinearCode& c = ic.code;
    c.k = L.k1 * L.k2 * L.z;
    const int diagonals = L.k1 + L.k2 - 1;

    int check = 0;
    for (int g = 0; g < L.groups; ++g) {
        ic.first[g] = check;
        const Group type = L.group(g);
        if (type == Group::Depth) {
            for (int row = 0; row < L.k1; ++row)
                for (int col = 0; col < L.k2; ++col, ++check)
                    for (int p = 0; p < L.z; ++p) c.H[check][L.index(p, row, col)] = 1;
        } else {
            for (int p = 0; p < L.z; ++p) {
                if (type == Group::Horizontal)
                    for (int row = 0; row < L.k1; ++row, ++check)
                        for (int col = 0; col < L.k2; ++col) c.H[check][L.index(p, row, col)] = 1;
                if (type == Group::Vertical)
                    for (int col = 0; col < L.k2; ++col, ++check)
                        for (int row = 0; row < L.k1; ++row) c.H[check][L.index(p, row, col)] = 1;
                if (type == Group::DiagonalSum || type == Group::DiagonalDiff)
                    for (int d = 0; d < diagonals; ++d, ++check)
                        for (int row = 0; row < L.k1; ++row) {
                            const int col = type == Group::DiagonalSum ? d - row : d - (L.k1 - 1) + row;
                            if (col >= 0 && col < L.k2) c.H[check][L.index(p, row, col)] = 1;
                        }
            }
        }
        ic.size[g] = check - ic.first[g];
    }
    c.r = check;
    c.n = c.k + c.r;
    c.fill_identity_part();
}
