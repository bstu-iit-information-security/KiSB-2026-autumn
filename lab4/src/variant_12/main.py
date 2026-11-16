"""ЛР №4, вариант 12: СТБ 34.101.45, кривая Вейерштрасса, аффинные координаты.
Задача варианта: constant-time генерация эфемерного ключа k.

Запуск демонстрации (вывод дублируется в lab4_output.txt):
    python3 main.py

Командный режим (только сырые hex-значения):
    python3 main.py keygen
    python3 main.py pub    <d>
    python3 main.py ecdh   <d> <Qx> <Qy>
    python3 main.py hash   <msg_hex>
    python3 main.py sign   <d> <msg_hex>
    python3 main.py verify <Qx> <Qy> <msg_hex> <r||s>
"""

import os
import random
import statistics
import sys
import time

import protocols as pr
from belt_hash import belt_hash
from ct import (ct_random_scalar, naive_random_scalar, secure_multiply,
                fixed_length_scalar, DEFAULT_ITERATIONS)
from ec import BIGN256 as C, Point, is_probable_prime

HERE = os.path.dirname(os.path.abspath(__file__))

# Тестовые сообщения и их хэши belt-hash (заданы в коде в hex, как требует задание).
TEST_MESSAGES = [
    ("48656C6C6F2C206269676E21",                       # "Hello, bign!"
     "92E5F8B9D6B608DEF9464FF66CC38FA78AF1F86D99762C0DC0E526FC95498E2B"),
    ("B194BAC80A08F53B366D008E58",                     # контрольный пример belt-hash
     "ABEF9725D4C5A83597A367D14494CC2542F20F659DDFECC961A3EC550CBA8C75"),
    ("D09BD0B0D0B1D0BED180D0B0D182D0BED180D0BDD0B0D18F20D180D0B0D0B1D0BED182D0B0"
     "20E28496342C20D0B2D0B0D180D0B8D0B0D0BDD182203132",  # "Лабораторная работа №4, вариант 12"
     "459D3A4D9F5D04D290D6D7F125214F8CC481B0A2DFACFE4ADD7BDA72C310F513"),
]

# Контрольные примеры belt-hash из СТБ 34.101.31: X = первые n байт H-блока.
BELT_HASH_VECTORS = [
    ("B194BAC80A08F53B366D008E58",
     "ABEF9725D4C5A83597A367D14494CC2542F20F659DDFECC961A3EC550CBA8C75"),
    ("B194BAC80A08F53B366D008E584A5DE48504FA9D1BB6C7AC252E72C202FDCE0D",
     "749E4C3653AECE5E48DB4761227742EB6DBE13F4A80F7BEFF1A9CF8D10EE7786"),
    ("B194BAC80A08F53B366D008E584A5DE48504FA9D1BB6C7AC252E72C202FDCE0D"
     "5BE3D61217B96181FE6786AD716B890B",
     "9D02EE446FB6A29FE5C982D4B13AF9D3E90861BC4CEF27CF306BFB0B174A154A"),
]

# Контрольный пример ключей из СТБ 34.101.45 (там числа записаны little-endian,
# здесь — обычная big-endian запись).
STB_D = "69E273C25F23790C9E423207ED1F283418F2749C32F033456739734BB8B5661F"
STB_QX = "D07F8590A8F77BF84F1EF10C6DE44CF5DDD52B4C9DE4CE3FE0799D1750561ABD"
STB_QY = "909AD9B92A4DB89A4A050959DA2E0C1926281B466D68913417C8E86103A6C67A"


class Tee:
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")
        self.out = sys.stdout

    def write(self, s):
        self.out.write(s)
        self.f.write(s)

    def flush(self):
        self.out.flush()
        self.f.flush()


def title(s):
    print()
    print("=" * 78)
    print(s)
    print("=" * 78)


def H(x):
    return pr.int_to_hex(x)


def ok(flag):
    return "OK" if flag else "ОШИБКА"


# --------------------------------------------------------------------------

