"""Лабораторная № 5. Итеративные коды. Вариант 1, k=16.
Запуск: py lab5.py. Python 3.10+, только стандартная библиотека.

Формы из таблицы 5.2: 4x4, 8x2, 4x2x2, 2x4x2.
Для прямоугольных слоёв принято явное обобщение диагоналей:
2D — обычные i+j=d; 3D — циклические (i+j) mod rows и (i-j) mod rows.
Группы: H,V,D+,D-,Z. HV добавляется отдельно для каждого слоя.
Поиск ошибок до веса 3 не означает гарантии исправления всех троек.
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


def iterative(rows, cols, layers, groups, hv):
    """Одна строка A соответствует одному передаваемому паритету."""
    a = []
    k = rows * cols * layers

    def add(cells):
        check = [0] * k
        for t, i, j in cells:
            check[(t * rows + i) * cols + j] = 1
        a.append(check)

    for t in range(layers):
        for i in range(rows):
            add([(t, i, j) for j in range(cols)])       # H: строки
        for j in range(cols):
            add([(t, i, j) for i in range(rows)])       # V: столбцы
        if groups >= 3:
            for d in range(rows + cols - 1 if layers == 1 else rows):
                add([(t, i, j) for i in range(rows) for j in range(cols)
                     if (i+j if layers == 1 else (i+j) % rows) == d])
        if groups >= 4:
            for d in range(rows):
                add([(t, i, j) for i in range(rows) for j in range(cols)
                     if (i-j) % rows == d])
        if hv:
            add([(t, i, j) for i in range(rows) for j in range(cols)])
    if groups == 5:
        for i in range(rows):
            for j in range(cols):
                add([(t, i, j) for t in range(layers)])  # Z: между слоями
    return a



# Вариант 1: k=16. Не путать с номером лабораторной работы.
SHAPES = [(4,4,1),(8,2,1),(4,2,2),(2,4,2)]


def make_decoder(h):
    """Синдромный поиск минимальной ошибки веса 1, 2 или 3.

    Для троек используются уже построенные синдромы пар.
    Исходное слово и реальные позиции декодер не получает.
    """
    columns = [sum(bit << j for j,bit in enumerate(col)) for col in zip(*h)]
    singles = {s:(i,) for i,s in enumerate(columns)}
    pairs = {}
    for i in range(len(columns)):
        for j in range(i+1,len(columns)):
            pairs.setdefault(columns[i] ^ columns[j],[]).append((i,j))
    cache = {}

    def find_error(s):
        if s in singles:
            return 1,singles[s]
        if s in pairs:
            candidates = pairs[s]
            return 2,candidates[0] if len(candidates) == 1 else None
        if s in cache:
            return cache[s]
        candidates = set()
        for i,col in enumerate(columns):
            for pair in pairs.get(s ^ col,()):
                if i not in pair:
                    candidates.add(tuple(sorted((i,*pair))))
                    if len(candidates) > 1:
                        cache[s] = (3,None)
                        return cache[s]
        answer = (3,next(iter(candidates))) if candidates else (None,None)
        cache[s] = answer
        return answer

    def decode(received):
        s = 0
        for bit,col in zip(received,columns):
            if bit:
                s ^= col
        vector = tuple((s >> j) & 1 for j in range(len(h)))
        if s == 0:
            return received[:],vector,(),0,"Проверки выполнены"
        weight,positions = find_error(s)
        if positions is None:
            status = "Неоднозначное исправление" if weight else "Нет кандидата веса до 3"
            return received[:],vector,None,weight,status
        result = received[:]
        for p in positions:
            result[p] ^= 1
        return result,vector,positions,weight,"Применён минимальный кандидат исправления"

    return decode


def main():
    print("="*64)
    print("ЛАБОРАТОРНАЯ № 5 — ИТЕРАТИВНЫЕ КОДЫ. ВАРИАНТ 1")
    print("="*64)
    entered = input("16 бит [0110100110010110]: ").strip()
    text = "".join(entered.split()) if entered else "0110100110010110"
    if len(text) != 16 or set(text) - {"0","1"}:
        raise ValueError("Для варианта 1 нужны ровно 16 бит: только 0 и 1.")
    data = list(map(int,text))
    mode = ask_int("1 — одна конфигурация; 2 — все конфигурации варианта",1,2,1)
    if mode == 1:
        print("1: 4x4; 2: 8x2; 3: 4x2x2; 4: 2x4x2")
        shape = SHAPES[ask_int("Форма",1,4,1)-1]
        groups = ask_int("Групп паритетов",2,3 if shape[2] == 1 else 5,2)
        hv = ask_int("Дополнительный HV: 0 — нет; 1 — да",0,1,0)
        configs = [(shape,groups,hv)]
    else:
        configs = [(shape,g,hv) for shape in SHAPES
                   for g in range(2,4 if shape[2] == 1 else 6) for hv in (0,1)]
    max_errors = min(16+len(iterative(*shape,g,hv)) for shape,g,hv in configs)
    count = ask_int(f"Ошибок в подробном опыте (0–{max_errors})",0,max_errors,2)
    show_h = ask_int("Показать матрицы H в консоли: 0 — нет; 1 — да",0,1,0)
    samples = ask_int("Опытов на каждую кратность для статистики",1,100000,300)
    report = ["ЛАБОРАТОРНАЯ № 5. ВАРИАНТ 1", "k=16; формы: 4x4, 8x2, 4x2x2, 2x4x2.",
              "Группы: H,V,D+,D-,Z. HV — отдельная опция, не направление.",
              "2D-диагонали: i+j=d. 3D-диагонали: (i+j) mod rows=d и (i-j) mod rows=d.",
              "Это выбранное обобщение квадратного примера методички для прямоугольников.",
              "Порядок паритетов: в каждом слое H,V,D+,D-,HV, затем группа Z.",
              "Декодер ищет минимальную ошибку веса до 3; при равноправных кандидатах отказывается.",
              "Это не гарантия исправления всех ошибок веса до 3 для любого кода.",
              "Нулевой синдром не доказывает отсутствие ошибок. Seed опытов=1, статистики=2."]
    comparison = ["\nСРАВНЕНИЕ", "Форма    Группы HV    r    n   Скорость  Избыточность"]
    for shape,groups,hv in configs:
        rows,cols,layers = shape
        name = f"{rows}x{cols}" + (f"x{layers}" if layers > 1 else "")
        a = iterative(rows,cols,layers,groups,hv)
        h = matrix(a)
        decode = make_decoder(h)
        r,n = len(a),16+len(a)
        heading = ["\n"+"="*64,f"ФОРМА {name} | ГРУПП {groups} | HV={hv}",
                   f"k=16; r={r}; n={n}; скорость={16/n:.4f}; избыточность={r/n:.4f}"]
        for t in range(layers):
            heading.append(f"Слой {t+1}:")
            for i in range(rows):
                start = (t*rows+i)*cols
                heading.append("  " + " ".join(map(str,data[start:start+cols])))
        print("\n".join(heading))
        report += heading + matrix_text(h)
        if show_h:
            print("\n".join(matrix_text(h)))
        lines = detailed(data,a,decode,count,random.Random(1))
        lines += experiment(encode(data,a),decode,samples,random.Random(2))
        print("\n".join(lines))
        report += lines
        comparison.append(f"{name:<9} {groups:>5} {hv:>2} {r:>4} {n:>4} {16/n:>10.4f} {r/n:>12.4f}")
    report += comparison + ["\nВЫВОДЫ",
        "Большее число проверок уменьшает скорость. Исправление зависит от структуры проверок.",
        "Двойные и тройные ошибки могут иметь неоднозначный синдром; отказ не является сбоем.",
        "За возможностями кода возможны невидимые ошибки и ложные исправления.",
        "Для H,V без HV расстояние 3, с HV — 4; утверждение части 2, стр. 50, требует уточнения.",
        "Для rows=2 циклические D+ и D- совпадают: направления не следует считать независимыми.",
        "Правило диагоналей прямоугольных слоёв следует согласовать с преподавателем."]
    print("\n".join(comparison))
    save_report("lab5_result.txt",report)


if __name__ == "__main__":
    try:
        main()
    except (ValueError,OSError) as error:
        print("Ошибка:",error)
    except (EOFError,KeyboardInterrupt):
        print("\nВвод прерван.")
