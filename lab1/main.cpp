#include "lfsr.hpp"
#include "sg_generator.hpp"
#include "prime_utils.hpp"

#include <iostream>
#include <chrono>

using namespace std;

int main() {
    cout << "Lab work #1, Variant 2\n\n";

    // LFSR и SG-генератор
    const int g1Degree = 7;
    const int polyMasks[] = {15, 3, 9};
    const char* polyNames[] = {
        "x^7 + x^3 + x^2 + x + 1",
        "x^7 + x + 1",
        "x^7 + x^3 + 1"
    };

    cout << "1. Primitiveness check of degree-7 polynomials:\n";
    for (int i = 0; i < 3; ++i) {
        const bool primitive = isPrimitive(g1Degree, polyMasks[i]);
        LFSR lfsr(g1Degree, polyMasks[i], 1);
        cout << "   " << polyNames[i] << " -> "
             << (primitive ? "primitive" : "NOT primitive")
             << ", period = " << lfsr.getPeriod() << endl;
    }

    // Для SG G1 = x^7 + x + 1 и G2 = x^5 + x^2 + 1.
    const int g1Mask = polyMasks[1];
    const int g2Degree = 5;
    const int g2Mask = 5;
    if (!isPrimitive(g2Degree, g2Mask)) {
        cerr << "Warning: chosen G2 polynomial is not primitive!" << endl;
    }

    const int g1InitialState = 85;
    const int g2InitialState = 25;

    const int sampleBits = 10000;
    cout << "\n2. SG-generator statistics for different G1 polynomials:\n";
    cout << "   polynomial                          zeros  ones  ones frequency\n";
    for (int i = 0; i < 3; ++i) {
        SGGenerator testGenerator(
            g1Degree, polyMasks[i], g2Degree, g2Mask,
            g1InitialState, g2InitialState);
        int ones = 0;
        for (int bit = 0; bit < sampleBits; ++bit) {
            if (testGenerator.nextBit() == 1) {
                ++ones;
            }
        }
           const double onesFrequency = static_cast<double>(ones) / sampleBits;
           cout << "   " << polyNames[i] << "  "
               << (sampleBits - ones) << "  " << ones << "  "
               << onesFrequency << endl;
    }

    SGGenerator sg(g1Degree, g1Mask, g2Degree, g2Mask,
                   g1InitialState, g2InitialState);

    // Часть 2: генерация простого числа с тестом Леманна
    cout << "\n3. Generating a 16-bit prime using Lehmann test (5 iterations):\n";
    int bits = 16;
    int lehmannIter = 5;
    int candidates = 0;
    int filteredCandidates = 0;

    auto start = chrono::high_resolution_clock::now();
    int prime = generatePrime(bits, sg, lehmannIter, candidates,
                              filteredCandidates);
    auto end = chrono::high_resolution_clock::now();
    chrono::duration<double> elapsed = end - start;

    cout << "   Found prime: " << prime << endl;
    cout << "   Candidates tested before success: " << candidates << endl;
        cout << "   Candidates rejected by small-prime filtering: "
            << filteredCandidates << endl;
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