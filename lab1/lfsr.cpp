#include "lfsr.hpp"

LFSR::LFSR(int degree, int polyMask, int initState)
    : n(degree), mask(polyMask), state(initState) {
    if (state == 0) state = 1;
}

int LFSR::nextBit() {
    int feedback = 0;
    for (int i = 0; i < n; ++i) {
        if (mask & (1u << i)) {
            feedback ^= ((state >> i) & 1);
        }
    }
    state = (state >> 1) | (feedback << (n - 1));
    return state & 1;
}

int LFSR::getState() const { return state; }

bool isPrimitive(int degree, int polyMask) {
    LFSR lfsr(degree, polyMask, 1);
    int initState = 1;
    int period = 0;
    do {
        lfsr.nextBit();
        period++;
    } while (lfsr.getState() != initState && period < (1u << degree));
    return period == (1u << degree) - 1;
}