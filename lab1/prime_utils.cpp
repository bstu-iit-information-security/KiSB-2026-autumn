#include "prime_utils.hpp"
#include "sg_generator.hpp"

#include <random>
#include <cmath>

using namespace std;

int mod_pow(int a, int e, int m) {
    int res = 1;
    a %= m;
    while (e > 0) {
        if (e & 1) res = (res * a) % m;
        a = (a * a) % m;
        e >>= 1;
    }
    return res;
}

bool isPrimeLehmann(int n, int k) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0) return false;

    static random_device rd;
    static mt19937_64 gen(rd());
    uniform_int_distribution<int> dis(2, n - 2);

    for (int i = 0; i < k; ++i) {
        int a = dis(gen);
        int t = mod_pow(a, (n - 1) / 2, n);
        if (t != 1 && t != n - 1) {
            return false;
        }
    }
    return true;
}

bool trialDivision(int n, const int primes[], int primeCount) {
    for (int i = 0; i < primeCount; ++i) {
        int p = primes[i];
        if (p * p > n) break;
        if (n % p == 0) return false;
    }
    return true;
}

const int SMALL_PRIMES[] = {
    2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,
    101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,191,
    193,197,199,211,223,227,229,233,239,241,251
};
const int SMALL_PRIMES_COUNT = sizeof(SMALL_PRIMES) / sizeof(SMALL_PRIMES[0]);

int generatePrime(int bits, SGGenerator& sg, int lehmannIterations,
                       int& candidatesTested) {
    candidatesTested = 0;
    while (true) {
        int n = sg.generateNumber(bits);
        n |= 1ULL;
        n |= (1ULL << (bits - 1));
        candidatesTested++;

        if (!trialDivision(n, SMALL_PRIMES, SMALL_PRIMES_COUNT)) {
            continue;
        }

        if (isPrimeLehmann(n, lehmannIterations)) {
            return n;
        }
    }
}