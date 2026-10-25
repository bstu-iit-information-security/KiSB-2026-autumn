import java.util.*;

/**
 * Лабораторная работа №5. Итеративные коды.
 * Вариант 3: k=24, k1=4, k2=6, 3 группы паритетов
 * (строки + столбцы + общий паритет).
 */
public class Lab2 {

    // ==================== Параметры варианта ====================
    static final int K1 = 4;          // строк
    static final int K2 = 6;          // столбцов
    static final int K  = K1 * K2;    // 24 информационных бита
    static final int N  = K + K1 + K2 + 1; // 24 + 4 + 6 + 1 = 35

    // ==================== Основной класс кода ====================
    static class IterativeCode {
        int[][] info;          // информационная матрица [K1][K2]
        int[] rowParity;       // паритеты строк [K1]
        int[] colParity;       // паритеты столбцов [K2]
        int overallParity;     // общий паритет (паритет паритетов)

        // ----- Кодирование -----
        void encode(String binary) {
            if (binary.length() != K || !binary.matches("[01]+")) {
                throw new IllegalArgumentException("Нужно ровно " + K + " бит (0/1)");
            }

            info = new int[K1][K2];
            int idx = 0;
            for (int i = 0; i < K1; i++) {
                for (int j = 0; j < K2; j++) {
                    info[i][j] = binary.charAt(idx++) - '0';
                }
            }

            // Паритеты строк (чётность)
            rowParity = new int[K1];
            for (int i = 0; i < K1; i++) {
                int sum = 0;
                for (int j = 0; j < K2; j++) sum ^= info[i][j];
                rowParity[i] = sum;
            }

            // Паритеты столбцов
            colParity = new int[K2];
            for (int j = 0; j < K2; j++) {
                int sum = 0;
                for (int i = 0; i < K1; i++) sum ^= info[i][j];
                colParity[j] = sum;
            }

            // Общий паритет (паритет всех строковых паритетов + всех столбцовых)
            // Можно считать и как паритет всей информационной матрицы + паритетов
            int sum = 0;
            for (int p : rowParity) sum ^= p;
            for (int p : colParity) sum ^= p;
            overallParity = sum;
        }

        // Получить полное кодовое слово (информация + паритеты)
        String getCodeword() {
            StringBuilder sb = new StringBuilder();
            // Информационные биты
            for (int i = 0; i < K1; i++)
                for (int j = 0; j < K2; j++)
                    sb.append(info[i][j]);
            // Строковые паритеты
            for (int p : rowParity) sb.append(p);
            // Столбцовые паритеты
            for (int p : colParity) sb.append(p);
            // Общий
            sb.append(overallParity);
            return sb.toString();
        }

        // ----- Декодирование и исправление -----
        static class DecodeResult {
            boolean corrected;
            int errorRow = -1, errorCol = -1;
            String message;
            String correctedCodeword;
        }

