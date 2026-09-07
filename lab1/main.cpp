#include "lfsr.hpp"
#include "sg_generator.hpp"
#include "prime_utils.hpp"

#include <iostream>
#include <chrono>

using namespace std;

int main() {
    cout << "Lab work #1, Variant 2\n\n";

    //Часть 1 LFSR и SG-генератор
    int deg7 = 7;
    const int polyMasks[] = {15, 3, 9};
    const char* polyNames[] = {
        "x^7 + x^3 + x^2 + x + 1",
        "x^7 + x + 1",
        "x^7 + x^3 + 1"
    };

    cout << "1. Primitiveness check of degree-7 polynomials:\n";
    for (int i = 0; i < 3; ++i) {
        bool prim = isPrimitive(deg7, polyMasks[i]);
        cout << "   " << polyNames[i] << " -> "
                  << (prim ? "primitive" : "NOT primitive") << endl;
    }

    // полином для G1 (x^7 + x + 1) и G2 (x^5 + x^2 + 1)
    int maskG1 = 3;
    int deg2 = 5;
    int maskG2 = 5;
    if (!isPrimitive(deg2, maskG2)) {
        cerr << "Warning: chosen G2 polynomial is not primitive!" << endl;
    }

    int init1 = 85;
    int init2 = 25;
    SGGenerator sg(deg7, maskG1, deg2, maskG2, init1, init2);

    const int SAMPLE_BITS = 10000;
    int ones = 0;
    for (int i = 0; i < SAMPLE_BITS; ++i) {
        if (sg.nextBit() == 1) ones++;
    }
    double freq = static_cast<double>(ones) / SAMPLE_BITS;
    cout << "\n2. SG-generator statistics (after " << SAMPLE_BITS << " bits):\n";
    cout << "   ones = " << ones << ", frequency = " << freq
              << " (expected ~0.5)\n";

    // Часть 2: генерация простого числа с тестом Леманна
    cout << "\n3. Generating a 16-bit prime using Lehmann test (5 iterations):\n";
    int bits = 16;
    int lehmannIter = 5;
    int candidates = 0;

    auto start = chrono::high_resolution_clock::now();
    int prime = generatePrime(bits, sg, lehmannIter, candidates);
    auto end = chrono::high_resolution_clock::now();
    chrono::duration<double> elapsed = end - start;

    cout << "   Found prime: " << prime << endl;
    cout << "   Candidates tested before success: " << candidates << endl;
    cout << "   Time elapsed: " << elapsed.count() << " seconds\n";

    //проверка
    cout << "\n   Additional deterministic check (trial division up to sqrt):\n";
    bool definitelyPrime = true;
    for (int d = 2; d * d <= prime; ++d) {
        if (prime % d == 0) {
            definitelyPrime = false;
            break;
        }
    }
    cout << "   " << (definitelyPrime ? "The number is indeed prime."
                                           : "Error: composite!") << endl;

    return 0;
}