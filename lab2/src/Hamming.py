import argparse
import random
 
MIN_BITS = 16         
ENCODING = "cp1251"    
 
 
def fmt(bits):
    return "".join(map(str, bits))
 
 
def matrix_str(M):
    return "\n".join(" ".join(map(str, row)) for row in M)
 
 
def bits_from_text(text):
    data = text.encode(ENCODING, errors="replace")
    return [int(b) for byte in data for b in f"{byte:08b}"]
 
 
def calc_r(k):
    r = 2
    while 2 ** r < k + r + 1:
        r += 1
    return r
 
 
def build_P(k, r):
    cols, num = [], 3
    while len(cols) < k:
        if num >= 2 ** r:
            raise ValueError("слишком мало проверочных разрядов r для данного k")
        if bin(num).count("1") >= 2:
            cols.append([int(c) for c in format(num, f"0{r}b")])
        num += 1
    return [[cols[j][i] for j in range(k)] for i in range(r)]
 
 
def build_H(P, k, r):
    return [P[i] + [1 if j == i else 0 for j in range(r)] for i in range(r)]
 
 
def build_H4(H):
    r, n = len(H), len(H[0])
    Hx = [row + [0] for row in H] + [[1] * (n + 1)]
    last = [sum(Hx[i][j] for i in range(r + 1)) % 2 for j in range(n + 1)]
    Hc = Hx[:-1] + [last]
    return Hx, Hc
 
 
def columns(H):
    return [[H[i][j] for i in range(len(H))] for j in range(len(H[0]))]
 
 
def check_bits(xk, P, dmin):
    xr = [sum(P[i][j] & xk[j] for j in range(len(xk))) % 2 for i in range(len(P))]
    if dmin == 4:
        xr.append((sum(xk) + sum(xr)) % 2)
    return xr
 
 
def syndrome(yn, k, P, dmin):
    r = len(P)
    yk, yr = yn[:k], yn[k:]
    yr2 = check_bits(yk, P, dmin)                      
    s = [a ^ b for a, b in zip(yr[:r], yr2[:r])]
    if dmin == 4:
        s.append(sum(yn) % 2)                          
    return yr2, s
 
 
def locate(s, P, k, dmin):
    r = len(P)
    n = k + r + (1 if dmin == 4 else 0)
    cols = columns(build_H(P, k, r))
    if dmin == 3:
        if not any(s):
            return "ошибок не обнаружено", None
        for j, c in enumerate(cols):
            if c == s:
                return "одиночная ошибка", j
        return "ошибка обнаружена, но не может быть исправлена", None
    sr, sa = s[:-1], s[-1]
    if not any(sr) and sa == 0:
        return "ошибок не обнаружено", None
    if sa == 1:
        if not any(sr):
            return "одиночная ошибка (в общем паритете)", n - 1
        for j, c in enumerate(cols):
            if c == sr:
                return "одиночная ошибка", j
        return "ошибка обнаружена, но не может быть исправлена (нечётная кратность >= 3)", None
    return "двойная ошибка обнаружена, исправление невозможно", None
 
 
