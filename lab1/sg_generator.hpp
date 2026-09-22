#ifndef SG_GENERATOR_HPP
#define SG_GENERATOR_HPP

#include "lfsr.hpp"

// SG-генератор: G1 – основной, G2 – селектор
class SGGenerator {
private:
    LFSR G1, G2;

public:
    SGGenerator(int deg1, int poly1, int deg2, int poly2,
                int init1, int init2);

    // очередной бит выходной последовательности
    int nextBit();

    // из выходной последовательности
    int generateNumber(int bits);
};

#endif