def show_curve():
    title("1. Параметры кривой bign-curve256v1 (СТБ 34.101.45) и самопроверка модуля 1")
    print(f"p  = {H(C.p)}")
    print(f"a  = {H(C.a)}")
    print(f"b  = {H(C.b)}")
    print(f"q  = {H(C.q)}")
    print(f"G  : x = {H(C.G.x)}\n     y = {H(C.G.y)}")
    checks = [
        ("4a^3 + 27b^2 != 0 (кривая невырождена)", C.is_nonsingular()),
        ("p простое", is_probable_prime(C.p)),
        ("q простое", is_probable_prime(C.q)),
        ("G лежит на кривой", C.is_on_curve(C.G)),
        ("q·G = O", C.multiply(C.q, C.G).inf == 1),
    ]
    rnd = random.Random(4)
    P = C.multiply(rnd.randrange(1, C.q), C.G)
    Q = C.multiply(rnd.randrange(1, C.q), C.G)
    R = C.multiply(rnd.randrange(1, C.q), C.G)
    checks += [
        ("P + P = 2P (сложение согласовано с удвоением)", C.add(P, P) == C.double(P)),
        ("P + (-P) = O", C.add(P, C.neg(P)).inf == 1),
        ("P + O = P", C.add(P, Point.infinity()) == P),
        ("(P + Q) + R = P + (Q + R)", C.add(C.add(P, Q), R) == C.add(P, C.add(Q, R))),
        ("P + Q и 2P лежат на кривой", C.is_on_curve(C.add(P, Q)) and C.is_on_curve(C.double(P))),
    ]
    for name, flag in checks:
        print(f"  {name:<48} {ok(flag)}")
    return all(f for _, f in checks)


def show_hash():
    title("2. Хэш-функция belt-hash (СТБ 34.101.31) на шифре БелТ из ЛР №3")
    good = True
    for x, y in BELT_HASH_VECTORS:
        got = belt_hash(bytes.fromhex(x)).hex().upper()
        good &= got == y
        print(f"X = {x}  ({len(x) // 2} байт)")
        print(f"  H(X) = {got}  {ok(got == y)}")
    return good


def show_keys():
    title("3. Контрольный пример ключей СТБ 34.101.45: Q = d·G")
    d = pr.hex_to_int(STB_D)
    Q = pr.public_key(d)
    good = H(Q.x) == STB_QX and H(Q.y) == STB_QY
    print(f"d     = {STB_D}")
    print(f"Q     : x = {H(Q.x)}\n        y = {H(Q.y)}")
    print(f"ожид. : x = {STB_QX}\n        y = {STB_QY}")
    same = Q == C.multiply(d, C.G)
    print(f"SecureMultiply (лестница) совпадает с эталоном: {ok(good)}; с Double-and-Add: {ok(same)}")
    return good and same


def show_ecdh():
    title("4. Протокол ECDH")
    dA, QA = pr.generate_keypair()
    dB, QB = pr.generate_keypair()
    KA = pr.ecdh_shared_point(dA, QB)
    KB = pr.ecdh_shared_point(dB, QA)
    print("Алиса:")
    print(f"  d_A = {H(dA)}")
    print(f"  Q_A : x = {H(QA.x)}\n        y = {H(QA.y)}")
    print("Боб:")
    print(f"  d_B = {H(dB)}")
    print(f"  Q_B : x = {H(QB.x)}\n        y = {H(QB.y)}")
    print("Обмен открытыми ключами Q_A, Q_B.")
    print(f"Алиса: K = d_A·Q_B : x = {H(KA.x)}")
    print(f"Боб:   K = d_B·Q_A : x = {H(KB.x)}")
    good = KA == KB
    print(f"Общий секрет (x-координата) совпадает: {ok(good)}")
    bad = Point(QB.x, (QB.y + 1) % C.p)
    try:
        pr.ecdh_shared_point(dA, bad)
        rejected = False
    except ValueError as e:
        rejected = True
        print(f"Подменённый Q_B (y + 1, точка вне кривой) отклонён: {e}")
    return good and rejected


def show_signatures():
    title("5. ЭЦП СТБ 34.101.45: подпись и проверка")
    d = pr.hex_to_int(STB_D)
    Q = pr.public_key(d)
    print(f"Ключ подписи d = {STB_D} (контрольный пример стандарта)")
    good = True
    last = None
    for msg_hex, hash_hex in TEST_MESSAGES:
        msg = bytes.fromhex(msg_hex)
        h = pr.message_hash(msg)
        e = pr.hash_to_e(h)
        sig = pr.sign(msg, d)
        valid = pr.verify(msg, Q, sig)
        good &= valid and h.hex().upper() == hash_hex
        print(f"\nM    = {msg_hex}")
        print(f"H(M) = {h.hex().upper()}  (ожидается {ok(h.hex().upper() == hash_hex)})")
        print(f"e    = {H(e)}")
        print(f"r    = {H(sig[0])}")
        print(f"s    = {H(sig[1])}")
        print(f"Проверка подписи: {'верна' if valid else 'НЕВЕРНА'}")
        last = (msg, sig)

    msg, (r, s) = last
    print("\nОтбраковка искажённых данных (последнее сообщение):")
    sb = bytearray(s.to_bytes(32, "big"))
    sb[17] ^= 0x01
    s_bad = int.from_bytes(sb, "big")
    rb = bytearray(r.to_bytes(32, "big"))
    rb[0] ^= 0x80
    cases = [
        (f"искажён 1 байт s (байт 17: {s.to_bytes(32, 'big')[17]:02X} -> {sb[17]:02X})", msg, Q, (r, s_bad)),
        ("искажён 1 байт r", msg, Q, (int.from_bytes(rb, "big") % C.q, s)),
        ("изменён 1 байт сообщения", msg[:-1] + bytes([msg[-1] ^ 1]), Q, (r, s)),
        ("чужой открытый ключ", msg, C.double(Q), (r, s)),
        ("s = 0", msg, Q, (r, 0)),
        ("s = q", msg, Q, (r, C.q)),
    ]
    print(f"  s исходная = {H(s)}")
    print(f"  s искаж.   = {H(s_bad)}")
    for name, m, key, sig in cases:
        v = pr.verify(m, key, sig)
        good &= not v
        print(f"  {name:<44} -> {'принята (ОШИБКА)' if v else 'отклонена'}")
    return good


