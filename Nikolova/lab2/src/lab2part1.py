import random

ENCODING = "cp1251"


def read_message():
    """Сообщение из текстового файла или с клавиатуры (не меньше 2 символов)."""
    while True:
        path = input("Имя текстового файла (Enter - ввести вручную): ").strip()
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read().strip("\r\n")
            except (OSError, UnicodeDecodeError) as e:
                print("Не удалось прочитать файл:", e)
                continue
        else:
            text = input("Сообщение (не меньше 2 символов): ")

        if len(text) < 2:
            print("Сообщение должно содержать не меньше 2 символов.")
            continue
        try:
            text.encode(ENCODING)
        except UnicodeEncodeError:
            print("В сообщении есть символы, которых нет в кодировке", ENCODING)
            continue
        return text


def read_dmin():
    while True:
        s = input("d_min (3 или 4): ").strip()
        if s in ("3", "4"):
            return int(s)
        print("Нужно ввести 3 или 4.")


def to_bits(text):
    bits = []
    for b in text.encode(ENCODING):
        for c in format(b, "08b"):
            bits.append(int(c))
    return bits


def build_h(k, dmin):
    """Возвращает (H, r, n) для заданных k и d_min."""
    
    r = 1
    while 2 ** r < k + r + 1:
        r += 1
    n = k + r

   
    cols = []
    wt = 2
    while len(cols) < k:
        for num in range(3, 2 ** r):
            if bin(num).count("1") == wt and len(cols) < k:
                cols.append(num)
        wt += 1

    
    H = []
    for i in range(r):
        row = [(cols[j] >> (r - 1 - i)) & 1 for j in range(k)]
        row += [1 if i == j else 0 for j in range(r)]
        H.append(row)

  
    if dmin == 4:
        for row in H:
            row.append(0)
        H.append([1] * (n + 1))
        H[-1] = [sum(row[j] for row in H) % 2 for j in range(n + 1)]
        r += 1
        n += 1
    return H, r, n


def check_bits(H, k, x):
    """Проверочные символы для информационных бит x."""
    return [sum(row[j] * x[j] for j in range(k)) % 2 for row in H]


def show(v):
    return "".join(map(str, v))


def main():
    text = read_message()
    dmin = read_dmin()

    Xk = to_bits(text)
    k = len(Xk)
    H, r, n = build_h(k, dmin)

    Xr = check_bits(H, k, Xk)
    Xn = Xk + Xr

    print("Сообщение:", text)
    print("k =", k, " r =", r, " n =", n, " d_min =", dmin)
    print("Матрица H:")
    for row in H:
        print(show(row[:k]), "|", show(row[k:]))
    print("Xk =", show(Xk))
    print("Xr =", show(Xr))
    print("Xn =", show(Xn))

    for errors in [0, 1, 2]:
        print()
        print("Ошибок:", errors)
        Yn = Xn[:]
        pos = random.sample(range(n), errors)
        for p in pos:
            Yn[p] = 1 - Yn[p]
        print("Позиции ошибок (с 1):", sorted(p + 1 for p in pos))

        Yk, Yr = Yn[:k], Yn[k:]
        Yr2 = check_bits(H, k, Yk)
        S = [1 if Yr[i] != Yr2[i] else 0 for i in range(r)]

        print("Yn  =", show(Yn))
        print("Yr  =", show(Yr))
        print("Yr' =", show(Yr2))
        print("S   =", show(S))

        E = [0] * n
        if sum(S) == 0:
            print("Синдром нулевой: ошибок не обнаружено")
        else:
           
            mist = -1
            for j in range(n):
                if [row[j] for row in H] == S:
                    mist = j
                    break
            if mist == -1:
                print("Синдром не совпадает ни с одним столбцом H: "
                      "обнаружена двойная ошибка, исправить нельзя")
            else:
                E[mist] = 1
                print("Синдром совпал со столбцом", mist + 1,
                      "- исправляем бит", mist + 1)
                if dmin == 3 and errors == 2:
                    print("Внимание: при d_min = 3 двойная ошибка не "
                          "обнаруживается, исправление ложное")
        print("En  =", show(E))

        Y = [(Yn[i] + E[i]) % 2 for i in range(n)]
        print("Исправленное =", show(Y))
        if Y == Xn:
            print("Слово восстановлено верно")
        else:
            print("Слово восстановлено неверно")


if __name__ == "__main__":
    main()