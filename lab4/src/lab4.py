# -*- coding: utf-8 -*-
"""
Лабораторная работа №4, вариант 15.
Арифметика точечных групп эллиптических кривых, протокол ECDH и алгоритмы ЭЦП.

Вариант 15: ЭЦП EdDSA (Ed25519), кривая Эдвардса в аффинных координатах,
задача защиты — constant-time извлечение квадратного корня по модулю (алгоритм
Тонелли-Шенкса с изоляцией ветвлений).

Структура проекта:
    ec_curve.py  — модуль 1, алгебра кривой Ed25519 (Point, add, double, multiply);
    protocols.py — модуль 2, SHA-512, ECDH, подпись и проверка Ed25519;
    ct_secure.py — модуль 3, constant-time защита (Тонелли-Шенкс, CMOV, CSWAP,
                   лестница Монтгомери, сравнение без раннего выхода);
    lab4.py      — меню, тестирование и анализ (этот файл).
Ввод и вывод — только сырые шестнадцатеричные значения; форматы PEM/DER/ASN.1
не используются. matplotlib нужен только для рисунка в пункте 6.
"""
import ast
import inspect
import os
import secrets
import statistics
import time

import ec_curve as ec
import ct_secure as ct
import protocols as pr

VARIANT = 15
OUT_DIR = "results"

