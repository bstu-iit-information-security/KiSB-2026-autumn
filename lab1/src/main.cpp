#include <iostream>
#include <vector>
#include <random>
#include <cmath>
#include <chrono>
#include <windows.h>
#include <algorithm>
#include <numeric>

using namespace std;

class Fibonacci {
private:
    long long x0, x1, N;
public:
    Fibonacci(long long x0, long long x1, long long mod) : x0(x0), x1(x1), N(mod) {}

    vector<long long> generate(int length) {
        vector<long long> seq;
        for (int i = 0; i < length; i++) {
            long long next = (x0 + x1) % N;
            seq.push_back(next);

            x0 = x1;
            x1 = next;
        }

        return seq;
    }

    vector<long long> generate1(int length) {
        vector<long long> seq;
        for (int i = 0; i < length; i++) {
            long long next = (x0 + x1) % N;
            seq.push_back(next);

            x0 = x1;
            x1 = next;
        }

        float M = accumulate(seq.begin(), seq.end(), 0LL) / seq.size();
        cout << "МАТ ОЖ " << M << endl;
        float D = 0;
        for(int i = 0; i < seq.size(); i++){
            D += pow((M - seq[i]), 2);
        } 
        D /= seq.size();
        cout << "ДИСП " << D << endl;

        auto minE = *min_element(seq.begin(), seq.end());
        auto maxE = *max_element(seq.begin(), seq.end());

        cout << "РАВНОМЕРНОЕ МАТ ОЖ " << (minE + maxE) / 2 << endl;
        cout << "РАВНОМЕРНОЕ ДИСП " << pow(minE - maxE, 2) / 12 << endl;


        return seq;
    }
};

long long power_mod(long long base, long long exp, long long mod) {
    long long res = 1;
    base = base % mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % mod;
        base = (base * base) % mod;
        exp /= 2;
    }
    return res;
}

long long nod(long long a, long long b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

bool miller_rabin(long long n, int k) {
    if (n <= 1 || n == 4) return false;
    if (n <= 3) return true;

    long long t = n - 1;
    int s = 0;
    while (t % 2 == 0) {
        t /= 2;
        s++;
    }

    random_device rd;
    mt19937_64 gen(rd());

    for (int i = 0; i < k; i++) {
        long long a = 1 + (gen() % (n - 1));

        if (nod(a, n) != 1) {
            return false;
        }

        long long x = power_mod(a, t, n);

        if (x == 1 || x == n - 1) {
            continue;
        }

        bool is_composite = true;
        for (int r = 1; r < s; r++) {
            x = (x * x) % n;
            if (x == n - 1) {
                is_composite = false;
                break;
            }
        }

        if (is_composite) {
            return false;
        }
    }
    return true;
}

bool check_small_primes(long long n) {
    int primes[] = {3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,
                    83,89,97,101,103,107,109,113,127,131,137,139,149,151,157,
                    163,167,173,179,181,191,193,197,199,211,223,227,229,233,239,
                    241,251};
                    
    for (int p : primes) {
        if (n % p == 0) {
            return false; 
        }
    }
    return true; 
}

long long generate_prime(int p_bits, Fibonacci& gen, int& total_tested, int& small_prime_rejected, double& test_time_ms) {
    total_tested = 0;
    small_prime_rejected = 0;
    test_time_ms = 0.0; 

    while (true) {
        total_tested++;
        long long candidate = 0;
        vector<long long> bits = gen.generate(p_bits);
        
        for (int i = 0; i < p_bits; i++) {
            candidate = (candidate << 1) | (bits[i] % 2);
        }
        
        candidate |= (1LL << (p_bits - 1));
        candidate |= 1LL;

    
        auto start_test = chrono::high_resolution_clock::now();

        if (!check_small_primes(candidate)) {
            auto end_test = chrono::high_resolution_clock::now();
            test_time_ms += chrono::duration<double, milli>(end_test - start_test).count();
            
            small_prime_rejected++;
            continue;
        }

        bool is_prime = miller_rabin(candidate, 5);
        
        auto end_test = chrono::high_resolution_clock::now();
        test_time_ms += chrono::duration<double, milli>(end_test - start_test).count();
    
        if (is_prime) {
            return candidate;
        }
    }
}

int main() {
    SetConsoleOutputCP(CP_UTF8);

    Fibonacci gen(1234, 6890, 100007);
    int bit_length = 30;
    
    int total = 0, filtered = 0;
    double test_time_ms = 0.0; 
    
    vector<long long> ans = gen.generate1(100000);
    long long prime = generate_prime(bit_length, gen, total, filtered, test_time_ms);
    
    cout << "Простое число: " << prime << endl;
    cout << "Всего сгенерировано кандидатов: " << total << endl;
    cout << "Отсеяно малые простые числа: " << filtered << " (" << (filtered * 100.0 / total) << "%)" << endl;
    cout << "Отсеяно тестом Рабина-Миллера: " << (total - filtered - 1) << endl;
    cout << "Время работы критериев (фильтрация + Рабин-Миллер): " << test_time_ms << " мс" << endl;
    cout << "---------------------------------------------------" << endl;
    
    return 0;
}