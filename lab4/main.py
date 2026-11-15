import hashlib
import sys

# МОДУЛЬ 1: АЛГЕБРА ЭЛЛИПТИЧЕСКИХ КРИВЫХ
# Точка на бесконечности — None, иначе кортеж (x, y)
class Curve:
    """Параметры эллиптической кривой y^2 = x^3 + a*x + b (mod p)."""
    __slots__ = ('p', 'a', 'b', 'q', 'Gx', 'Gy', 'G')

    def __init__(self, p: int, a: int, b: int, q: int, Gx: int, Gy: int):
        self.p = p
        self.a = a
        self.b = b
        self.q = q
        self.Gx = Gx
        self.Gy = Gy
        self.G = (Gx, Gy)

    def is_on_curve(self, P) -> bool:
        if P is None:
            return True
        x, y = P
        return (y * y - (x * x * x + self.a * x + self.b)) % self.p == 0


def inv_mod(a: int, p: int) -> int:
    """Обратный элемент по модулю p (расширенный алгоритм Евклида)."""
    if a == 0:
        raise ZeroDivisionError("0 не имеет обратного элемента")
    lm, hm = 1, 0
    low, high = a % p, p
    while low > 1:
        r = high // low
        nm, new = hm - lm * r, high - low * r
        lm, low, hm, high = nm, new, lm, low
    return lm % p


def point_add(curve: Curve, P, Q):
    """Сложение двух точек P + Q в аффинных координатах."""
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q

    if x1 == x2 and (y1 + y2) % curve.p == 0:
        return None
    if P == Q:
        return point_double(curve, P)

    s = ((y2 - y1) * inv_mod(x2 - x1, curve.p)) % curve.p
    x3 = (s * s - x1 - x2) % curve.p
    y3 = (s * (x1 - x3) - y1) % curve.p
    return (x3, y3)


def point_double(curve: Curve, P):
    """Удвоение точки P (P == Q) в аффинных координатах."""
    if P is None:
        return None
    x1, y1 = P
    if y1 == 0:
        return None
    s = ((3 * x1 * x1 + curve.a) * inv_mod(2 * y1, curve.p)) % curve.p
    x3 = (s * s - 2 * x1) % curve.p
    y3 = (s * (x1 - x3) - y1) % curve.p
    return (x3, y3)


def scalar_mult_double_and_add(curve: Curve, k: int, P):
    """Классический Double-and-Add (НЕ constant-time, для сравнения)."""
    if k == 0 or P is None:
        return None
    if k < 0:
        k = -k
        P = (P[0], (-P[1]) % curve.p)
    R = None
    Q = P
    while k:
        if k & 1:
            R = point_add(curve, R, Q)
        Q = point_double(curve, Q)
        k >>= 1
    return R

# МОДУЛЬ 3: CONSTANT-TIME ЗАЩИТА — ЛЕСТНИЦА МОНТГОМЕРИ
def cswap_points(swap_bit: int, P, Q):
    """
    Constant-time условный обмен двух точек (без ветвления по swap_bit).
    swap_bit == 1 -> обменять; 0 -> оставить.
    """
    p_present = 1 if P is not None else 0
    q_present = 1 if Q is not None else 0
    px, py = P if P is not None else (0, 0)
    qx, qy = Q if Q is not None else (0, 0)

    mask = -swap_bit  # 0x00..00 или 0xFF..FF

    dx = (px ^ qx) & mask
    px ^= dx
    qx ^= dx
    dy = (py ^ qy) & mask
    py ^= dy
    qy ^= dy
    df = (p_present ^ q_present) & mask
    p_present ^= df
    q_present ^= df

    P_new = (px, py) if p_present else None
    Q_new = (qx, qy) if q_present else None
    return P_new, Q_new


