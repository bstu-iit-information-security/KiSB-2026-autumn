import java.util.*;


public class Lab2p1 {

    static class HammingCode {
        int k;          // длина информационной части
        int r;          // количество проверочных бит
        int n;          // общая длина кодового слова (n = k + r)
        int[][] H;      // проверочная матрица r × n
        int[][] G;      // порождающая матрица k × n (для справки)

        /**
         * Конструктор: подбирает минимальное r для заданного k
         * и строит систематическую проверочную матрицу.
         */
        HammingCode(int infoLength) {
            this.k = infoLength;
            // Ищем минимальное r: 2^r >= k + r + 1
            r = 1;
            while ((1 << r) < k + r + 1) {
                r++;
            }
            n = k + r;

            buildParityCheckMatrix();
            // buildGeneratorMatrix(); // можно раскомментировать при необходимости
        }

        /**
         * Строим проверочную матрицу H в систематической форме:
         * H = [P | I_r]
         * Столбцы — все различные ненулевые двоичные векторы длины r,
         * последние r столбцов образуют единичную матрицу.
         */
        private void buildParityCheckMatrix() {
            H = new int[r][n];

            // Сначала заполняем единичную матрицу в конце (позиции k ... n-1)
            for (int i = 0; i < r; i++) {
                H[i][k + i] = 1;
            }

            // Теперь заполняем первые k столбцов различными ненулевыми векторами,
            // которые ещё не использованы (не являются базисными векторами единичной матрицы)
            List<int[]> used = new ArrayList<>();
            for (int i = 0; i < r; i++) {
                int[] e = new int[r];
                e[i] = 1;
                used.add(e);
            }

            int col = 0;
            for (int num = 1; num < (1 << r) && col < k; num++) {
                int[] vec = new int[r];
                for (int b = 0; b < r; b++) {
                    vec[b] = (num >> b) & 1;
                }

                // Проверяем, не является ли этот вектор уже использованным (единичным)
                boolean isUsed = false;
                for (int[] u : used) {
                    if (Arrays.equals(u, vec)) {
                        isUsed = true;
                        break;
                    }
                }
                if (!isUsed) {
                    for (int i = 0; i < r; i++) {
                        H[i][col] = vec[i];
                    }
                    used.add(vec);
                    col++;
                }
            }
        }

        /**
         * Кодирование: systematic form
         * Информационные биты идут первыми, проверочные — в конце.
         * Проверочные биты вычисляются так, чтобы H * c^T = 0
         */
        String encode(String infoBits) {
            if (infoBits.length() != k || !infoBits.matches("[01]+")) {
                throw new IllegalArgumentException("Нужно ровно " + k + " бит (0/1)");
            }

            int[] c = new int[n];
            // Копируем информационные биты
            for (int i = 0; i < k; i++) {
                c[i] = infoBits.charAt(i) - '0';
            }

            // Вычисляем проверочные биты (последние r позиций)
            // Из условия H * c^T = 0 → для каждой строки H:
            // sum(H[i][j] * c[j]) = 0  (mod 2)
            // → c[k+i] = sum(H[i][j] * c[j]) для j = 0..k-1
            for (int i = 0; i < r; i++) {
                int sum = 0;
                for (int j = 0; j < k; j++) {
                    sum ^= H[i][j] * c[j];
                }
                c[k + i] = sum;
            }

            StringBuilder sb = new StringBuilder();
            for (int bit : c) sb.append(bit);
            return sb.toString();
        }

        /**
         * Вычисление синдрома S = H * y^T
         */
        int[] calculateSyndrome(String received) {
            int[] y = new int[n];
            for (int i = 0; i < n; i++) {
                y[i] = received.charAt(i) - '0';
            }

            int[] syndrome = new int[r];
            for (int i = 0; i < r; i++) {
                int sum = 0;
                for (int j = 0; j < n; j++) {
                    sum ^= H[i][j] * y[j];
                }
                syndrome[i] = sum;
            }
            return syndrome;
        }

        /**
         * Декодирование по синдрому
         */
        static class DecodeResult {
            boolean hasError;
            boolean corrected;
            int errorPosition = -1;     // позиция ошибки (0-based), -1 если нет
            String syndromeStr;
            String correctedWord;
            String message;
        }