# ----------------------------------------------------------------------
#               ТЕСТОВЫЕ ДАННЫЕ (сырые hex-строки)
# ----------------------------------------------------------------------
SHA512_VECTORS = [   # (сообщение, SHA-512) — FIPS 180-4
    ("", "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce"
         "47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"),
    ("616263", "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
               "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f"),
]
RFC8032_VECTORS = [  # (секретный ключ, открытый ключ, сообщение, подпись) — RFC 8032, 7.1
    ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
     "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
     "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
     "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
     "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
     "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025", "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac"
     "18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]
# Тестовое сообщение варианта (ASCII «Lab 4, variant 15: EdDSA (Ed25519), constant-time
# Tonelli-Shanks») и его SHA-512
DEMO_MSG_HEX = "4c616220342c2076617269616e742031353a204564445341202845643235353139292c20636f6e7374616e742d74696d6520546f6e656c6c692d5368616e6b73"
DEMO_MSG_SHA512_HEX = "b1580bbc185ed81cca973a58cb667770f0f830d4bf73568ca3864f35628cad4fa53c9a0876298467a14093986ba882a09c253dd8f71a47ec9d19b2073548da5f"
DEMO_SIGN_SEED_HEX = "346a6ae1e0f91d8589abba86dfbc43cbf24dcc6dd1b6556d421ea2476fc5a4be"
ALICE_SEED_HEX = "6944baf9e4d2fbc835e9dcec3459f99eb229198332d95e345cff3f4d166b40ed"
BOB_SEED_HEX = "71315310066e4c549293f30fcb52708004ddc5a222dadeb2802bad208d8fd81f"
# Простые числа с разным S (p - 1 = Q * 2^S) для проверки Тонелли-Шенкса
SQRT_PRIMES = [
    ("secp256k1, S = 1", "fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f"),
    ("Ed25519, S = 2", ec.P_HEX),
    ("NIST P-224, S = 96", "ffffffffffffffffffffffffffffffff000000000000000000000001"),
]


# ======================================================================
#                     ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ======================================================================
def title(text):
    print("=" * 78)
    print(text)
    print("=" * 78)


def ask_hex(prompt, default_hex, nbytes=None):
    """Ввод только сырых hex-значений: Enter — по умолчанию, r — случайное значение."""
    s = input(f"{prompt} (hex{', ' + str(nbytes) + ' байт' if nbytes else ''}"
              f"{', r — случайно' if nbytes else ''}) [{default_hex or 'пусто'}]: ").strip()
    if not s:
        s = default_hex
    elif s.lower() == "r" and nbytes:
        s = secrets.token_hex(nbytes)
        print(f"  сгенерировано: {s}")
    data = bytes.fromhex(s)
    if nbytes and len(data) != nbytes:
        raise ValueError(f"нужно ровно {nbytes} байт ({2 * nbytes} hex-символов)")
    return data


def out_path(name):
    os.makedirs(OUT_DIR, exist_ok=True)
    return os.path.join(OUT_DIR, name)


# ======================================================================
#                     САМОПРОВЕРКА
# ======================================================================
def self_test():
    title("САМОПРОВЕРКА: параметры кривой, SHA-512, RFC 8032, Тонелли-Шенкс")
    res = []

    def check(name, ok):
        res.append(bool(ok))
        print(f"  [{'OK' if ok else 'ОШИБКА'}] {name}")

    check("d * 121666 = -121665 (mod p)", (ec.D * 121666 + 121665) % ec.P == 0)
    check("a = -1 — квадрат (p = 1 mod 4), d — невычет: закон сложения полный",
          ec.P % 4 == 1 and ct.ct_sqrt(ec.D)[1] == 0)
    check("G лежит на кривой, y_G = 4/5 (mod p)",
          ec.is_on_curve(ec.G) and ec.G.y == 4 * ec.finv(5) % ec.P)
    check("q * G = O (порядок базовой точки)", ec.multiply(ec.Q, ec.G) == ec.O)
    check("double(G) = add(G, G), G + (-G) = O, G + O = G",
          ec.double(ec.G) == ec.add(ec.G, ec.G) and ec.add(ec.G, ec.neg(ec.G)) == ec.O
          and ec.add(ec.G, ec.O) == ec.G)
    ok = all(ct.secure_multiply(k, ec.G) == ec.multiply(k, ec.G)
             for k in [1, 2, ec.Q - 1] + [secrets.randbelow(ec.Q) for _ in range(3)])
    check("лестница Монтгомери = Double-and-Add (k = 1, 2, q - 1 и 3 случайных)", ok)
    for m, hval in SHA512_VECTORS:
        check(f"SHA-512(«{bytes.fromhex(m).decode()}») = {hval[:16]}…", pr.sha512(bytes.fromhex(m)).hex() == hval)
    check("SHA-512 тестового сообщения совпадает с заданным в коде hex-значением",
          pr.sha512(bytes.fromhex(DEMO_MSG_HEX)).hex() == DEMO_MSG_SHA512_HEX)
    for n, (sk, pk, msg, sig) in enumerate(RFC8032_VECTORS, 1):
        seed, m = bytes.fromhex(sk), bytes.fromhex(msg)
        check(f"RFC 8032 TEST {n}: открытый ключ {pk[:16]}…", pr.keypair(seed)[3].hex() == pk)
        check(f"RFC 8032 TEST {n}: подпись {sig[:16]}…", pr.sign(m, seed).hex() == sig)
        check(f"RFC 8032 TEST {n}: проверка подписи", pr.verify(m, bytes.fromhex(sig), bytes.fromhex(pk))[0])
    for name, phex in SQRT_PRIMES:
        p = int(phex, 16)
        ctx = ct.SqrtContext(p)
        good = True
        for _ in range(100):
            a = secrets.randbelow(p)
            r1, ok1 = ct.ct_sqrt(a, ctx)
            r2, ok2 = ct.sqrt_classic(a, ctx)
            sq = secrets.randbelow(p) ** 2 % p
            r3, ok3 = ct.ct_sqrt(sq, ctx)
            good &= ok1 == ok2 == (pow(a, (p - 1) // 2, p) != p - 1)
            good &= (not ok1 or r1 * r1 % p == a) and ok3 == 1 and r3 * r3 % p == sq
        check(f"ct_sqrt, {name}: 200 случайных аргументов, совпадение с классическим", good)
    pt, valid = ct.ct_decompress(ec.encode_point(ec.G))
    check("декомпрессия encode(G) даёт G", valid == 1 and pt == ec.G)
    check("y >= p отвергается", ct.ct_decompress(ec.P.to_bytes(32, "little"))[1] == 0)
    y = 2
    while ct.ct_sqrt(ec.x2_from_y(y))[1]:
        y += 1
    check(f"y = {y}: x^2 — невычет, точка отвергается", ct.ct_decompress(y.to_bytes(32, "little"))[1] == 0)
    print("Самопроверка пройдена" if all(res) else "ВНИМАНИЕ: обнаружены ошибки")
    return all(res)


# ======================================================================
#                     ПРОТОКОЛ ECDH
# ======================================================================
def demo_ecdh(seed_a=None, seed_b=None):
    title("ПРОТОКОЛ ECDH НА КРИВОЙ Ed25519")
    seed_a = seed_a or bytes.fromhex(ALICE_SEED_HEX)
    seed_b = seed_b or bytes.fromhex(BOB_SEED_HEX)
    d_a, q_a, enc_a = pr.ecdh_keypair(seed_a)
    d_b, q_b, enc_b = pr.ecdh_keypair(seed_b)
    for name, seed, d, q, enc in (("Алиса", seed_a, d_a, q_a, enc_a), ("Боб", seed_b, d_b, q_b, enc_b)):
        print(f"{name}:\n  seed = {seed.hex()}\n  d    = {d:064x}  (clamp(seed))")
        print(f"  Q = d*G:\n{q.hex('    ')}\n  передаётся encode(Q) = {enc.hex()}")
    rec_a, _ = ct.ct_decompress(enc_a)
    rec_b, _ = ct.ct_decompress(enc_b)
    print(f"Боб распаковал Q_A (constant-time Тонелли-Шенкс): "
          f"{'совпадает' if rec_a == q_a else 'НЕ СОВПАДАЕТ'} с Q_A")
    print(f"Алиса распаковала Q_B: {'совпадает' if rec_b == q_b else 'НЕ СОВПАДАЕТ'} с Q_B")
    k_a = pr.ecdh_shared(d_a, enc_b)
    k_b = pr.ecdh_shared(d_b, enc_a)
    print(f"Алиса: K = d_A * Q_B:\n{k_a.hex('    ')}\nБоб:   K = d_B * Q_A:\n{k_b.hex('    ')}")
    same = ct.ct_point_eq(k_a, k_b) == 1
    print(f"Shared Secret (x_K) Алисы: {k_a.x:064x}\nShared Secret (x_K) Боба:  {k_b.x:064x}")
    print("Общий секрет совпадает" if same else "ОШИБКА: секреты различаются")
    return same


# ======================================================================
#                     ПОДПИСЬ И ПРОВЕРКА Ed25519
# ======================================================================
def demo_sign(seed=None, msg=None):
    title("ЭЦП EdDSA (Ed25519): ЦИКЛ «ПОДПИСЬ — ПРОВЕРКА»")
    seed = seed or bytes.fromhex(DEMO_SIGN_SEED_HEX)
    msg = bytes.fromhex(DEMO_MSG_HEX) if msg is None else msg
    d, prefix, A, a_enc = pr.keypair(seed)
    print(f"Секретный ключ seed = {seed.hex()}\n  d = clamp(SHA-512(seed)[0:32]) = {d:064x}")
    print(f"  h_B = SHA-512(seed)[32:64] = {prefix.hex()}")
    print(f"Открытый ключ A = d*G:\n{A.hex('    ')}\n  encode(A) = {a_enc.hex()}")
    print(f"Сообщение M ({len(msg)} байт) = {msg.hex()}\n  SHA-512(M) = {pr.sha512(msg).hex()}")
    r = pr.hash_int(prefix, msg)
    R = ct.secure_multiply(r, ec.G)
    sig = pr.sign(msg, seed)
    print(f"r = SHA-512(h_B || M) mod q = {r:064x}\nR = r*G:\n{R.hex('    ')}")
    print(f"Подпись (R, S):\n  encode(R) = {sig[:32].hex()}\n  S         = {sig[32:].hex()}")
    ok, why, info = pr.verify(msg, sig, a_enc)
    print(f"Проверка: h = SHA-512(R || A || M) mod q = {info['h']:064x}")
    print(f"  S*G:\n{info['left'].hex('    ')}\n  R + h*A:\n{info['right'].hex('    ')}")
    print(f"  Результат: {'ПОДПИСЬ ВЕРНА' if ok else 'ПОДПИСЬ НЕВЕРНА'} ({why})")
    print("\nПреднамеренное искажение одного байта параметра S (байты 32..63 подписи):")
    rows = []
    for idx, mask in ((32, 0x01), (47, 0xff), (63, 0x80)):
        bad = bytearray(sig)
        bad[idx] ^= mask
        ok2, why2, _ = pr.verify(msg, bytes(bad), a_enc)
        rows.append((idx, mask, bad[32:].hex(), ok2, why2))
        print(f"  байт S[{idx - 32}] ^= 0x{mask:02x}: S' = {bad[32:].hex()}\n"
              f"    -> {'принята' if ok2 else 'ОТВЕРГНУТА'} ({why2})")
    bad_msg = bytes([msg[0] ^ 0x01]) + msg[1:] if msg else b"\x01"
    ok3, why3, _ = pr.verify(bad_msg, sig, a_enc)
    print(f"  искажён первый байт сообщения: -> {'принята' if ok3 else 'ОТВЕРГНУТА'} ({why3})")
    return sig, rows


# ======================================================================
#                     КВАДРАТНЫЙ КОРЕНЬ И ДЕКОМПРЕССИЯ
# ======================================================================
def count_ops(fn, *args):
    ct.OPS[0] = 0
    t0 = time.perf_counter()
    res = fn(*args)
    return ct.OPS[0], (time.perf_counter() - t0) * 1e6, res


def demo_sqrt(a=None, prime_index=1):
    name, phex = SQRT_PRIMES[prime_index]
    p = int(phex, 16)
    ctx = ct.SqrtContext(p)
    a = secrets.randbelow(p) ** 2 % p if a is None else a % p
    title(f"КВАДРАТНЫЙ КОРЕНЬ ПО МОДУЛЮ p ({name})")
    print(f"p = {p:x}\np - 1 = Q * 2^S: S = {ctx.S}, Q = {ctx.Q:x}\nневычет z = {ctx.z}")
    print(f"a = {a:064x}")
    for label, fn in (("constant-time", ct.ct_sqrt), ("классический", ct.sqrt_classic)):
        ops, us, (r, ok) = count_ops(fn, a, ctx)
        print(f"{label:>14}: R = {r:064x}, корень {'существует' if ok else 'не существует'}, "
              f"R^2 = a: {'да' if ok and r * r % p == a else '—'}, умножений: {ops}")


def demo_decompress(data=None):
    title("ДЕКОМПРЕССИЯ ТОЧКИ Ed25519 (constant-time Тонелли-Шенкс)")
    data = data or pr.keypair(bytes.fromhex(DEMO_SIGN_SEED_HEX))[3]
    v = int.from_bytes(data, "little")
    y, sign = v & ((1 << 255) - 1), v >> 255
    print(f"encode(P) = {data.hex()}\n  y = {y:064x}\n  знак x (бит 255) = {sign}")
    print(f"  x^2 = (y^2 - 1)/(d*y^2 + 1) = {ec.x2_from_y(y):064x}")
    pt, valid = ct.ct_decompress(data)
    print(f"Результат (valid = {valid}):\n{pt.hex('  ')}")
    print(f"  точка на кривой: {'да' if ec.is_on_curve(pt) else 'нет'}; повторное кодирование совпадает: "
          f"{'да' if ec.encode_point(pt) == data else 'нет'}")


# ======================================================================
#                     АНАЛИЗ CONSTANT-TIME
# ======================================================================
def branch_report():
    """Статический анализ исходного кода (модуль ast): число условных операторов,
    циклов while и операторов return в функциях."""
    print("\nСтатический анализ ветвлений (ast):")
    print(f"  {'функция':<26}{'if':>4}{'while':>7}{'for':>5}{'return':>8}  ветвления по секрету")
    rows = []
    notes = {"ct_decompress": "нет (if — проверка публичной длины)",
             "ct_bytes_eq": "нет (if — проверка публичной длины)",
             "sqrt_classic": "ЕСТЬ (ранний выход, while по t)", "multiply": "ЕСТЬ (if bit == 1)"}
    for f in (ct.ct_is_zero, ct.ct_select, ct.ct_cswap, ct.ct_bytes_eq, ct.ct_point_eq, ct.ct_sqrt,
              ct.ct_decompress, ct.secure_multiply, ct.sqrt_classic, ec.multiply):
        tree = ast.parse(inspect.getsource(f))
        nodes = list(ast.walk(tree))
        cnt = [sum(isinstance(n, t) for n in nodes) for t in ((ast.If, ast.IfExp), ast.While, ast.For, ast.Return)]
        note = notes.get(f.__name__, "нет")
        rows.append((f.__module__ + "." + f.__name__, *cnt, note))
        print(f"  {f.__name__:<26}{cnt[0]:>4}{cnt[1]:>7}{cnt[2]:>5}{cnt[3]:>8}  {note}")
    return rows


def sqrt_analysis(trials=300):
    print(f"\nИзвлечение корня: {trials} случайных аргументов (половина — квадраты, половина — невычеты)")
    hdr = (f"  {'модуль':<20}{'алгоритм':<15}{'умн.мин':>9}{'макс':>6}{'разных':>8}"
           f"{'t вычет, мкс':>15}{'t невычет, мкс':>18}")
    print(hdr)
    rows, data = [], {}
    for name, phex in SQRT_PRIMES[1:]:
        p = int(phex, 16)
        ctx = ct.SqrtContext(p)
        args = []
        while len(args) < trials:
            a = secrets.randbelow(p)
            want_square = len(args) % 2 == 0
            if (pow(a, (p - 1) // 2, p) != p - 1) == want_square:
                args.append((a, want_square))
        for label, fn in (("классический", ct.sqrt_classic), ("constant-time", ct.ct_sqrt)):
            ops, t_sq, t_ns = [], [], []
            for a, sq in args:
                o, us, _ = count_ops(fn, a, ctx)
                ops.append(o)
                (t_sq if sq else t_ns).append(us)
            row = (name, label, min(ops), max(ops), len(set(ops)), statistics.median(t_sq), statistics.median(t_ns))
            rows.append(row)
            data[(name, label)] = (ops, t_sq, t_ns)
            print(f"  {name:<20}{label:<15}{row[2]:>9}{row[3]:>6}{row[4]:>8}{row[5]:>15.1f}{row[6]:>18.1f}")
    print("  (время — медиана; умножения подсчитываются точно, включая возведения в степень)")
    return rows, data


def ladder_analysis(weights=(8, 64, 128, 192, 248), reps=3):
    print("\nСкалярное умножение k*G для 255-битных k с разным весом Хэмминга w:")
    print(f"  {'w':>4}  {'алгоритм':<22}{'вызовов add':>14}{'вызовов double':>17}{'время, мс':>11}")
    cnt = {"add": 0, "double": 0}
    orig_add, orig_double = ec.add, ec.double

    def c_add(p1, p2):
        cnt["add"] += 1
        return orig_add(p1, p2)

    def c_double(p1):
        cnt["double"] += 1
        return orig_double(p1)

    rows = []
    ec.add, ec.double = c_add, c_double
    try:
        rng = secrets.SystemRandom()
        for w in weights:
            k = (1 << 254) | sum(1 << b for b in rng.sample(range(254), w - 1))
            for label, fn in (("Double-and-Add", ec.multiply), ("лестница Монтгомери", ct.secure_multiply)):
                times = []
                for _ in range(reps):
                    cnt["add"] = cnt["double"] = 0
                    t0 = time.perf_counter()
                    fn(k, ec.G)
                    times.append((time.perf_counter() - t0) * 1e3)
                rows.append((w, label, cnt["add"], cnt["double"], statistics.median(times)))
                print(f"  {w:>4}  {label:<22}{cnt['add']:>14}{cnt['double']:>17}{rows[-1][4]:>11.1f}")
    finally:
        ec.add, ec.double = orig_add, orig_double
    return rows


def ct_analysis(trials=300, show=True):
    title("АНАЛИЗ ЗАЩИЩЁННОСТИ ОТ АТАК ПО ВРЕМЕНИ (CONSTANT-TIME)")
    br = branch_report()
    sq_rows, sq_data = sqrt_analysis(trials)
    ld_rows = ladder_analysis()
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    all_ops = sq_data[(SQRT_PRIMES[2][0], "классический")][0] + sq_data[(SQRT_PRIMES[2][0], "constant-time")][0]
    lo, hi = min(all_ops), max(all_ops) + 1
    bins = [lo + (hi - lo) * i / 50 for i in range(51)]           # общие интервалы для обеих серий
    for label, color in (("классический", "tab:red"), ("constant-time", "tab:green")):
        ops = sq_data[(SQRT_PRIMES[2][0], label)][0]
        axes[0].hist(ops, bins=bins, alpha=0.7, color=color, label=label)
    axes[0].set_title("Число умножений в sqrt, NIST P-224 (S = 96)", fontsize=10)
    axes[0].set_xlabel("модульных умножений за вызов")
    axes[0].set_ylabel("число аргументов")
    axes[0].legend()
    groups, labels = [], []
    for label in ("классический", "constant-time"):
        _, t_sq, t_ns = sq_data[(SQRT_PRIMES[1][0], label)]
        groups += [t_sq, t_ns]
        labels += [f"{label[:5]}.\nвычет", f"{label[:5]}.\nневычет"]
    axes[1].boxplot(groups, showfliers=False)
    axes[1].set_xticks(range(1, 5), labels)
    axes[1].set_title("Время sqrt по модулю 2^255 - 19, мкс", fontsize=10)
    for label, marker in (("Double-and-Add", "o-"), ("лестница Монтгомери", "s-")):
        pts = [(r[0], r[4]) for r in ld_rows if r[1] == label]
        axes[2].plot([a for a, _ in pts], [b for _, b in pts], marker, label=label)
    axes[2].set_title("Время k*G в зависимости от веса Хэмминга k", fontsize=10)
    axes[2].set_xlabel("вес Хэмминга w")
    axes[2].set_ylabel("мс")
    axes[2].set_ylim(bottom=0)
    axes[2].legend()
    for ax in axes:
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path("ct_analysis.png"), dpi=110)
    if show:
        plt.show()
    plt.close(fig)
    return br, sq_rows, ld_rows


# ======================================================================
def main():
    while True:
        print(f"\nМЕНЮ (лабораторная работа №4, вариант {VARIANT}: Ed25519, аффинные координаты,\n"
              "constant-time Тонелли-Шенкс)\n"
              " 1 — Самопроверка (параметры кривой, SHA-512, RFC 8032)\n"
              " 2 — Протокол ECDH (Алиса и Боб)\n"
              " 3 — Подпись и проверка Ed25519, искажение байта S\n"
              " 4 — Квадратный корень по модулю (constant-time и классический)\n"
              " 5 — Декомпрессия точки из 32 байт\n"
              " 6 — Анализ constant-time (ветвления, число операций, время)\n"
              " 0 — Выполнить всё и выйти")
        ch = input("Выбор: ").strip()
        try:
            if ch == "1":
                self_test()
            elif ch == "2":
                demo_ecdh(ask_hex("Секрет Алисы", ALICE_SEED_HEX, 32), ask_hex("Секрет Боба", BOB_SEED_HEX, 32))
            elif ch == "3":
                demo_sign(ask_hex("Секретный ключ", DEMO_SIGN_SEED_HEX, 32), ask_hex("Сообщение", DEMO_MSG_HEX))
            elif ch == "4":
                idx = int(input("Модуль: 0 — secp256k1, 1 — Ed25519, 2 — NIST P-224 [1]: ").strip() or "1")
                s = input("a (hex, Enter — случайный квадрат): ").strip()
                demo_sqrt(int(s, 16) if s else None, idx)
            elif ch == "5":
                demo_decompress(ask_hex("Сжатая точка", ec.encode_point(ec.G).hex(), 32))
            elif ch == "6":
                ct_analysis()
            elif ch == "0":
                self_test()
                demo_ecdh()
                demo_sign()
                demo_sqrt()
                demo_decompress()
                ct_analysis()
                break
        except (ValueError, OSError, IndexError) as e:
            print("Ошибка:", e)


if __name__ == "__main__":
    main()