def scalar_mult_montgomery_ladder(curve: Curve, k: int, P):

    if k == 0 or P is None:
        return None
    if k < 0:
        k = -k
        P = (P[0], (-P[1]) % curve.p)

    R0 = None      # O
    R1 = P         # P
    for bit_char in bin(k)[2:]:
        bit = int(bit_char)
        # cswap включается при bit == 1: после обмена (R0,R1) = (старый R1, старый R0)
        # и стандартные операции R1 = R0+R1, R0 = 2*R0 дают классику для b=1.
        R0, R1 = cswap_points(bit, R0, R1)
        R1 = point_add(curve, R0, R1)
        R0 = point_double(curve, R0)
        R0, R1 = cswap_points(bit, R0, R1)
    return R0

# МОДУЛЬ 2: ПРОТОКОЛЫ ECDH И ЭЦП
def ecdh_generate_keypair(curve: Curve, d: int):
    Q = scalar_mult_montgomery_ladder(curve, d, curve.G)
    return d, Q


def ecdh_shared_secret(curve: Curve, d_own: int, Q_peer):
    K = scalar_mult_montgomery_ladder(curve, d_own, Q_peer)
    if K is None:
        raise ValueError("Общий секрет — точка на бесконечности")
    return K[0]


def _hash_to_int(data: bytes, q: int) -> int:
    h = hashlib.sha256(data).digest()
    return int.from_bytes(h, 'big') % q


def stb_sign(curve: Curve, d: int, message: bytes, k: int):
    """Выработка подписи (r, s) по демонстрационной схеме СТБ/ГОСТ."""
    if not (0 < k < curve.q):
        raise ValueError("k вне диапазона (0, q)")
    C = scalar_mult_montgomery_ladder(curve, k, curve.G)
    if C is None:
        raise ValueError("C = O, выберите другое k")
    r = C[0] % curve.q
    if r == 0:
        raise ValueError("r = 0, выберите другое k")
    e = _hash_to_int(message, curve.q)
    s = (r * d + k * e) % curve.q
    if s == 0:
        raise ValueError("s = 0, выберите другое k")
    return r, s


def stb_verify(curve: Curve, Q, message: bytes, r: int, s: int) -> bool:
    """Проверка подписи (r, s)."""
    if not (0 < r < curve.q and 0 < s < curve.q):
        return False
    e = _hash_to_int(message, curve.q)
    if e == 0:
        return False
    v = inv_mod(e, curve.q)
    z1 = (s * v) % curve.q
    z2 = (-r * v) % curve.q
    C1 = scalar_mult_montgomery_ladder(curve, z1, curve.G)
    C2 = scalar_mult_montgomery_ladder(curve, z2, Q)
    C_prime = point_add(curve, C1, C2)
    if C_prime is None:
        return False
    R = C_prime[0] % curve.q
    return R == r

# ПАРАМЕТРЫ КРИВОЙ И ТЕСТОВЫЕ ДАННЫЕ (HEX-СТРОКИ В КОДЕ)
P_HEX = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFFFFFFFFFF"
A_HEX = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFFFFFFFFFC"
B_HEX = "64210519E59C80E70FA7E9AB72243049FEB8DEECC146B9B1"
Q_HEX = "FFFFFFFFFFFFFFFFFFFFFFFF99DEF836146BC9B1B4D22831"
GX_HEX = "188DA80EB03090F67CBF20EB43A18800F4FF0AFD82FF1012"
GY_HEX = "07192B95FFC8DA78631011ED6B24CDD573F977A11E794811"

CURVE = Curve(
    int(P_HEX, 16), int(A_HEX, 16), int(B_HEX, 16),
    int(Q_HEX, 16), int(GX_HEX, 16), int(GY_HEX, 16)
)

# меню
def print_header():
    print("=" * 64)
    print(" Лабораторная работа №4 — Вариант 1")
    print(" СТБ 34.101.45 | Вейерштрасс / Аффинные | Montgomery Ladder")
    print("=" * 64)


