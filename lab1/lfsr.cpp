#include "lfsr.hpp"

#include <stdexcept>

LFSR::LFSR(int degree, int polyMask, int initState)
    : state(initState), mask(polyMask), n(degree) {
    if (degree < 1 || degree > 30) {
        throw std::invalid_argument("LFSR degree must be between 1 and 30");
    }
    if (polyMask < 0 || (static_cast<unsigned int>(polyMask) >> degree) != 0) {
        throw std::invalid_argument("LFSR polynomial mask does not fit degree");
    }

    const int stateMask = (1u << degree) - 1;
    state &= stateMask;
    if (state == 0) {
        throw std::invalid_argument("LFSR initial state must not be zero");
    }
}

int LFSR::nextBit() {
    int feedback = 0;
    for (int i = 0; i < n; ++i) {
        if ((mask & (1u << i)) != 0) {
            feedback ^= ((state >> i) & 1);
        }
    }
    state = (state >> 1) | (feedback << (n - 1));
    return state & 1;
}

int LFSR::getState() const { return state; }

int LFSR::getPeriod() const {
    LFSR copy = *this;
    const int initialState = copy.getState();
    int period = 0;
    const int maxStates = 1u << n;

    do {
        copy.nextBit();
        ++period;
    } while (copy.getState() != initialState && period < maxStates);

    return period;
}

bool isPrimitive(int degree, int polyMask) {
    LFSR lfsr(degree, polyMask, 1);
    return lfsr.getPeriod() == (1u << degree) - 1;
}