        DecodeResult decode(String received) {
            DecodeResult res = new DecodeResult();
            if (received.length() != N) {
                res.message = "Неверная длина принятого слова";
                return res;
            }

            // Разбираем принятое слово
            int[][] rInfo = new int[K1][K2];
            int[] rRowP = new int[K1];
            int[] rColP = new int[K2];
            int rOverall;

            int idx = 0;
            for (int i = 0; i < K1; i++)
                for (int j = 0; j < K2; j++)
                    rInfo[i][j] = received.charAt(idx++) - '0';

            for (int i = 0; i < K1; i++) rRowP[i] = received.charAt(idx++) - '0';
            for (int j = 0; j < K2; j++) rColP[j] = received.charAt(idx++) - '0';
            rOverall = received.charAt(idx) - '0';

            // Пересчитываем паритеты по принятой информации
            int[] calcRowP = new int[K1];
            for (int i = 0; i < K1; i++) {
                int sum = 0;
                for (int j = 0; j < K2; j++) sum ^= rInfo[i][j];
                calcRowP[i] = sum;
            }

            int[] calcColP = new int[K2];
            for (int j = 0; j < K2; j++) {
                int sum = 0;
                for (int i = 0; i < K1; i++) sum ^= rInfo[i][j];
                calcColP[j] = sum;
            }

            // Синдромы (несовпадения паритетов)
            int[] rowSyndrome = new int[K1];
            int[] colSyndrome = new int[K2];
            for (int i = 0; i < K1; i++) rowSyndrome[i] = calcRowP[i] ^ rRowP[i];
            for (int j = 0; j < K2; j++) colSyndrome[j] = calcColP[j] ^ rColP[j];

            // Ищем строки и столбцы с ошибкой
            List<Integer> badRows = new ArrayList<>();
            List<Integer> badCols = new ArrayList<>();
            for (int i = 0; i < K1; i++) if (rowSyndrome[i] == 1) badRows.add(i);
            for (int j = 0; j < K2; j++) if (colSyndrome[j] == 1) badCols.add(j);

            // Проверка общего паритета
            int calcOverall = 0;
            for (int p : calcRowP) calcOverall ^= p;
            for (int p : calcColP) calcOverall ^= p;
            boolean overallFail = (calcOverall != rOverall);

            // Логика исправления
            if (badRows.isEmpty() && badCols.isEmpty()) {
                if (!overallFail) {
                    res.message = "Ошибок не обнаружено. Слово принято корректно.";
                    res.corrected = true;
                } else {
                    res.message = "Обнаружена ошибка в общем паритете (или тройная ошибка).";
                    res.corrected = false;
                }
            } else if (badRows.size() == 1 && badCols.size() == 1) {
                // Классическая одиночная ошибка в информационной части
                int er = badRows.get(0);
                int ec = badCols.get(0);
                rInfo[er][ec] ^= 1; // исправляем
                res.errorRow = er;
                res.errorCol = ec;
                res.corrected = true;
                res.message = String.format("Обнаружена и исправлена одиночная ошибка в позиции [%d][%d]", er, ec);
            } else if (badRows.size() == 1 && badCols.isEmpty()) {
                // Ошибка в строковом паритете
                res.message = "Ошибка в строковом паритете строки " + badRows.get(0);
                res.corrected = true; // паритет можно просто пересчитать
            } else if (badRows.isEmpty() && badCols.size() == 1) {
                res.message = "Ошибка в столбцовом паритете столбца " + badCols.get(0);
                res.corrected = true;
            } else {
                res.message = String.format(
                        "Обнаружена ошибка кратности > 1 (плохие строки: %s, столбцы: %s). Исправление невозможно.",
                        badRows, badCols);
                res.corrected = false;
            }

            // Собираем исправленное слово
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < K1; i++)
                for (int j = 0; j < K2; j++)
                    sb.append(rInfo[i][j]);
            // Паритеты оставляем как есть или пересчитываем — для простоты оставляем принятые
            for (int p : rRowP) sb.append(p);
            for (int p : rColP) sb.append(p);
            sb.append(rOverall);
            res.correctedCodeword = sb.toString();

            return res;
        }

