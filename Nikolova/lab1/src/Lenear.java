package Part1;

import java.util.Arrays;

public class Lenear {

    public static void main(String[] args) {
        int N = 15;

        System.out.println("1. Мультипликативный генератор Лемера (c = 0)");

        testMultiplicative(1, 2, N, 10000);

        System.out.println("\n2. Смешанный генератор (c != 0), теорема Халла-Доббелла");

        testMixed(0, 16, 4, N, 10000);

        System.out.println("\n3. Смешанный генератор с параметрами (для сравнения)");
        testMixed(0, 3, 3, N, 10000);
    }


    public static void testMultiplicative(int x0, int a, int N, int count) {
        int[] sequence = generate(x0, a, 0, N, count);
        System.out.println("Первые 20 элементов: " + Arrays.toString(Arrays.copyOf(sequence, 20)));

        int period = findPeriod(x0, a, 0, N);
        int lambda = carmichaelLambda(N);
        boolean primitiveRootExists = (lambda == eulerPhi(N));

        System.out.println("Период генератора: " + period);
        System.out.println("Функция Кармайкла lambda(" + N + ") = " + lambda
                + (primitiveRootExists ? " (совпадает с phi(N), первообразные корни существуют)"
                : " (первообразных корней по модулю " + N + " не существует, "
                + "т.к. " + N + " не имеет вида 2, 4, p^k или 2*p^k)"));
        System.out.println("=> Теоретически достижимый максимум периода для МКГ: " + lambda);

        checkChiSquare(sequence, N, period);
    }


    public static void testMixed(int x0, int a, int c, int N, int count) {
        int[] sequence = generate(x0, a, c, N, count);
        System.out.println("Первые 20 элементов: " + Arrays.toString(Arrays.copyOf(sequence, 20)));

        int period = findPeriod(x0, a, c, N);
        System.out.println("Период генератора: " + period + " (макс. возможный : " + N + ")");

        HullDobellResult check = checkHullDobell(a, c, N);
        System.out.println("Проверка условий :");
        System.out.println("  a) НОД(c, N) = 1 : " + check.gcdOk);
        System.out.println("  b) (a-1) кратно всем простым делителям N : " + check.primeFactorsOk);
        System.out.println("  c) (a-1) кратно 4, если N кратно 4 : " + check.mod4Ok
                + (N % 4 != 0 ? " (условие неприменимо, N не кратно 4)" : ""));
        System.out.println("  ИТОГ: условия теоремы " + (check.allOk ? "ВЫПОЛНЕНЫ -> ожидается T = N"
                : "НЕ выполнены -> период короче N"));

        checkChiSquare(sequence, N, period);
    }


    public static int[] generate(int x0, int a, int c, int N, int count) {
        int[] sequence = new int[count];
        int current = x0;
        for (int i = 0; i < count; i++) {
            current = (a * current + c) % N;
            sequence[i] = current;
        }
        return sequence;
    }


    public static int findPeriod(int x0, int a, int c, int N) {
        int slow = (a * x0 + c) % N;
        int fast = (a * ((a * x0 + c) % N) + c) % N;

        while (slow != fast) {
            slow = (a * slow + c) % N;
            fast = (a * ((a * fast + c) % N) + c) % N;
        }

        int steps = 1;
        fast = (a * slow + c) % N;
        while (slow != fast) {
            fast = (a * fast + c) % N;
            steps++;
        }
        return steps;
    }


    public static void checkChiSquare(int[] sequence, int N, int period) {
        int[] frequencies = new int[N];
        for (int val : sequence) {
            frequencies[val]++;
        }

        double expected = (double) sequence.length / N;
        double chiSquare = 0.0;
        for (int i = 0; i < N; i++) {
            double diff = frequencies[i] - expected;
            chiSquare += (diff * diff) / expected;
        }


        double criticalValue = 23.685;

        System.out.println("Частоты выпадения символов [0.." + (N - 1) + "]: " + Arrays.toString(frequencies));
        System.out.printf("Значение Хи-квадрат (наблюдаемое): %.3f\n", chiSquare);
        System.out.println("Критическое значение (alpha=0.05, df=14): " + criticalValue);

        if (chiSquare <= criticalValue) {
            System.out.println("ИТОГ: Гипотеза о равномерном распределении ПОДТВЕРЖДАЕТСЯ.");
        } else {
            System.out.println("ИТОГ: Гипотеза о равномерном распределении ОТКЛОНЯЕТСЯ.");
            if (period < N) {
                System.out.println("Пояснение: период генератора (" + period + ") меньше размера алфавита ("
                        + N + "), поэтому последовательность физически не может принимать все "
                        + N + " значений - отклонение гипотезы здесь ОЖИДАЕМО, а не свидетельствует об ошибке.");
            }
        }
    }



    private static int gcd(int x, int y) {
        return y == 0 ? x : gcd(y, x % y);
    }


    private static int eulerPhi(int N) {
        int result = N;
        int n = N;
        for (int p = 2; (long) p * p <= n; p++) {
            if (n % p == 0) {
                while (n % p == 0) n /= p;
                result -= result / p;
            }
        }
        if (n > 1) result -= result / n;
        return result;
    }


    private static int carmichaelLambda(int N) {
        int n = N;
        int lambda = 1;
        for (int p = 2; (long) p * p <= n; p++) {
            if (n % p == 0) {
                int exp = 0;
                while (n % p == 0) { n /= p; exp++; }
                int pk = (int) Math.pow(p, exp);
                int lambdaPk;
                if (p == 2 && exp >= 3) {
                    lambdaPk = pk / 4;
                } else {
                    lambdaPk = pk - pk / p;
                }
                lambda = lcm(lambda, lambdaPk);
            }
        }
        if (n > 1) {
            lambda = lcm(lambda, n - 1);
        }
        return lambda;
    }

    private static int lcm(int x, int y) {
        return x / gcd(x, y) * y;
    }


    private static java.util.List<Integer> primeFactors(int N) {
        java.util.List<Integer> factors = new java.util.ArrayList<>();
        int n = N;
        for (int p = 2; (long) p * p <= n; p++) {
            if (n % p == 0) {
                factors.add(p);
                while (n % p == 0) n /= p;
            }
        }
        if (n > 1) factors.add(n);
        return factors;
    }

    private static class HullDobellResult {
        boolean gcdOk, primeFactorsOk, mod4Ok, allOk;
    }


    private static HullDobellResult checkHullDobell(int a, int c, int N) {
        HullDobellResult r = new HullDobellResult();
        r.gcdOk = gcd(c, N) == 1;

        r.primeFactorsOk = true;
        for (int p : primeFactors(N)) {
            if ((a - 1) % p != 0) {
                r.primeFactorsOk = false;
                break;
            }
        }

        r.mod4Ok = (N % 4 != 0) || ((a - 1) % 4 == 0);

        r.allOk = r.gcdOk && r.primeFactorsOk && r.mod4Ok;
        return r;
    }
}