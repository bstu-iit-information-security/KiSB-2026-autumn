import java.math.BigInteger;

public class lab1p2gen2 {

    // 1. Генератор Эйхенауэра-Лена с обращением (модуль N = 2^16)
    public static int modInverse(int val, int n) {
        int a = val, b = n;
        int u1 = 1, u2 = 0;
        while (a > 0) {
            int q = b / a;
            int remainder = b % a;
            int uNext = u2 - q * u1;
            b = a; a = remainder;
            u2 = u1; u1 = uNext;
        }
        if (b > 1) return 0;
        return (u2 < 0) ? u2 + n : u2;
    }

    public static int nextEichenauerLehn(int currentX, int paramA, int paramC, int paramN) {
        if (currentX == 0) {
            return paramC % paramN;
        }
        int inv = modInverse(currentX, paramN);
        if (inv == 0) {
            return (paramA * (currentX + 1) + paramC) % paramN;
        }
        return (paramA * inv + paramC) % paramN;
    }

    // Генерация p-битного кандидата
    public static BigInteger generateCandidate(int bits, int paramA, int paramC, int paramN, int[] stateX) {
        BigInteger number = BigInteger.ZERO;
        for (int i = 0; i < bits; i++) {
            stateX[0] = nextEichenauerLehn(stateX[0], paramA, paramC, paramN);
            int bit = (stateX[0] > (paramN / 2)) ? 1 : 0;
            if (bit == 1) {
                number = number.setBit(i);
            }
        }
        // Установка старшего и младшего битов в 1
        number = number.setBit(bits - 1);
        number = number.setBit(0);
        return number;
    }

    // 2. Список малых простых чисел для сита (< 256)
    private static final int[] PRIMES = {
            2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
            73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
            157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
            239, 241, 251
    };

    /**
     * Фильтрация ситом малых простых чисел.
     * Возвращает делитель, если число составное, или -1, если прошло сито.
     */
    public static int getSieveDivisor(BigInteger n) {
        for (int p : PRIMES) {
            BigInteger num = BigInteger.valueOf(p);
            if (n.equals(num)) return -1; // Число само является простым
            if (n.mod(num).equals(BigInteger.ZERO)) {
                return p; // Нашли малый делитель
            }
        }
        return -1; // Прошло сито
    }

    // 3. Полиномиальный тест простоты (AKS / Теорема 3)
    public static BigInteger[] multiplyPoly(BigInteger[] poly1, BigInteger[] poly2, int r, BigInteger n) {
        BigInteger[] result = new BigInteger[r];
        for (int i = 0; i < r; i++) result[i] = BigInteger.ZERO;

        for (int i = 0; i < r; i++) {
            if (poly1[i].equals(BigInteger.ZERO)) continue;
            for (int j = 0; j < r; j++) {
                if (poly2[j].equals(BigInteger.ZERO)) continue;

                int targetIndex = (i + j) % r;
                BigInteger term = poly1[i].multiply(poly2[j]).mod(n);
                result[targetIndex] = result[targetIndex].add(term).mod(n);
            }
        }
        return result;
    }

    public static BigInteger[] polyPow(BigInteger[] base, BigInteger exponent, int r, BigInteger n) {
        BigInteger[] result = new BigInteger[r];
        for (int i = 0; i < r; i++) result[i] = BigInteger.ZERO;
        result[0] = BigInteger.ONE;

        BigInteger[] curBase = base;
        BigInteger exp = exponent;

        while (exp.compareTo(BigInteger.ZERO) > 0) {
            if (exp.testBit(0)) {
                result = multiplyPoly(result, curBase, r, n);
            }
            curBase = multiplyPoly(curBase, curBase, r, n);
            exp = exp.shiftRight(1);
        }
        return result;
    }

    public static boolean isPrimeSimple(BigInteger n) {
        if (n.compareTo(BigInteger.TWO) < 0) return false;
        BigInteger limit = n.sqrt();
        for (BigInteger d = BigInteger.TWO; d.compareTo(limit) <= 0; d = d.add(BigInteger.ONE)) {
            if (n.mod(d).equals(BigInteger.ZERO)) return false;
        }
        return true;
    }

    public static BigInteger getLargestPrimeFactor(BigInteger num) {
        BigInteger maxPrime = BigInteger.valueOf(-1);
        BigInteger temp = num;
        BigInteger two = BigInteger.valueOf(2);

        while (temp.mod(two).equals(BigInteger.ZERO)) {
            maxPrime = two;
            temp = temp.divide(two);
        }

        BigInteger i = BigInteger.valueOf(3);
        while (i.multiply(i).compareTo(temp) <= 0) {
            while (temp.mod(i).equals(BigInteger.ZERO)) {
                maxPrime = i;
                temp = temp.divide(i);
            }
            i = i.add(two);
        }
        if (temp.compareTo(two) > 0) maxPrime = temp;
        return maxPrime;
    }