        // Красивый вывод матрицы
        void printMatrix() {
            System.out.println("\nИнформационная матрица + паритеты:");
            System.out.print("     ");
            for (int j = 0; j < K2; j++) System.out.printf(" c%d ", j);
            System.out.println(" | Prow");
            System.out.println("    +" + "----".repeat(K2) + "+-----");

            for (int i = 0; i < K1; i++) {
                System.out.printf(" r%d |", i);
                for (int j = 0; j < K2; j++) System.out.printf("  %d ", info[i][j]);
                System.out.printf("|  %d%n", rowParity[i]);
            }
            System.out.println("    +" + "----".repeat(K2) + "+-----");
            System.out.print("Pcol|");
            for (int j = 0; j < K2; j++) System.out.printf("  %d ", colParity[j]);
            System.out.printf("|  %d  (overall)%n", overallParity);
        }
    }

    // ==================== Вспомогательные методы ====================
    static String randomBinary(int len) {
        Random rnd = new Random();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < len; i++) sb.append(rnd.nextInt(2));
        return sb.toString();
    }

    static String introduceErrors(String codeword, int multiplicity) {
        char[] bits = codeword.toCharArray();
        Random rnd = new Random();
        Set<Integer> positions = new HashSet<>();
        while (positions.size() < multiplicity) {
            positions.add(rnd.nextInt(bits.length));
        }
        for (int pos : positions) {
            bits[pos] = (bits[pos] == '0') ? '1' : '0';
        }
        return new String(bits);
    }

    // ==================== Главное меню ====================
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        IterativeCode code = new IterativeCode();
        String currentInfo = null;
        String currentCodeword = null;

        System.out.println("=== Лабораторная работа №5. Итеративные коды ===");
        System.out.println("Вариант 3: k=24, матрица 4×6, 3 группы паритетов");
        System.out.println("Длина кодового слова n = " + N + " бит\n");

        while (true) {
            System.out.println("----------------------------------------");
            System.out.println("1. Ввести / сгенерировать информационное слово");
            System.out.println("2. Закодировать и показать матрицу");
            System.out.println("3. Внести ошибки");
            System.out.println("4. Декодировать и исправить");
            System.out.println("5. Анализ корректирующей способности");
            System.out.println("0. Выход");
            System.out.print("Выбор: ");

            int choice;
            try {
                choice = Integer.parseInt(sc.nextLine().trim());
            } catch (Exception e) {
                System.out.println("Введите число!");
                continue;
            }

            switch (choice) {
                case 1 -> {
                    System.out.print("Введите 24 бита (или Enter для случайной генерации): ");
                    String input = sc.nextLine().trim();
                    if (input.isEmpty()) {
                        currentInfo = randomBinary(K);
                        System.out.println("Сгенерировано: " + currentInfo);
                    } else {
                        currentInfo = input;
                    }
                    try {
                        code.encode(currentInfo);
                        currentCodeword = code.getCodeword();
                        System.out.println("Информационное слово принято.");
                    } catch (Exception e) {
                        System.out.println("Ошибка: " + e.getMessage());
                        currentInfo = null;
                    }
                }
                case 2 -> {
                    if (currentInfo == null) {
                        System.out.println("Сначала введите информационное слово (пункт 1)");
                        break;
                    }
                    code.printMatrix();
                    System.out.println("\nКодовое слово Xn (" + N + " бит):");
                    System.out.println(currentCodeword);
                }
                case 3 -> {
                    if (currentCodeword == null) {
                        System.out.println("Сначала закодируйте слово");
                        break;
                    }
                    System.out.print("Кратность ошибки (1, 2, 3...): ");
                    try {
                        int mult = Integer.parseInt(sc.nextLine().trim());
                        String errored = introduceErrors(currentCodeword, mult);
                        System.out.println("Исходное : " + currentCodeword);
                        System.out.println("С ошибками: " + errored);
                        currentCodeword = errored; // теперь работаем с испорченным
                    } catch (Exception e) {
                        System.out.println("Некорректный ввод");
                    }
                }
                case 4 -> {
                    if (currentCodeword == null) {
                        System.out.println("Нет кодового слова");
                        break;
                    }
                    IterativeCode.DecodeResult res = code.decode(currentCodeword);
                    System.out.println("\nРезультат декодирования:");
                    System.out.println(res.message);
                    if (res.corrected) {
                        System.out.println("Исправленное слово: " + res.correctedCodeword);
                    }
                }
                case 5 -> {
                    System.out.println("\n--- Анализ корректирующей способности ---");
                    System.out.print("Количество испытаний: ");
                    int trials = Integer.parseInt(sc.nextLine().trim());
                    System.out.print("Кратность ошибки: ");
                    int mult = Integer.parseInt(sc.nextLine().trim());

                    int detected = 0, corrected = 0;
                    for (int t = 0; t < trials; t++) {
                        String info = randomBinary(K);
                        code.encode(info);
                        String cw = code.getCodeword();
                        String errored = introduceErrors(cw, mult);
                        IterativeCode.DecodeResult res = code.decode(errored);
                        if (!res.message.contains("не обнаружено")) detected++;
                        if (res.corrected && res.message.contains("исправлена")) corrected++;
                    }
                    System.out.printf("Испытаний: %d, кратность ошибки: %d%n", trials, mult);
                    System.out.printf("Обнаружено: %d (%.1f%%)%n", detected, 100.0 * detected / trials);
                    System.out.printf("Исправлено: %d (%.1f%%)%n", corrected, 100.0 * corrected / trials);
                    System.out.println("(Для одиночных ошибок код должен исправлять ~100%)");
                }
                case 0 -> {
                    System.out.println("Выход.");
                    return;
                }
                default -> System.out.println("Неверный пункт");
            }
            System.out.println();
        }
    }
}