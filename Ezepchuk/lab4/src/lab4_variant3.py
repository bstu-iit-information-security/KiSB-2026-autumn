#!/usr/bin/env python3
"""Лабораторная 4, вариант 3. Python 3.10+, без сторонних пакетов.

Запуск тестов: python lab4_variant3.py
Команды: keygen; pub D; ecdh D QX QY; sign D MESSAGE_HEX;
         verify QX QY MESSAGE_HEX R S
Все данные вводятся hex без 0x. Для пустого сообщения передать "".

Модули логически разделены, весь код находится в одном файле.
ВАЖНО: фиксированное число шагов инверсии не делает Python int
constant-time. Арифметика интерпретатора, выделение памяти и особые
случаи точек могут зависеть от данных. Это учебная реализация алгоритма
Ферма, не эквивалент защищённому native-коду предыдущей версии.
Вложенных динамических контейнеров нет. Полностью статическое хранение
BigInt средствами чистого Python невозможно.
"""
from dataclasses import dataclass
import hashlib
import secrets
import sys

# МОДУЛЬ 3. Инверсия через малую теорему Ферма.
class Protection:
    @staticmethod
    def inverse(a: int, modulus: int) -> int:
        """modulus — фиксированное доверенное простое число p или q.

        Ровно 256 итераций и 2 умножения на итерацию для secp256k1.
        Выбор результата — арифметической маской без if по биту a.
        Это постоянная структура алгоритма, а НЕ гарантия времени Python.
        """
        if not 0 < a < modulus:
            raise ValueError('Для инверсии требуется 0 < a < modulus')
        exponent = modulus - 2  # публичная константа
        result = 1
        for i in range(modulus.bit_length() - 1, -1, -1):
            square = result * result % modulus
            product = square * a % modulus
            mask = -((exponent >> i) & 1)
            result = square ^ ((square ^ product) & mask)
        return result

# МОДУЛЬ 1. Арифметика эллиптической кривой, аффинные координаты.
@dataclass(frozen=True, slots=True)
class Point:
    x: int = 0
    y: int = 0
    infinity: bool = True

O = Point()

class Curve:
    p = int('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F', 16)
    a = int('00', 16)
    b = int('07', 16)
    q = int('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141', 16)
    G = Point(
        int('79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798', 16),
        int('483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8', 16), False)

    def on_curve(self, P: Point) -> bool:
        return P.infinity or (0 <= P.x < self.p and 0 <= P.y < self.p
            and (P.y * P.y - P.x ** 3 - self.a * P.x - self.b) % self.p == 0)

    def add(self, P: Point, Q: Point) -> Point:
        if P.infinity:
            return Q
        if Q.infinity:
            return P
        if P.x == Q.x:
            if P.y != Q.y or P.y == 0:
                return O
            numerator = (3 * P.x * P.x + self.a) % self.p
            denominator = 2 * P.y % self.p
        else:
            numerator = (Q.y - P.y) % self.p
            denominator = (Q.x - P.x) % self.p
        slope = numerator * Protection.inverse(denominator, self.p) % self.p
        x = (slope * slope - P.x - Q.x) % self.p
        y = (slope * (P.x - x) - P.y) % self.p
        return Point(x, y, False)

    def double_add(self, scalar: int, P: Point) -> Point:
        if scalar < 0:
            raise ValueError('Отрицательный скаляр')
        R = O
        for i in range(scalar.bit_length() - 1, -1, -1):
            R = self.add(R, R)
            if (scalar >> i) & 1:
                R = self.add(R, P)
        return R

    @staticmethod
    def cswap(A: Point, B: Point, bit: int) -> tuple[Point, Point]:
        mask = -bit
        x = (A.x ^ B.x) & mask
        y = (A.y ^ B.y) & mask
        infinity = (int(A.infinity) ^ int(B.infinity)) & mask
        return (Point(A.x ^ x, A.y ^ y, bool(int(A.infinity) ^ infinity)),
                Point(B.x ^ x, B.y ^ y, bool(int(B.infinity) ^ infinity)))

    def ladder(self, scalar: int, P: Point) -> Point:
        if not 0 <= scalar < (1 << 256):
            raise ValueError('Скаляр должен занимать не более 256 бит')
        R0, R1 = O, P
        for i in range(255, -1, -1):
            bit = (scalar >> i) & 1
            R0, R1 = self.cswap(R0, R1, bit)
            total = self.add(R0, R1)
            doubled = self.add(R0, R0)
            R0, R1 = doubled, total
            R0, R1 = self.cswap(R0, R1, bit)
        return R0

    def valid_public(self, P: Point) -> bool:
        return not P.infinity and self.on_curve(P) and self.double_add(self.q, P).infinity