# --------------------------------------------------------------------------
# Исследование: constant-time генерация k
# --------------------------------------------------------------------------

class CountingRng:
    """Детерминированный ГПСЧ для эксперимента, считает число обращений."""

    def __init__(self, seed):
        self.r = random.Random(seed)
        self.calls = 0

    def __call__(self, bits):
        self.calls += 1
        return self.r.getrandbits(bits)


def first_valid_index(seed, q):
    """Номер первого допустимого кандидата для данного seed (для анализа)."""
    rng = CountingRng(seed)
    bits = q.bit_length()
    i = 0
    while True:
        i += 1
        k = rng(bits)
        if 0 < k < q:
            return i


def timed(fn, seed, repeat=7):
    best = float("inf")
    for _ in range(repeat):
        rng = CountingRng(seed)
        t = time.perf_counter_ns()
        fn(rng)
        best = min(best, time.perf_counter_ns() - t)
    return best


def pearson(xs, ys):
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    return sxy / (sx * sy) if sx and sy else 0.0


def show_k_generation(n_runs=1500):
    title("6. Задача варианта: constant-time генерация эфемерного ключа k")
    import math
    q = C.q
    p_rej = (2 ** q.bit_length() - q + 1) / 2 ** q.bit_length()
    print(f"Для q кривой bign-curve256v1 кандидат из {q.bit_length()} бит отбрасывается с вероятностью")
    print(f"(2^256 - q + 1) / 2^256 ≈ 2^{math.log2(p_rej):.1f}: утечка почти не проявляется.")
    print("Чтобы эффект был виден, эксперимент проводится и для «неудобной» границы")
    q_demo = 2 ** 255 + 1
    print(f"q_demo = 2^255 + 1 = {H(q_demo)}: отбрасывается ~50% 256-битных кандидатов.")

    # корректность и неизменное число обращений к ГПСЧ
    calls = set()
    in_range = True
    for seed in range(300):
        for qq in (q, q_demo):
            rng = CountingRng(seed)
            k = ct_random_scalar(qq, rng)
            calls.add(rng.calls)
            in_range &= 0 < k < qq
            in_range &= k == _first_valid_value(seed, qq)
    print(f"\nct_random_scalar: k в (0, q) и равен первому допустимому кандидату: {ok(in_range)};")
    print(f"число обращений к ГПСЧ за вызов (по 600 вызовам): {sorted(calls)} — всегда {DEFAULT_ITERATIONS}.")

    # время против числа отброшенных кандидатов
    attempts, t_naive, t_ct = [], [], []
    for seed in range(n_runs):
        a = first_valid_index(seed, q_demo)
        attempts.append(a)
        t_naive.append(timed(lambda rng: naive_random_scalar(q_demo, rng), seed))
        t_ct.append(timed(lambda rng: ct_random_scalar(q_demo, rng), seed))

    print(f"\n{n_runs} генераций k для q_demo (время — минимум из 7 повторов, нс):")
    print(f"{'попыток до успеха':>18} | {'доля':>6} | {'наивный, нс':>12} | {'constant-time, нс':>18}")
    groups = sorted(set(attempts))
    for g in groups:
        idx = [i for i, a in enumerate(attempts) if a == g]
        if len(idx) < 5:
            continue
        mn = statistics.median(t_naive[i] for i in idx)
        mc = statistics.median(t_ct[i] for i in idx)
        print(f"{g:>18} | {len(idx) / n_runs:>6.1%} | {mn:>12.0f} | {mc:>18.0f}")
    rn = pearson(attempts, t_naive)
    rc = pearson(attempts, t_ct)
    print(f"Корреляция Пирсона «число отброшенных кандидатов — время»:")
    print(f"  наивный цикл while:          r = {rn:+.3f}")
    print(f"  constant-time (N = {DEFAULT_ITERATIONS}):     r = {rc:+.3f}")
    print("Вывод: у наивного генератора время линейно растёт с числом отброшенных")
    print("кандидатов и выдаёт его; у constant-time генератора время не зависит от него.")
    return in_range and calls == {DEFAULT_ITERATIONS} and abs(rc) < 0.2 < rn


