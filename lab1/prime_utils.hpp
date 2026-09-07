#ifndef PRIME_UTILS_HPP
#define PRIME_UTILS_HPP

#include <cstdint>
#include <vector>
#include "sg_generator.hpp"

// Модульное возведение в степень (a^e mod m)
int mod_pow(int a, int e, int m);

// Тест Леманна (вероятностный)
bool isPrimeLehmann(int n, int k);


bool trialDivision(int n, const std::vector<int>& primes);


int generatePrime(int bits, SGGenerator& sg, int lehmannIterations,
                       int& candidatesTested);

// для предварительной фильтрации
extern const std::vector<int> SMALL_PRIMES;

#endif