def print_menu():
    print("\n--- МЕНЮ ---")
    print(" 1. Модуль 1: Показать параметры кривой и проверить G")
    print(" 2. Модуль 1: Сложение двух точек (Add)")
    print(" 3. Модуль 1: Удвоение точки (Double)")
    print(" 4. Модуль 1: Скалярное умножение Double-and-Add (не CT)")
    print(" 5. Модуль 3: Скалярное умножение Montgomery Ladder (CT)")
    print(" 6. Модуль 3: Демонстрация CSWAP")
    print(" 7. Модуль 2: Протокол ECDH (Алиса и Боб)")
    print(" 8. Модуль 2: Цикл «Подпись — Проверка»")
    print(" 9. Модуль 2: Отбраковка при искажении s")
    print("10. Запустить все тесты (полный прогон)")
    print(" 0. Выход")
    print("-" * 64)


def read_hex(prompt: str) -> int:
    s = input(prompt).strip()
    if s.lower().startswith("0x"):
        s = s[2:]
    return int(s, 16)


def read_point():
    print("  (точка на бесконечности — введите 'O')")
    x_str = input("  x (hex) или O: ").strip()
    if x_str.upper() == "O":
        return None
    if x_str.lower().startswith("0x"):
        x_str = x_str[2:]
    y_str = input("  y (hex): ").strip()
    if y_str.lower().startswith("0x"):
        y_str = y_str[2:]
    return (int(x_str, 16), int(y_str, 16))


def fmt_point(P) -> str:
    if P is None:
        return "O (точка на бесконечности)"
    return f"({P[0]:016x}, {P[1]:016x})"

def menu_show_curve():
    print("\n[Модуль 1] Параметры кривой:")
    print(f"  p  = 0x{CURVE.p:x}")
    print(f"  a  = 0x{CURVE.a:x}")
    print(f"  b  = 0x{CURVE.b:x}")
    print(f"  q  = 0x{CURVE.q:x}")
    print(f"  Gx = 0x{CURVE.Gx:x}")
    print(f"  Gy = 0x{CURVE.Gy:x}")
    print(f"  G лежит на кривой: {CURVE.is_on_curve(CURVE.G)}")
    print(f"  G в подгруппе: q*G == O -> "
          f"{scalar_mult_double_and_add(CURVE, CURVE.q, CURVE.G) is None}")

def menu_add():
    print("\n[Модуль 1] Сложение точек P + Q")
    print("Точка P:")
    P = read_point()
    print("Точка Q:")
    Q = read_point()
    if not CURVE.is_on_curve(P):
        print("  ! P не лежит на кривой")
        return
    if not CURVE.is_on_curve(Q):
        print("  ! Q не лежит на кривой")
        return
    R = point_add(CURVE, P, Q)
    print(f"  P + Q = {fmt_point(R)}")
    print(f"  На кривой: {CURVE.is_on_curve(R)}")

def menu_double():
    print("\n[Модуль 1] Удвоение точки 2P")
    print("Точка P:")
    P = read_point()
    if not CURVE.is_on_curve(P):
        print("  ! P не лежит на кривой")
        return
    R = point_double(CURVE, P)
    print(f"  2P = {fmt_point(R)}")
    print(f"  На кривой: {CURVE.is_on_curve(R)}")

def menu_double_and_add():
    print("\n[Модуль 1] Скалярное умножение k*P (Double-and-Add, не constant-time)")
    k = read_hex("  k (hex): ")
    print("Точка P (Enter = G):")
    P = read_point()
    if not CURVE.is_on_curve(P):
        print("  ! P не лежит на кривой")
        return
    R = scalar_mult_double_and_add(CURVE, k, P)
    print(f"  k*P = {fmt_point(R)}")

def menu_montgomery():
    print("\n[Модуль 3] Скалярное умножение k*P (Montgomery Ladder, constant-time)")
    k = read_hex("  k (hex): ")
    print("Точка P (Enter = G):")
    P = read_point()
    if not CURVE.is_on_curve(P):
        print("  ! P не лежит на кривой")
        return
    R = scalar_mult_montgomery_ladder(CURVE, k, P)
    print(f"  k*P = {fmt_point(R)}")