        DecodeResult decode(String received) {
            DecodeResult res = new DecodeResult();
            if (received.length() != n) {
                res.message = "Неверная длина принятого слова";
                return res;
            }

            int[] syndrome = calculateSyndrome(received);
            res.syndromeStr = Arrays.toString(syndrome).replaceAll("[\\[\\], ]", "");

            // Если синдром нулевой — ошибок нет
            boolean allZero = true;
            for (int s : syndrome) {
                if (s != 0) {
                    allZero = false;
                    break;
                }
            }

            if (allZero) {
                res.hasError = false;
                res.corrected = true;
                res.correctedWord = received;
                res.message = "Синдром нулевой. Ошибок не обнаружено.";
                return res;
            }

            res.hasError = true;

            // Ищем столбец матрицы H, который совпадает с синдромом
            // Номер этого столбца = позиция ошибки
            for (int col = 0; col < n; col++) {
                boolean match = true;
                for (int i = 0; i < r; i++) {
                    if (H[i][col] != syndrome[i]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    res.errorPosition = col;
                    break;
                }
            }

            if (res.errorPosition != -1) {
                // Исправляем ошибку
                char[] bits = received.toCharArray();
                bits[res.errorPosition] = (bits[res.errorPosition] == '0') ? '1' : '0';
                res.correctedWord = new String(bits);
                res.corrected = true;
                res.message = String.format(
                        "Обнаружена одиночная ошибка в позиции %d (нумерация с 0). Исправлено.",
                        res.errorPosition);
            } else {
                // Синдром не совпал ни с одним столбцом → двойная (или большей кратности) ошибка
                res.corrected = false;
                res.correctedWord = received;
                res.message = "Синдром ненулевой, но не соответствует ни одному столбцу H. " +
                        "Вероятно, произошла ошибка кратности ≥ 2. Исправление невозможно.";
            }

            return res;
        }

        // Красивый вывод матрицы H
        void printH() {
            System.out.println("\nПроверочная матрица H (" + r + " × " + n + "):");
            for (int i = 0; i < r; i++) {
                for (int j = 0; j < n; j++) {
                    System.out.print(H[i][j] + " ");
                    if (j == k - 1) System.out.print("| "); // граница информационных и проверочных
                }
                System.out.println();
            }
            System.out.println("(левая часть — P, правая — единичная матрица I_r)");
        }

        void printParameters() {
            System.out.printf("Параметры кода: (n, k, r) = (%d, %d, %d), d_min = 3%n", n, k, r);
            System.out.printf("Скорость кода R = k/n = %.3f%n", (double) k / n);
            System.out.printf("Может исправлять t = %d ошибку, обнаруживать до %d ошибок%n",
                    1, 2);
        }
    }

    // ==================== Вспомогательные методы ====================
    static String textToBinary(String text) {
        StringBuilder sb = new StringBuilder();
        for (char c : text.toCharArray()) {
            String bin = Integer.toBinaryString(c);
            // Дополняем до 8 бит (ASCII)
            while (bin.length() < 8) bin = "0" + bin;
            sb.append(bin);
        }
        return sb.toString();
    }

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
        while (positions.size() < multiplicity && positions.size() < bits.length) {
            positions.add(rnd.nextInt(bits.length));
        }
        System.out.print("Инвертированы позиции: ");
        for (int pos : positions) {
            bits[pos] = (bits[pos] == '0') ? '1' : '0';
            System.out.print(pos + " ");
        }
        System.out.println();
        return new String(bits);
    }

    // ==================== Главное меню ====================
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        HammingCode code = null;
        String currentInfo = null;
        String currentCodeword = null;

        System.out.println("=== Лабораторная работа №4. Код Хемминга ===");
        System.out.println("Часть 1 лабораторной работы №2\n");

