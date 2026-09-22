#include "sg_generator.hpp"

#include <stdexcept>

SGGenerator::SGGenerator(int deg1, int poly1, int deg2, int poly2,
                         int init1, int init2)
    : G1(deg1, poly1, init1), G2(deg2, poly2, init2) {
    LFSR selector = G2;
    const int initialState = selector.getState();
    const unsigned int maxStates = 1u << deg2;
    bool emitsOne = false;
    bool returnsToInitialState = false;

    for (unsigned int step = 0; step < maxStates; ++step) {
        if (selector.nextBit() == 1) emitsOne = true;
        if (selector.getState() == 0) break;
        if (selector.getState() == initialState) {
            returnsToInitialState = true;
            break;
        }
    }

    if (!returnsToInitialState || !emitsOne) {
        throw std::invalid_argument(
            "SG selector must have a non-zero cycle that emits 1");
    }
}

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
    if (bits < 1 || bits > 30) {
        throw std::invalid_argument("Number size must be between 1 and 30 bits");
    }

    int num = 0;
    for (int i = 0; i < bits; ++i) {
        num = (num << 1) | nextBit();
    }
    return num;
}