"""Лабораторная № 4. Код Хемминга. Вариантов в задании нет.
Запуск: py lab4.py. Python 3.10+, только стандартная библиотека.
"""
import random
from pathlib import Path


def ask_int(prompt, low, high, default):
    value = int(input(f"{prompt} [{default}]: ").strip() or default)
    if not low <= value <= high:
        raise ValueError(f"Введите число от {low} до {high}.")
    return value


def bit_text(bits):
    return "".join(map(str, bits))


def show_bits(label, bits):
    if bits is None:
        return [f"{label:<20} не определён"]
    text = bit_text(bits)
    chunks = [text[i:i+64] for i in range(0, len(text), 64)]
    return [f"{label if i == 0 else '':<20} {chunk}"
            for i, chunk in enumerate(chunks)]


def encode(data, a):
    return data + [sum(x*y for x,y in zip(data,row)) % 2 for row in a]


def matrix(a):
    r = len(a)
    return [row + [int(i == j) for j in range(r)] for i,row in enumerate(a)]


def matrix_text(h):
    lines = ["Проверочная матрица H:"]
    for start in range(0, len(h[0]), 32):
        stop = min(start+32, len(h[0]))
        lines.append(f"  Столбцы {start+1}–{stop}:")
        for j,row in enumerate(h, 1):
            lines.append(f"  {j:>2}: " + " ".join(map(str,row[start:stop])))
    return lines


def corrupt(word, count, rng):
    positions = sorted(rng.sample(range(len(word)), count))
    received = word[:]
    for p in positions:
        received[p] ^= 1
    return received, positions


def experiment(word, decode, samples, rng):
    lines = ["", "СТАТИСТИКА", " i   Опыты  Обнаружено    N2    N3   N2/N1   N3/N1  Ложных",
             "N2 — верная кратность; N3 — точное восстановление всех битов."]
    for count in range(0, min(6,len(word))+1):
        detected = n2 = n3 = wrong = 0
        for _ in range(samples):
            received,_ = corrupt(word,count,rng)
            result,s,positions,weight,status = decode(received)
            detected += any(s)
            n2 += weight == count
            n3 += result == word
            wrong += positions not in (None,()) and result != word
        lines.append(f"{count:>2} {samples:>7} {detected:>11} {n2:>5} {n3:>5} "
                     f"{n2/samples:>7.3f} {n3/samples:>7.3f} {wrong:>7}")
    lines.append("Случайная выборка не заменяет теоретические гарантии кода.")
    return lines


def detailed(data,a,decode,count,rng):
    word = encode(data,a)
    received,actual = corrupt(word,count,rng)
    result,s,estimated,weight,status = decode(received)
    n,k = len(word),len(data)
    lines = ["", f"ОПЫТ: ошибок внесено — {count}", "-"*64]
    values = [
        ("Xk",data), ("Xr",word[k:]), ("Xn",word), ("Yn",received),
        ("Yr",received[k:]), ("Yr повторно",encode(received[:k],a)[k:]),
        ("Синдром",s), ("E фактический",[int(i in actual) for i in range(n)]),
        ("E оценённый",None if estimated is None else [int(i in estimated) for i in range(n)]),
        ("Yn исправленное",result)
    ]
    for label,bits in values:
        lines += show_bits(label,bits)
    lines += [f"Реальные позиции: {[p+1 for p in actual]}",
              f"Оценённые позиции: {None if estimated is None else [p+1 for p in estimated]}",
              f"Оценка кратности: {weight}", f"Статус: {status}",
              f"Слово восстановлено: {'ДА' if result == word else 'НЕТ'}"]
    return lines


def save_report(filename, lines):
    Path(filename).write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"\nСохранён {filename}. При следующем запуске он перезаписывается.")


