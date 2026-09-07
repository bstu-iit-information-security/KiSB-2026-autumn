#ifndef LFSR_HPP
#define LFSR_HPP

#include <cstdint>

// Линейный регистр сдвига с обратной связью (LFSR)
class LFSR {
private:
    int state;   // текущее состояние (биты регистра)
    int mask;    // битовая маска коэффициентов (x^0..x^(n-1))
    int n;            // степень полинома (длина регистра)

public:
    LFSR(int degree, int polyMask, int initState);

    int nextBit();

    int getState() const;
    void setState(int s);
};


bool isPrimitive(int degree, int polyMask);

#endif 