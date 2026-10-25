import java.util.*;

public class lab1p1 {

    public static int modInverse(int val, int n) {
        int a = val;
        int b = Math.abs(n);
        int u1 = 1;
        int u2 = 0;
        while (a > 0) {
            int q = b / a; // частное
            int remainder = b % a; // остаток
            int uNext = u2 - q * u1;
            b = a;
            a = remainder;
            u2 = u1;
            u1 = uNext;
        }
        if (b > 1) {
            return 0;
        }
        if (u2 < 0) {
            u2 += Math.abs(n);
        }
        return u2;
    }

    public static ArrayList<Integer> generator(int paramA, int paramC, int paramN, int x0, int sLength) {
        int currentX = x0;
        ArrayList<Integer> subsequence = new ArrayList<>();
        for (int i = 0; i < sLength; i++) {
            subsequence.add(currentX);
            if (currentX == 0) {
                currentX = paramC;
            } else {
                int invertX = modInverse(currentX, paramN);

                if (invertX == 0) {
                    currentX = paramC % paramN;
                } else {
                    currentX = (paramA * invertX + paramC) % paramN;
                }
            }
        }
        return subsequence;
    }

    public static void periodTest(ArrayList<Integer> subsequence) {
        System.out.println("Последовательность: " + subsequence);
        int x0 = subsequence.get(0);
        boolean found = false;
        for (int i = 1; i < subsequence.size(); i++) {
            if (x0 == subsequence.get(i)) {
                System.out.println("Период = " + i);
                found = true;
                break;
            }
        }
        if (!found) {
            System.out.println("Период не обнаружен");
        }
    }

    public static void frequencyTest(ArrayList<Integer> subsequence) {
        if (subsequence == null || subsequence.size() < 2) {
            System.out.println("Недостаточно элементов для анализа пар (нужно минимум 2).");
            return;
        }

        Map<String, Integer> pairMap = new HashMap<>();

        int totalPairs = subsequence.size() - 1;

        for (int i = 0; i < totalPairs; i++) {
            int current = subsequence.get(i);
            int next = subsequence.get(i + 1);

            String pairKey = current + "->" + next;
            pairMap.put(pairKey, pairMap.getOrDefault(pairKey, 0) + 1);
        }

        System.out.println("Частоты пар (текущее -> следующее): " + pairMap);

        double sumDiff = 0;
        for (int i = 0; i < totalPairs; i++) {
            sumDiff += (subsequence.get(i + 1) - subsequence.get(i));
        }
        double avgDiff = sumDiff / totalPairs;
        System.out.println("Средняя разность переходов (Next - Curr): " + avgDiff);

        double varianceSum = 0;
        for (int i = 0; i < totalPairs; i++) {
            double diff = subsequence.get(i + 1) - subsequence.get(i);
            varianceSum += Math.pow(diff - avgDiff, 2);
        }
        double variance = varianceSum / totalPairs;
        System.out.println("Дисперсия разностей переходов: " + variance);
    }

    /**
     * Метод проверки равномерности распределения по критерию Пирсона (Хи-квадрат)
     * @param subsequence сгенерированная последовательность чисел
     * @param paramN модуль N (верхняя граница диапазона генератора)
     * @param numIntervals количество интервалов разбиения (например, 8)
     */
    public static void checkChiSquare(ArrayList<Integer> subsequence, int paramN, int numIntervals) {
        System.out.println("\n=== КРИТЕРИЙ ХИ-КВАДРАТ (Проверка на равномерность) ===");
        int totalElements = subsequence.size();
        int[] observed = new int[numIntervals];
        double intervalWidth = (double) paramN / numIntervals;

        // 1. Подсчет количества попаданий в каждый интервал
        for (int num : subsequence) {
            int index = (int) (num / intervalWidth);
            if (index >= numIntervals) {
                index = numIntervals - 1; // Защита от вылета за границы массива
            }
            observed[index]++;
        }

        // 2. Вычисление теоретической частоты попадания
        double expected = (double) totalElements / numIntervals;

        // 3. Вычисление эмпирического значения хи-квадрат
        double chiSquare = 0.0;
        System.out.println("Распределение элементов по интервалам:");
        for (int i = 0; i < numIntervals; i++) {
            double diff = observed[i] - expected;
            chiSquare += (diff * diff) / expected;
            System.out.printf("  Интервал %d [%3.0f - %3.0f]: получено = %3d, ожидалось = %.1f\n",
                    i + 1, i * intervalWidth, (i + 1) * intervalWidth - 1, observed[i], expected);
        }

        System.out.printf("\nНаблюдаемое значение Chi-Square (хи-квадрат): %.4f\n", chiSquare);

        // 4. Сравнение с критическим значением для alpha = 0.05 и df = numIntervals - 1
        if (numIntervals == 8) {
            double criticalValue = 14.07; // Критическое значение для df = 7 при alpha = 0.05
            System.out.println("Критическое значение Chi-Square (alpha = 0.05, df = 7): " + criticalValue);

            if (chiSquare < criticalValue) {
                System.out.println("РЕЗУЛЬТАТ: Гипотеза о равномерности ПОДТВЕРЖДАЕТСЯ (хи-квадрат < " + criticalValue + ")");
            } else {
                System.out.println("РЕЗУЛЬТАТ: Гипотеза о равномерности ОТКЛОНЯЕТСЯ (хи-квадрат >= " + criticalValue + ")");
            }
        }
    }

    public static void main(String[] args) {
        int paramN = 16;
        ArrayList<Integer> subsequence = generator(9, 14, paramN, 1, 100);

        periodTest(subsequence);
        frequencyTest(subsequence);

        // Запуск проверки на равномерность (8 интервалов)
        checkChiSquare(subsequence, paramN, 8);
    }
}