        while (true) {
            System.out.println("----------------------------------------");
            System.out.println("1. Ввести информационное сообщение (текст или биты)");
            System.out.println("2. Показать параметры кода и матрицу H");
            System.out.println("3. Закодировать");
            System.out.println("4. Внести ошибки (0, 1 или 2)");
            System.out.println("5. Декодировать (вычислить синдром и исправить)");
            System.out.println("6. Полный пример (текст → код → ошибка → исправление)");
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
                    System.out.println("Выберите способ ввода:");
                    System.out.println("  a) Текст (будет переведён в ASCII-биты)");
                    System.out.println("  b) Двоичная строка");
                    System.out.println("  c) Случайная двоичная строка заданной длины");
                    System.out.print("Ваш выбор (a/b/c): ");
                    String mode = sc.nextLine().trim().toLowerCase();

                    String bits;
                    if (mode.equals("a")) {
                        System.out.print("Введите текст (не меньше 2-3 символов): ");
                        String text = sc.nextLine();
                        bits = textToBinary(text);
                        System.out.println("Двоичное представление (" + bits.length() + " бит):");
                        System.out.println(bits);
                    } else if (mode.equals("b")) {
                        System.out.print("Введите двоичную строку: ");
                        bits = sc.nextLine().trim();
                    } else {
                        System.out.print("Длина в битах (≥ 16): ");
                        int len = Integer.parseInt(sc.nextLine().trim());
                        bits = randomBinary(len);
                        System.out.println("Сгенерировано: " + bits);
                    }

                    if (bits.length() < 16) {
                        System.out.println("Внимание: по заданию желательно ≥ 16 бит. Продолжаем...");
                    }
                    if (!bits.matches("[01]+")) {
                        System.out.println("Ошибка: только символы 0 и 1!");
                        break;
                    }

                    currentInfo = bits;
                    code = new HammingCode(bits.length());
                    System.out.println("Информационное слово принято. Параметры кода пересчитаны.");
                    code.printParameters();
                }
                case 2 -> {
                    if (code == null) {
                        System.out.println("Сначала введите информационное слово (пункт 1)");
                        break;
                    }
                    code.printParameters();
                    code.printH();
                }
                case 3 -> {
                    if (code == null || currentInfo == null) {
                        System.out.println("Сначала введите информационное слово");
                        break;
                    }
                    try {
                        currentCodeword = code.encode(currentInfo);
                        System.out.println("Информационное слово (" + code.k + " бит):");
                        System.out.println(currentInfo);
                        System.out.println("\nКодовое слово Xn (" + code.n + " бит):");
                        System.out.println(currentCodeword);
                        System.out.println("(первые " + code.k + " бит — информационные, последние " + code.r + " — проверочные)");
                    } catch (Exception e) {
                        System.out.println("Ошибка кодирования: " + e.getMessage());
                    }
                }
                case 4 -> {
                    if (currentCodeword == null) {
                        System.out.println("Сначала закодируйте слово (пункт 3)");
                        break;
                    }
                    System.out.print("Кратность ошибки (0, 1 или 2): ");
                    try {
                        int mult = Integer.parseInt(sc.nextLine().trim());
                        if (mult < 0 || mult > 2) {
                            System.out.println("Рекомендуется 0–2. Продолжаем...");
                        }
                        String errored = introduceErrors(currentCodeword, mult);
                        System.out.println("Исходное : " + currentCodeword);
                        System.out.println("С ошибками: " + errored);
                        currentCodeword = errored;
                    } catch (Exception e) {
                        System.out.println("Некорректный ввод");
                    }
                }
                case 5 -> {
                    if (code == null || currentCodeword == null) {
                        System.out.println("Нет данных для декодирования");
                        break;
                    }
                    HammingCode.DecodeResult res = code.decode(currentCodeword);
                    System.out.println("\n--- Результат декодирования ---");
                    System.out.println("Синдром S = " + res.syndromeStr);
                    System.out.println(res.message);
                    if (res.corrected && res.hasError) {
                        System.out.println("Исправленное слово: " + res.correctedWord);
                    }
                }
                case 6 -> {
                    // Полный демонстрационный прогон
                    System.out.print("Введите короткий текст для демонстрации: ");
                    String text = sc.nextLine();
                    String bits = textToBinary(text);
                    System.out.println("\n1. Информационные биты (" + bits.length() + " шт.): " + bits);

                    code = new HammingCode(bits.length());
                    code.printParameters();
                    code.printH();

                    String cw = code.encode(bits);
                    System.out.println("\n2. Закодированное слово: " + cw);

                    System.out.println("\n3. Вносим одну случайную ошибку:");
                    String errored = introduceErrors(cw, 1);
                    System.out.println("   Принято: " + errored);

                    System.out.println("\n4. Декодирование:");
                    HammingCode.DecodeResult res = code.decode(errored);
                    System.out.println("   Синдром: " + res.syndromeStr);
                    System.out.println("   " + res.message);
                    if (res.corrected) {
                        System.out.println("   После исправления: " + res.correctedWord);
                        // Проверяем, совпало ли с исходным
                        if (res.correctedWord.equals(cw)) {
                            System.out.println("   ✓ Успешно восстановлено исходное кодовое слово!");
                        }
                    }
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