def hamming(k, distance):
    """Матрица A для H=[A|I]. Столбцы — как в методичке."""
    r = 2
    while 2 ** r < k + r + 1:
        r += 1
    columns = [number for number in range(1, 2 ** r)
               if number.bit_count() >= 2]
    columns.sort(key=lambda number: (number.bit_count(), number))
    a = [[(number >> (r - 1 - j)) & 1 for number in columns[:k]]
         for j in range(r)]
    if distance == 4:
        # Общий бит = чётность всего базового слова, выраженная через данные.
        a.append([(1 + sum(row[i] for row in a)) % 2 for i in range(k)])
    return a



def make_decoder(h, distance):
    columns = {tuple(col): i for i,col in enumerate(zip(*h))}

    def decode(received):
        s = tuple(sum(x*y for x,y in zip(received,row)) % 2 for row in h)
        if not any(s):
            return received[:],s,(),0,"Проверки выполнены"
        if distance == 4 and sum(received) % 2 == 0:
            return received[:],s,None,2,"Двойная ошибка, если кратность не выше 2"
        if s not in columns:
            return received[:],s,None,None,"Синдром не соответствует одиночной ошибке"
        p = columns[s]
        result = received[:]
        result[p] ^= 1
        return result,s,(p,),1,"Применено исправление одиночной ошибки"

    return decode


def main():
    print("="*64)
    print("ЛАБОРАТОРНАЯ № 4 — КОД ХЕММИНГА")
    print("="*64)
    path = Path(input("Файл UTF-8 [message.txt]: ").strip().strip('"') or "message.txt")
    if not path.exists():
        if path != Path("message.txt"):
            raise ValueError(f"Файл не найден: {path}")
        text = input("Введите текст для создания message.txt [Привет!]: ") or "Привет!"
        path.write_text(text,encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    data = [int(bit) for byte in text.encode("utf-8") for bit in f"{byte:08b}"]
    if len(data) < 16:
        raise ValueError("По методичке нужно не менее 16 информационных битов.")
    mode = ask_int("Режим: 1 — d=3; 2 — d=4; 3 — оба",1,3,3)
    show_h = ask_int("Показать матрицу в консоли: 0 — нет; 1 — да",0,1,1)
    samples = ask_int("Опытов на каждую кратность для статистики",1,100000,300)
    report = ["ЛАБОРАТОРНАЯ № 4. КОД ХЕММИНГА",f"Файл: {path}",
              f"Текст: {text!r}; кодировка UTF-8; k={len(data)}",
              "H=[A|I]; все операции выполняются по модулю 2.",
              "Позиции считаются с 1 слева, включая проверочные биты.",
              "Нулевой синдром не доказывает отсутствие ошибок.",
              "Seed подробных опытов=1, статистики=2."]
    print(f"\nИсходный текст: {text!r}; {len(data)} бит.")
    for distance in ((3,4) if mode == 3 else (mode+2,)):
        a = hamming(len(data),distance)
        h = matrix(a)
        decode = make_decoder(h,distance)
        k,r = len(data),len(a)
        heading = ["\n"+"="*64,f"ХЕММИНГ: d_min={distance}",
                   f"k={k}; r={r}; n={k+r}; скорость={k/(k+r):.4f}; избыточность={r/(k+r):.4f}"]
        print("\n".join(heading))
        report += heading + matrix_text(h)
        if show_h:
            print("\n".join(matrix_text(h)))
        rng = random.Random(1)
        for count in (0,1,2):
            lines = detailed(data,a,decode,count,rng)
            print("\n".join(lines))
            report += lines
        lines = experiment(encode(data,a),decode,samples,random.Random(2))
        print("\n".join(lines))
        report += lines
    report += ["\nВЫВОДЫ", "Оба кода гарантированно исправляют одну ошибку.",
               "При d=3 двойная ошибка обнаруживается исходным синдромом,",
               "но может быть ошибочно исправлена как одиночная.",
               "При d=4 все двойные ошибки обнаруживаются без попытки исправления.",
               "Текст и требуемое расстояние методичка предлагает согласовать с преподавателем."]
    save_report("lab4_result.txt",report)


if __name__ == "__main__":
    try:
        main()
    except (ValueError,OSError) as error:
        print("Ошибка:",error)
    except (EOFError,KeyboardInterrupt):
        print("\nВвод прерван.")