def run(xk, dmin, nerr, rng, out):
    k = len(xk)
    r = calc_r(k)
    P = build_P(k, r)
    H = build_H(P, k, r)
    xr = check_bits(xk, P, dmin)
    xn = xk + xr
    n = len(xn)
 
    pos = sorted(rng.sample(range(n), nerr))
    yn = xn[:]
    for p in pos:
        yn[p] ^= 1
    yr = yn[k:]
    yr2, s = syndrome(yn, k, P, dmin)
    status, p = locate(s, P, k, dmin)
 
    en = [0] * n
    if p is not None:
        en[p] = 1
    yfix = [a ^ b for a, b in zip(yn, en)]
 
    w = out.append
    w(f"d_min = {dmin}")
    w(f"k = {k}, r = {len(xr)}, n = {n}")
    w(f"относительная избыточность r/k = {len(xr) / k:.3f}, скорость k/n = {k / n:.3f}")
    if dmin == 3:
        w("\nПроверочная матрица H (r x n) = [P' | I]:")
        w(matrix_str(H))
    else:
        Hx, Hc = build_H4(H)
        w("\nПроверочная матрица H' (4.8):")
        w(matrix_str(Hx))
        w("\nКаноническая форма (последняя строка = сумма всех строк):")
        w(matrix_str(Hc))
    w(f"\nX_k  (информационное слово)   = {fmt(xk)}")
    w(f"X_r  (избыточные символы)     = {fmt(xr)}")
    w(f"X_n  (кодовое слово)          = {fmt(xn)}")
    w(f"\nГенерируется ошибок: {nerr}; позиции (с 1): {[q + 1 for q in pos]}")
    w(f"Y_n  (принятое слово)         = {fmt(yn)}")
    w(f"Y_r  (принятые избыточные)    = {fmt(yr)}")
    w(f"Y_r' (пересчитанные)          = {fmt(yr2)}")
    w(f"S    (синдром)                = {fmt(s)}")
    w(f"Результат анализа синдрома: {status}" + (f" в позиции {p + 1}" if p is not None else ""))
    w(f"E_n  (вектор ошибки)          = {fmt(en)}")
    w(f"Y_n' (исправленное слово)     = {fmt(yfix)}")
    if yfix == xn:
        w("Итог: Y_n' = X_n, слово восстановлено верно." if nerr else "Итог: ошибок не было, слово принято верно.")
    elif p is None and any(s):
        w("Итог: ошибка обнаружена, слово не исправлено (требуется повторная передача).")
    elif not any(s):
        w("Итог: синдром нулевой, но слово искажено - ошибка НЕ обнаружена.")
    else:
        w("Итог: слово исправлено НЕВЕРНО (число ошибок превышает корректирующую способность кода).")
 
 
def matrices_report():
    out = []
    for k in (4, 6, 8, 9, 10, 15, 16):
        r = calc_r(k)
        P = build_P(k, r)
        H = build_H(P, k, r)
        Hx, Hc = build_H4(H)
        out.append(f"===== k = {k} =====")
        out.append(f"d_min = 3: r = {r}, n = {k + r}\n{matrix_str(H)}")
        out.append(f"d_min = 4: r = {r + 1}, n = {k + r + 1}\nH':\n{matrix_str(Hx)}\nканоническая:\n{matrix_str(Hc)}\n")
    k = 3
    out.append("===== Код простой чётности, k = 3 (d_min = 2) =====")
    out.append("H = [1 1 1 1]   (X_r = x1 + x2 + x3 mod 2, n = 4)")
    return "\n".join(out)
 
 
def main():
    ap = argparse.ArgumentParser(description="Код Хемминга: кодирование, ошибки, синдром, исправление")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text", help="исходное сообщение (строка)")
    src.add_argument("--file", help="текстовый файл с сообщением")
    ap.add_argument("--dmin", type=int, choices=(3, 4), default=3)
    ap.add_argument("--errors", type=int, choices=(0, 1, 2), default=1)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default="hamming_log.txt", help="файл-протокол")
    ap.add_argument("--matrices", action="store_true", help="вывести матрицы для контрольных вопросов")
    a = ap.parse_args()
 
    if a.matrices:
        text = matrices_report()
        print(text)
        with open("hamming_matrices.txt", "w", encoding="utf-8") as f:
            f.write(text)
        return
 
    if a.file:
        with open(a.file, encoding="utf-8") as f:
            msg = f.read().strip()
    else:
        msg = a.text if a.text else "Hello, мир!"
    xk = bits_from_text(msg)
    if len(xk) < MIN_BITS:
        raise SystemExit(f"Сообщение слишком короткое: {len(xk)} бит, нужно не менее {MIN_BITS}")
 
    rng = random.Random(a.seed)
    out = [f"Сообщение: {msg!r}"]
    run(xk, a.dmin, a.errors, rng, out)
    text = "\n".join(out)
    print(text)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(text + "\n")
 
 
if __name__ == "__main__":
    main()
