#include "prime_utils.hpp"

#include <stdexcept>

int mod_pow(int base, int exponent, int modulus) {
    long long result = 1;
    long long currentBase = base % modulus;
    while (exponent > 0) {
        if (exponent & 1) result = (result * currentBase) % modulus;
        currentBase = (currentBase * currentBase) % modulus;
        exponent >>= 1;
    }
    return static_cast<int>(result);
}

bool isPrimeLehmann(int number, int iterations, SGGenerator& generator) {
    if (number < 2) return false;
    if (number == 2 || number == 3) return true;
    if (number % 2 == 0) return false;

    for (int iteration = 0; iteration < iterations; ++iteration) {
        const int base = 2 + generator.generateNumber(16) % (number - 3);
        const int residue = mod_pow(base, (number - 1) / 2, number);
        if (residue != 1 && residue != number - 1) {
            return false;
        }
    }
    return true;
}

bool trialDivision(int number, const int primes[], int primeCount) {
    for (int i = 0; i < primeCount; ++i) {
        const int prime = primes[i];
        if (number == prime) return true;
        if (prime * prime > number) break;
        if (number % prime == 0) return false;
    }
    return true;
}

const int SMALL_PRIMES[] = {
    2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,
    101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,191,
    193,197,199,211,223,227,229,233,239,241,251
};
const int SMALL_PRIMES_COUNT = sizeof(SMALL_PRIMES) / sizeof(SMALL_PRIMES[0]);

int generatePrime(int bitCount, SGGenerator& generator, int lehmannIterations,
                  int& candidatesTested, int& filteredCandidates) {
    if (bitCount < 2 || bitCount > 30) {
        throw std::invalid_argument("Prime size must be between 2 and 30 bits");
    }

    candidatesTested = 0;
    filteredCandidates = 0;
    while (true) {
        int candidate = generator.generateNumber(bitCount);
        candidate |= 1;
        candidate |= (1 << (bitCount - 1));
        candidatesTested++;

        if (!trialDivision(candidate, SMALL_PRIMES, SMALL_PRIMES_COUNT)) {
            filteredCandidates++;
            continue;
        }

        if (isPrimeLehmann(candidate, lehmannIterations, generator)) {
            return candidate;
        }
    }
}