def menu_cswap():
    print("\n[Модуль 3] Демонстрация constant-time CSWAP")
    print("Точка A:")
    A = read_point()
    print("Точка B:")
    B = read_point()
    bit = read_hex("  swap_bit (0 или 1, hex): ")
    A2, B2 = cswap_points(bit, A, B)
    print(f"  После CSWAP({bit}):")
    print(f"    A' = {fmt_point(A2)}")
    print(f"    B' = {fmt_point(B2)}")

def menu_ecdh():
    print("\n[Модуль 2] Протокол ECDH")
    print("Введите личные ключи в hex (Enter — использовать тестовые):")
    dA_in = input("  dA (hex) или Enter: ").strip()
    dB_in = input("  dB (hex) или Enter: ").strip()

    dA = int(dA_in, 16) % CURVE.q if dA_in else int("1234567890ABCDEF1234567890ABCDEF", 16) % CURVE.q
    dB = int(dB_in, 16) % CURVE.q if dB_in else int("FEDCBA0987654321FEDCBA0987654321", 16) % CURVE.q

    print(f"\n  Алиса: dA = 0x{dA:016x}")
    print(f"  Боб:   dB = 0x{dB:016x}")

    _, QA = ecdh_generate_keypair(CURVE, dA)
    _, QB = ecdh_generate_keypair(CURVE, dB)
    print(f"  QA = {fmt_point(QA)}")
    print(f"  QB = {fmt_point(QB)}")

    KA = ecdh_shared_secret(CURVE, dA, QB)
    KB = ecdh_shared_secret(CURVE, dB, QA)
    print(f"  K_Алиса = 0x{KA:016x}")
    print(f"  K_Боб   = 0x{KB:016x}")
    if KA == KB:
        print("  [OK] Общий секрет совпадает")
    else:
        print("  [FAIL] Секреты не совпадают!")

def menu_sign_verify():
    print("\n[Модуль 2] Цикл «Подпись — Проверка»")
    d_in = input("  Личный ключ d (hex) или Enter (тест): ").strip()
    d = int(d_in, 16) % CURVE.q if d_in else int("A1B2C3D4E5F60718293A4B5C6D7E8F90", 16) % CURVE.q

    msg_hex = input("  Сообщение (hex) или Enter (\"Hello, Lab4!\"): ").strip()
    if not msg_hex:
        msg_hex = "48656C6C6F2C204C61623421"
    message = bytes.fromhex(msg_hex)

    k_in = input("  Эфемерный ключ k (hex) или Enter (тест): ").strip()
    k = int(k_in, 16) % CURVE.q if k_in else int("0F1E2D3C4B5A69788796A5B4C3D2E1F0", 16) % CURVE.q

    Q = scalar_mult_montgomery_ladder(CURVE, d, CURVE.G)
    print(f"  d = 0x{d:016x}")
    print(f"  Q = {fmt_point(Q)}")
    print(f"  M (hex) = {msg_hex}")

    r, s = stb_sign(CURVE, d, message, k)
    print(f"  Подпись: r = 0x{r:016x}, s = 0x{s:016x}")

    ok = stb_verify(CURVE, Q, message, r, s)
    print(f"  Проверка: {'УСПЕХ' if ok else 'ОШИБКА'}")

def menu_tamper():
    print("\n[Модуль 2] Отбраковка при искажении s")
    d = int("A1B2C3D4E5F60718293A4B5C6D7E8F90", 16) % CURVE.q
    message = bytes.fromhex("48656C6C6F2C204C61623421")
    k = int("0F1E2D3C4B5A69788796A5B4C3D2E1F0", 16) % CURVE.q

    Q = scalar_mult_montgomery_ladder(CURVE, d, CURVE.G)
    r, s = stb_sign(CURVE, d, message, k)
    print(f"  Оригинал: r = 0x{r:016x}, s = 0x{s:016x}")
    ok = stb_verify(CURVE, Q, message, r, s)
    print(f"  Проверка оригинала: {'УСПЕХ' if ok else 'ОШИБКА'}")

    s_bad = s ^ 1
    print(f"  Искажён:  r = 0x{r:016x}, s' = 0x{s_bad:016x}")
    ok_bad = stb_verify(CURVE, Q, message, r, s_bad)
    print(f"  Проверка искажённой: "
          f"{'УСПЕХ (ОШИБКА!)' if ok_bad else 'ОТКЛОНЕНА (корректно)'}")