def _first_valid_value(seed, q):
    rng = CountingRng(seed)
    bits = q.bit_length()
    while True:
        k = rng(bits)
        if 0 < k < q:
            return k


def show_spa():
    title("7. SPA/Timing: Double-and-Add против лестницы Монтгомери (SecureMultiply)")
    rnd = random.Random(7)
    n = C.q.bit_length()

    def key_with_weight(w):
        while True:
            bits = rnd.sample(range(n - 1), w - 1) + [n - 2]
            k = sum(1 << b for b in set(bits))
            if 0 < k < C.q:
                return k

    print(f"{'вес Хэмминга d':>15} | {'Double-and-Add, мс':>18} | {'сложений':>8} | {'лестница, мс':>12} | {'итераций':>8}")
    rows = []
    for w in (16, 64, 128, 192, 240):
        ks = [key_with_weight(w) for _ in range(3)]
        td = min(_time_ms(lambda: C.multiply(k, C.G)) for k in ks)
        tl = min(_time_ms(lambda: secure_multiply(C, k, C.G)) for k in ks)
        rows.append((w, td, tl))
        print(f"{w:>15} | {td:>18.2f} | {w - 1:>8} | {tl:>12.2f} | {n:>8}")
    print("Double-and-Add выполняет столько сложений, сколько единиц в d: время выдаёт вес ключа,")
    print("а по трассе потребления видна последовательность D/DA, то есть сами биты.")
    print("Лестница всегда выполняет bitlen(q) итераций «сложение + удвоение», точки")
    print(f"переставляются CSWAP по маске; скаляр приводится к фиксированной длине "
          f"(k + q или k + 2q,\nбит {n} всегда равен 1).")
    k_short = 5
    print(f"Пример: k = 5 -> k' = k + 2q = {fixed_length_scalar(k_short, C.q):066X} "
          f"({fixed_length_scalar(k_short, C.q).bit_length()} бит)")


def _time_ms(fn):
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000


# --------------------------------------------------------------------------
# Командный режим
# --------------------------------------------------------------------------

def cli(argv):
    cmd, args = argv[0], argv[1:]
    if cmd == "keygen":
        d, Q = pr.generate_keypair()
        print(f"d  = {H(d)}\nQx = {H(Q.x)}\nQy = {H(Q.y)}")
    elif cmd == "pub":
        Q = pr.public_key(pr.hex_to_int(args[0]))
        print(f"Qx = {H(Q.x)}\nQy = {H(Q.y)}")
    elif cmd == "ecdh":
        d = pr.hex_to_int(args[0])
        Q = Point(pr.hex_to_int(args[1]), pr.hex_to_int(args[2]))
        K = pr.ecdh_shared_point(d, Q)
        print(f"Kx = {H(K.x)}\nKy = {H(K.y)}")
    elif cmd == "hash":
        print(belt_hash(bytes.fromhex(args[0])).hex().upper())
    elif cmd == "sign":
        sig = pr.sign(bytes.fromhex(args[1]), pr.hex_to_int(args[0]))
        print(f"r  = {H(sig[0])}\ns  = {H(sig[1])}\nr||s = {pr.signature_to_hex(sig)}")
    elif cmd == "verify":
        Q = Point(pr.hex_to_int(args[0]), pr.hex_to_int(args[1]))
        res = pr.verify(bytes.fromhex(args[2]), Q, pr.signature_from_hex(args[3]))
        print("VALID" if res else "INVALID")
        return 0 if res else 1
    else:
        print(__doc__)
        return 2
    return 0


def main():
    if len(sys.argv) > 1:
        return cli(sys.argv[1:])
    sys.stdout = Tee(os.path.join(HERE, "lab4_output.txt"))
    print("ЛР №4. Арифметика точечных групп эллиптических кривых, ECDH и ЭЦП")
    print("Вариант 12: СТБ 34.101.45, кривая Вейерштрасса, аффинные координаты;")
    print("constant-time генерация эфемерного ключа k (Rejection Sampling).")
    results = [
        ("параметры и групповой закон", show_curve()),
        ("belt-hash", show_hash()),
        ("контрольный пример ключей", show_keys()),
        ("ECDH", show_ecdh()),
        ("подпись и проверка", show_signatures()),
        ("constant-time генерация k", show_k_generation()),
    ]
    show_spa()
    title("Итог")
    for name, flag in results:
        print(f"  {name:<30} {ok(flag)}")
    sys.stdout.flush()
    return 0 if all(f for _, f in results) else 1


if __name__ == "__main__":
    sys.exit(main())
