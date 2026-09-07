#include "sg_generator.hpp"

SGGenerator::SGGenerator(int deg1, int poly1, int deg2, int poly2,
                         int init1, int init2)
    : G1(deg1, poly1, init1), G2(deg2, poly2, init2) {}

int SGGenerator::nextBit() {
    while (true) {
        int b1 = G1.nextBit();
        int b2 = G2.nextBit();
        if (b2 == 1) {
            return b1;
        }
    }
}

int SGGenerator::generateNumber(int bits) {
    int num = 0;
    for (int i = 0; i < bits; ++i) {
        num = (num << 1) | nextBit();
    }
    return num;
}