# МОДУЛЬ 2. Генерация ключей, ECDH и ECDSA.
class Protocols:
    def __init__(self):
        self.curve = Curve()

    def validate_secret(self, d: int) -> None:
        if not 0 < d < self.curve.q:
            raise ValueError('Требуется 0 < секретный ключ < q')

    def random_secret(self) -> int:
        return secrets.randbelow(self.curve.q - 1) + 1

    def public_key(self, d: int) -> Point:
        self.validate_secret(d)
        return self.curve.ladder(d, self.curve.G)

    def ecdh(self, d: int, Q: Point) -> bytes:
        self.validate_secret(d)
        if not self.curve.valid_public(Q):
            raise ValueError('Недопустимый открытый ключ')
        R = self.curve.ladder(d, Q)
        if R.infinity:
            raise ValueError('Общая точка равна O')
        # Сырой секрет, для прикладного шифрования нужны KDF и аутентификация.
        return R.x.to_bytes(32, 'big')

    @staticmethod
    def digest(message_hex: str) -> int:
        if len(message_hex) % 2 or any(c not in '0123456789abcdefABCDEF' for c in message_hex):
            raise ValueError('Сообщение должно содержать чётное число hex-цифр')
        return int.from_bytes(hashlib.sha256(bytes.fromhex(message_hex)).digest(), 'big')

    def sign_hash(self, d: int, e: int) -> tuple[int, int]:
        self.validate_secret(d)
        q = self.curve.q
        while True:
            k = self.random_secret()
            C = self.curve.ladder(k, self.curve.G)
            r = C.x % q
            if r == 0:
                continue
            s = Protection.inverse(k, q) * (e + r * d) % q
            if s != 0:
                return r, s

    def verify_hash(self, Q: Point, e: int, signature: tuple[int, int]) -> bool:
        r, s = signature
        q = self.curve.q
        if not (0 < r < q and 0 < s < q) or not self.curve.valid_public(Q):
            return False
        w = Protection.inverse(s, q)
        u1, u2 = e * w % q, r * w % q
        C = self.curve.add(self.curve.double_add(u1, self.curve.G),
                           self.curve.double_add(u2, Q))
        return not C.infinity and C.x % q == r

# Hex-интерфейс и встроенные тесты.
def parse_hex(value: str) -> int:
    if not 1 <= len(value) <= 64 or any(c not in '0123456789abcdefABCDEF' for c in value):
        raise ValueError('Ожидается от 1 до 64 hex-цифр без 0x')
    return int(value, 16)

def print_point(name: str, P: Point) -> None:
    print(f'{name}.infinity={int(P.infinity)}')
    if not P.infinity:
        print(f'{name}.x={P.x:064X}\n{name}.y={P.y:064X}')

