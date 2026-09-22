import math
a=9
c=18
N=2**20
x0=101

def obr(x0):
    return pow(x0,-1,N)
def gen(x0):
    if x0:
        x1=(a*obr(x0)+c)%N
    else:
        x1=c
    return x1

def part1():
    generated = []
    for i in range(0, 1000):
        x0 = gen(x0)
        generated.append(x0)

    print(generated)

    M = sum(generated) / len(generated)
    print(f"Мат.Ожидание {sum(generated) / len(generated)}")
    s = 0
    for g in generated:
        s += (M - g) ** 2
    s /= len(generated)
    print(f"Дисперсия {s}")
    print(
        f"Для равномерного Мат.Ожидание = {(max(generated) + min(generated)) / 2}  Дисперсия = {(max(generated) - min(generated)) ** 2 / 12}")

def candidate(p,x):
    n=0
    for _ in range(p):
        x=gen(x)
        bit = (x>>5|x>>8)&1
        #print(bit, end=", ")
        n = (n << 1) | bit
    n |= (1 << (p - 1))
    n |= 1
    return x, n

prostye=[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163, 1171, 1181, 1187, 1193, 1201, 1213, 1217, 1223, 1229, 1231, 1237, 1249, 1259, 1277, 1279, 1283, 1289, 1291, 1297, 1301, 1303, 1307, 1319, 1321, 1327, 1361, 1367, 1373, 1381, 1399, 1409, 1423, 1427, 1429, 1433, 1439, 1447, 1451, 1453, 1459, 1471, 1481, 1483, 1487, 1489, 1493, 1499, 1511, 1523, 1531, 1543, 1549, 1553, 1559, 1567, 1571, 1579, 1583, 1597, 1601, 1607, 1609, 1613, 1619, 1621, 1627, 1637, 1657, 1663, 1667, 1669, 1693, 1697, 1699, 1709, 1721, 1723, 1733, 1741, 1747, 1753, 1759, 1777, 1783, 1787, 1789, 1801, 1811, 1823, 1831, 1847, 1861, 1867, 1871, 1873, 1877, 1879, 1889, 1901, 1907, 1913, 1931, 1933, 1949, 1951, 1973, 1979, 1987, 1993, 1997, 1999]
def prover_del(n):
    for p in prostye:
        if p*p>n:
            break
        if (n%p)==0:
            return False
    return True

def isPerfectPower(n):
    #print(math.floor(math.log2(n)))
    for b in range(2, math.floor(math.log2(n))):
        if (math.floor(n**(1.0/b))**b)==n :
           return True;
    return False;

def findR(n):
    r = 2
    limit = math.floor(math.log2(n) ** 2)

    while True:
        good = True

        for k in range(1, limit + 1):
            if pow(n, k, r) == 1:
                good = False
                break

        if good:
            return r

        r += 1

def NOD(a, n):
    while n != 0:
        ostatok = a % n
        a = n
        n = ostatok
    return a

def phi(n):
    result = n

    p = 2
    x = n

    while p * p <= x:
        if x % p == 0:
            while x % p == 0:
                x //= p

            result -= result // p

        p += 1

    if x > 1:
        result -= result // x

    return result

def polynomial_multiply(a, b, r, n):
    result = [0] * r

    for i in range(r):
        if a[i] == 0:
            continue

        for j in range(r):
            if b[j] == 0:
                continue

            k = (i + j) % r
            result[k] += a[i] * b[j]

    for i in range(r):
        result[i] %= n

    return result

def polynomial_power(a, power, r, n):
    result = [0] * r
    result[0] = 1

    while power > 0:

        if power % 2 == 1:
            result = polynomial_multiply(result, a, r, n)

        a = polynomial_multiply(a, a, r, n)

        power //= 2

    return result

def isProstoe(n):
    if n < 2:
        return False


    if not prover_del(n):
        return False

    if isPerfectPower(n):
        return False

    r = findR(n)
    print("n =", n, "r =", r)
    for a in range(2, r + 1):
        if NOD(a, n) > 1:
            return False

    if n <= r:
        return True

    limit = math.floor(
        math.sqrt(phi(r)) * math.log2(n)
    )

    # Проверяем:

    for a in range(1, limit + 1):
        polynomial = [0] * r
        polynomial[0] = a % n
        polynomial[1] = 1

        left = polynomial_power(
            polynomial,
            n,
            r,
            n
        )

        right = [0] * r

        right[0] = a % n
        right[n % r] = (right[n % r] + 1) % n

        if left != right:
            return False

    return True

if __name__ == '__main__':
    x=x0
    while True:
        x, n=candidate(17,x)
        #print(n)
        if(isProstoe(n)):
            print(f"{n} - Простое")
            break


