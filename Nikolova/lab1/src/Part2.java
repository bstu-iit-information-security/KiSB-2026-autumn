package Part2;

import java.math.BigInteger;
import java.util.Random;

public class Part2 {

    private static final int[] SMALL_PRIMES = {
            2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79,
            83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167,
            173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251
    };


    private static long lcgState = System.nanoTime() & 0xFFL;
    private static final long A = 1664525;
    private static final long C = 1013904223;
    private static final long N = 256;

    private static int nextLcgByte() {
        lcgState = (A * lcgState + C) % N;
        return (int) lcgState;
    }


    public static BigInteger findPrime(int bitLength, int iterationsK) {
        System.out.println("Поиск простого числа (Тест Лемана)");
        System.out.println("Разрядность: " + bitLength + " бит, Количество проверок (k): " + iterationsK);

        long startTime = System.currentTimeMillis();
        int totalCandidates = 0;
        int filteredBySmallPrimes = 0;
        int failedLehmann = 0;

        while (true) {
            totalCandidates++;


            BigInteger candidate = generateCandidate(bitLength);


            if (!isPassedTrialDivision(candidate)) {
                filteredBySmallPrimes++;
                continue;
            }


            if (isPassedLehmannTest(candidate, iterationsK)) {
                long elapsedTime = System.currentTimeMillis() - startTime;

                System.out.println("\n--- РЕЗУЛЬТАТ НАЙДЕН ---");
                System.out.println("Сгенерированное простое число n: " + candidate);
                System.out.println("Всего проверено: " + totalCandidates);
                System.out.println("Отсеяно на этапе просеивания: " + filteredBySmallPrimes +
                        String.format(" (%.1f%%)", (filteredBySmallPrimes * 100.0 / totalCandidates)));
                System.out.println("Отбраковано тестом Лемана: " + failedLehmann);
                System.out.println("Время работы: " + elapsedTime + " мс");
                return candidate;
            } else {
                failedLehmann++;
            }
        }
    }


    public static void main(String[] args) {
        findPrime(64, 5);
    }


    public static BigInteger generateCandidate(int bitLength) {
        byte[] bytes = new byte[(bitLength + 7) / 8];
        for (int i = 0; i < bytes.length; i++) {
            bytes[i] = (byte) (nextLcgByte() & 0xFF);
        }
        BigInteger n = new BigInteger(1, bytes);

        n = n.setBit(bitLength - 1);
        n = n.setBit(0);

        return n;
    }


    public static boolean isPassedTrialDivision(BigInteger n) {
        for (int p : SMALL_PRIMES) {
            BigInteger bigP = BigInteger.valueOf(p);
            if (n.equals(bigP)) return true;
            if (n.mod(bigP).equals(BigInteger.ZERO)) return false;
        }
        return true;
    }


    public static boolean isPassedLehmannTest(BigInteger n, int k) {
        if (n.compareTo(BigInteger.valueOf(3)) <= 0) return n.compareTo(BigInteger.ONE) > 0;

        BigInteger nMinusOne = n.subtract(BigInteger.ONE);
        BigInteger exponent = nMinusOne.divide(BigInteger.valueOf(2));
        BigInteger negativeOne = nMinusOne;

        Random rng = new Random();
        boolean hasMinusOne = false;

        for (int i = 0; i < k; i++) {
            BigInteger a;
            do {
                a = new BigInteger(n.bitLength(), rng);
            } while (a.compareTo(BigInteger.ONE) <= 0 || a.compareTo(n) >= 0);

            BigInteger t = a.modPow(exponent, n);

            if (!t.equals(BigInteger.ONE) && !t.equals(negativeOne)) {
                return false;
            }

            if (t.equals(negativeOne)) {
                hasMinusOne = true;
            }
        }


        return hasMinusOne;
    }
}