    public static boolean aksTest(BigInteger n) {
        if (n.compareTo(BigInteger.ONE) <= 0) return false;

        // Шаг 0: Пробные деления
        for (int p : PRIMES) {
            BigInteger num = BigInteger.valueOf(p);
            if (n.equals(num)) return true;
            if (n.mod(num).equals(BigInteger.ZERO)) return false;
        }

        // Шаг 1: Проверка на совершенную степень (n = a^b)
        int maxB = n.bitLength();
        for (int b = 2; b <= maxB; b++) {
            BigInteger low = BigInteger.valueOf(2), high = n;
            while (low.compareTo(high) <= 0) {
                BigInteger mid = low.add(high).shiftRight(1);
                BigInteger res = mid.pow(b);
                int cmp = res.compareTo(n);
                if (cmp == 0) return false;
                if (cmp < 0) low = mid.add(BigInteger.ONE);
                else high = mid.subtract(BigInteger.ONE);
            }
        }

        // Шаги 2–7: Поиск r
        BigInteger r = BigInteger.valueOf(2);
        double log2n = n.bitLength();

        while (r.compareTo(n) < 0) {
            if (!n.gcd(r).equals(BigInteger.ONE)) return false;

            if (isPrimeSimple(r)) {
                BigInteger rMinus1 = r.subtract(BigInteger.ONE);
                BigInteger q = getLargestPrimeFactor(rMinus1);

                double threshold = 4 * Math.sqrt(r.doubleValue()) * log2n;
                if (q.doubleValue() > threshold) {
                    BigInteger exp = rMinus1.divide(q);
                    if (!n.modPow(exp, r).equals(BigInteger.ONE)) {
                        break;
                    }
                }
            }
            r = r.add(BigInteger.ONE);
        }

        if (r.equals(n)) return true;

        // Шаги 9–10: Полиномиальная проверка
        int rInt = r.intValue();
        long limit = (long) (2 * Math.sqrt(rInt) * log2n);

        for (int a = 1; a <= limit; a++) {
            BigInteger bigA = BigInteger.valueOf(a);

            BigInteger[] basePoly = new BigInteger[rInt];
            for (int i = 0; i < rInt; i++) basePoly[i] = BigInteger.ZERO;
            basePoly[1] = BigInteger.ONE;
            basePoly[0] = n.subtract(bigA).mod(n);

            BigInteger[] leftPoly = polyPow(basePoly, n, rInt, n);

            BigInteger[] rightPoly = new BigInteger[rInt];
            for (int i = 0; i < rInt; i++) rightPoly[i] = BigInteger.ZERO;
            rightPoly[0] = n.subtract(bigA).mod(n);
            int nModR = n.mod(r).intValue();
            rightPoly[nModR] = rightPoly[nModR].add(BigInteger.ONE).mod(n);

            for (int i = 0; i < rInt; i++) {
                if (!leftPoly[i].equals(rightPoly[i])) return false;
            }
        }

        return true;
    }

    public static void main(String[] args) {
        int bits = 12; // Для AKS битовость 12-16 оптимальна
        int paramA = 9;
        int paramC = 14;
        int paramN = 65536;
        int[] stateX = {(int) (System.currentTimeMillis() % paramN)};
        if (stateX[0] % 2 == 0) stateX[0]++;

        System.out.println("=== ПОИСК ПРОСТОГО ЧИСЛА (Полиномиальный тест AKS) ===");
        BigInteger candidate = generateCandidate(bits, paramA, paramC, paramN, stateX);
        System.out.println("Сгенерированный начальный кандидат: " + candidate + "\n");

        int rejectedBySieve = 0;
        int rejectedByAKS = 0;
        long startTime = System.currentTimeMillis();

        while (true) {
            int sieveDivisor = getSieveDivisor(candidate);

            if (sieveDivisor != -1) {
                // Число отсеяно ситом
                System.out.println("[СИТО] Отсеян кандидат: " + candidate + " (делится на " + sieveDivisor + ")");
                rejectedBySieve++;
                candidate = candidate.add(BigInteger.TWO);
                continue;
            }

            // Кандидат прошел предварительное сито
            System.out.println("\n[-->] Кандидат " + candidate + " прошел сито, запускаем тест AKS...");

            if (aksTest(candidate)) {
                long endTime = System.currentTimeMillis();
                System.out.println("\n=================================================");
                System.out.println(" УСПЕХ! Найдено простое число: " + candidate);
                System.out.println("=================================================");
                System.out.println(" Отсеяно ситом     : " + rejectedBySieve);
                System.out.println(" Отсеяно тестом AKS: " + rejectedByAKS);
                System.out.println(" Время поиска      : " + (endTime - startTime) + " ms");
                System.out.println("=================================================");
                break;
            } else {
                System.out.println("[AKS]  Кандидат " + candidate + " отсеян тестом AKS (составное)\n");
                rejectedByAKS++;
                candidate = candidate.add(BigInteger.TWO);
            }
        }
    }
}