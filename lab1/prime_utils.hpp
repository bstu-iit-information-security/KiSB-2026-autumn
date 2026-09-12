#ifndef PRIME_UTILS_HPP
#define PRIME_UTILS_HPP

#include "sg_generator.hpp"

// a^e mod m
int mod_pow(int base, int exponent, int modulus);

// Леманна
bool isPrimeLehmann(int number, int iterations, SGGenerator& generator);

bool trialDivision(int number, const int primes[], int primeCount);

int generatePrime(int bitCount, SGGenerator& generator, int lehmannIterations,
                  int& candidatesTested, int& filteredCandidates);

// для предварительной фильтрации
extern const int SMALL_PRIMES[];
extern const int SMALL_PRIMES_COUNT;

#endif