def menu_run_all():
    print("\n========== ПОЛНЫЙ ПРОГОН ТЕСТОВ ==========")

    # 1. Кривая
    print("\n[1] Параметры кривой")
    print(f"  G на кривой: {CURVE.is_on_curve(CURVE.G)}")
    print(f"  q*G == O: {scalar_mult_double_and_add(CURVE, CURVE.q, CURVE.G) is None}")

    # 2. Montgomery Ladder == Double-and-Add
    print("\n[2] Сравнение Montgomery Ladder и Double-and-Add")
    k_test = 0xDEADBEEF
    R1 = scalar_mult_montgomery_ladder(CURVE, k_test, CURVE.G)
    R2 = scalar_mult_double_and_add(CURVE, k_test, CURVE.G)
    print(f"  Montgomery = Double-and-Add: {R1 == R2}")

    # 3. ECDH
    print("\n[3] ECDH")
    dA = int("1234567890ABCDEF1234567890ABCDEF", 16) % CURVE.q
    dB = int("FEDCBA0987654321FEDCBA0987654321", 16) % CURVE.q
    _, QA = ecdh_generate_keypair(CURVE, dA)
    _, QB = ecdh_generate_keypair(CURVE, dB)
    KA = ecdh_shared_secret(CURVE, dA, QB)
    KB = ecdh_shared_secret(CURVE, dB, QA)
    print(f"  K_Алиса = 0x{KA:016x}")
    print(f"  K_Боб   = 0x{KB:016x}")
    print(f"  Совпадают: {KA == KB}")

    # 4. Подпись-проверка
    print("\n[4] Цикл подпись-проверка")
    d = int("A1B2C3D4E5F60718293A4B5C6D7E8F90", 16) % CURVE.q
    message = bytes.fromhex("48656C6C6F2C204C61623421")
    k = int("0F1E2D3C4B5A69788796A5B4C3D2E1F0", 16) % CURVE.q
    Q = scalar_mult_montgomery_ladder(CURVE, d, CURVE.G)
    r, s = stb_sign(CURVE, d, message, k)
    print(f"  r = 0x{r:016x}, s = 0x{s:016x}")
    print(f"  Проверка корректной: {stb_verify(CURVE, Q, message, r, s)}")

    # 5. Искажение
    print("\n[5] Искажение s")
    s_bad = s ^ 1
    print(f"  s' = 0x{s_bad:016x}")
    print(f"  Проверка искажённой: {stb_verify(CURVE, Q, message, r, s_bad)}")

    print("\n========== КОНЕЦ ПРОГОНА ==========")

def main():
    print_header()
    if not CURVE.is_on_curve(CURVE.G):
        print("ОШИБКА: G не лежит на кривой!")
        sys.exit(1)

    handlers = {
        '1': menu_show_curve,
        '2': menu_add,
        '3': menu_double,
        '4': menu_double_and_add,
        '5': menu_montgomery,
        '6': menu_cswap,
        '7': menu_ecdh,
        '8': menu_sign_verify,
        '9': menu_tamper,
        '10': menu_run_all,
    }

    while True:
        print_menu()
        choice = input("Выбор: ").strip()
        if choice == '0':
            print("Выход.")
            break
        handler = handlers.get(choice)
        if handler is None:
            print("Неверный пункт меню.")
            continue
        try:
            handler()
        except Exception as e:
            print(f"  ! Ошибка: {e}")


if __name__ == "__main__":
    main()