def selftest(p: Protocols) -> None:
    count = 0
    def check(condition: bool, name: str) -> None:
        nonlocal count
        if not condition:
            raise AssertionError(name)
        count += 1
        print('PASS', name)
    c = p.curve
    check(c.on_curve(c.G), 'G on curve')
    check(c.double_add(c.q, c.G).infinity, 'qG = O')
    check(c.add(c.G, O) == c.G, 'G + O = G')
    check(c.add(c.G, Point(c.G.x, -c.G.y % c.p, False)).infinity, 'G + (-G) = O')
    check(c.ladder(0, c.G).infinity, '0G = O')
    for k in range(1, 13):
        check(c.ladder(k, c.G) == c.double_add(k, c.G), f'ladder equals double-and-add k={k:X}')
    for modulus in (c.p, c.q):
        for a in (1, 2, 3, modulus - 1):
            inverse = Protection.inverse(a, modulus)
            check(a * inverse % modulus == 1 and inverse == pow(a, -1, modulus), 'Fermat inverse equals Python inverse')
    try:
        Protection.inverse(0, c.p)
    except ValueError:
        check(True, 'zero inverse rejected')
    else:
        check(False, 'zero inverse rejected')
    # Известные координаты 2G — независимый эталон для арифметики.
    expected = Point(
        int('C6047F9441ED7D6D3045406E95C07CD85C778E4B8CEF3CA7ABAC09B95C709EE5', 16),
        int('1AE168FEA63DC339A3C58419466CEAEEF7F632653266D0E1236431A950CFE52A', 16), False)
    check(c.add(c.G, c.G) == expected, 'known secp256k1 2G vector')
    da, db = int('123456789ABCDEF', 16), int('FEDCBA987654321', 16)
    A, B = p.public_key(da), p.public_key(db)
    sa, sb = p.ecdh(da, B), p.ecdh(db, A)
    check(sa == sb, 'ECDH equal secrets')
    check(sa.hex().upper() == 'D8EB786721FF3735E2E64B90EB05B720AA7A65EECC93E22BAB62D13580565C78', 'ECDH agrees with C++ version')
    print_point('QA', A)
    print_point('QB', B)
    print(f'Shared_A={sa.hex().upper()}\nShared_B={sb.hex().upper()}')
    messages = ('', '616263', '4C6162342056617269616E742033')
    hashes = ('E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855',
              'BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD',
              '799167108315FAE29282BA2A0A7CCCB36478A1D69D44FA5432F40E80604C52A8')
    for message, expected_hash in zip(messages, hashes):
        e = p.digest(message)
        check(e == int(expected_hash, 16), 'SHA-256 known vector')
        r, s = p.sign_hash(da, e)
        print(f'message={message}\nhash={e:064X}\nr={r:064X}\ns={s:064X}')
        check(p.verify_hash(A, e, (r, s)), 'valid signature')
        changed = bytearray(s.to_bytes(32, 'big'))
        changed[-1] ^= 1
        check(not p.verify_hash(A, e, (r, int.from_bytes(changed, 'big'))), 'one byte of s changed: rejected')
        check(not p.verify_hash(A, p.digest(message + '00'), (r, s)), 'changed message rejected')
        check(not p.verify_hash(B, e, (r, s)), 'wrong public key rejected')
    check(not p.verify_hash(O, 1, (1, 1)), 'infinity public key rejected')
    check(not p.verify_hash(A, 1, (0, 1)), 'r = 0 rejected')
    check(not p.verify_hash(A, 1, (1, c.q)), 's = q rejected')
    check(not c.valid_public(Point(c.G.x, 0, False)), 'off-curve key rejected')
    check(c.valid_public(p.public_key(p.random_secret())), 'random key generation')
    print(f'ALL TESTS PASSED: {count}')

def main(args: list[str]) -> None:
    p = Protocols()
    if not args or args == ['--test']:
        selftest(p)
    elif args == ['keygen']:
        d = p.random_secret()
        print(f'd={d:064X}')
        print_point('Q', p.public_key(d))
    elif len(args) == 2 and args[0] == 'pub':
        print_point('Q', p.public_key(parse_hex(args[1])))
    elif len(args) == 4 and args[0] == 'ecdh':
        result = p.ecdh(parse_hex(args[1]), Point(parse_hex(args[2]), parse_hex(args[3]), False))
        print('shared=' + result.hex().upper())
    elif len(args) == 3 and args[0] == 'sign':
        r, s = p.sign_hash(parse_hex(args[1]), p.digest(args[2]))
        print(f'r={r:064X}\ns={s:064X}')
    elif len(args) == 6 and args[0] == 'verify':
        Q = Point(parse_hex(args[1]), parse_hex(args[2]), False)
        valid = p.verify_hash(Q, p.digest(args[3]), (parse_hex(args[4]), parse_hex(args[5])))
        print('valid=' + str(int(valid)))
    else:
        raise ValueError(__doc__)

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, AssertionError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
