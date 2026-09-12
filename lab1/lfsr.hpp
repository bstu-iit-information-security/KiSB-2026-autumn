#ifndef LFSR_HPP
#define LFSR_HPP

#include <cstdint>

class LFSR {
private:
    int state; // текущее состояние регистра
    int mask;  // коэффициенты полинома для обратной связи
    int n;     // длина регистра

public:
    LFSR(int degree, int polyMask, int initState);

    
    int nextBit();

    int getState() const;

    int getPeriod() const;
};


bool isPrimitive(int degree, int polyMask);

#endif 