
p = 0x8000000000000000000000000000000000000000000000000000000000000431
a = 7
b = 0x5FBFF498AA938CE739B8E022FBAFEF40563F6E6A3472FC2A514C0CE9DAE23B7E
q = 0x8000000000000000000000000000000150FE8A1892976154C59CFC193ACCF5B3
Gx = 0x2
Gy = 0x08E2A8A0E65147D4BD6316030E16D19C85C97F0A9CA267122B96ABBCEA7E8FC8


def inv(x, m):
    return pow(x, -1, m)


class Point:
    def __init__(self, X, Y, Z):
        self.X = X
        self.Y = Y
        self.Z = Z


INF = Point(1, 1, 0)          
G = Point(Gx, Gy, 1)


def is_inf(P):
    return P.Z == 0


def on_curve(x, y):
    return (y * y - (x * x * x + a * x + b)) % p == 0


def to_affine(P):
    if is_inf(P):
        return None
    zi = inv(P.Z, p)
    return (P.X * zi * zi % p, P.Y * zi * zi * zi % p)


def double(P):
    if is_inf(P) or P.Y == 0:
        return INF
    S = 4 * P.X * P.Y * P.Y % p
    M = (3 * P.X * P.X + a * pow(P.Z, 4, p)) % p
    X3 = (M * M - 2 * S) % p
    Y3 = (M * (S - X3) - 8 * pow(P.Y, 4, p)) % p
    Z3 = 2 * P.Y * P.Z % p
    return Point(X3, Y3, Z3)


def add(P1, P2):
    if is_inf(P1):
        return P2
    if is_inf(P2):
        return P1
    U1 = P1.X * P2.Z * P2.Z % p
    U2 = P2.X * P1.Z * P1.Z % p
    S1 = P1.Y * pow(P2.Z, 3, p) % p
    S2 = P2.Y * pow(P1.Z, 3, p) % p
    H = (U2 - U1) % p
    R = (S2 - S1) % p
    if H == 0:
        if R == 0:
            return double(P1)   # точки равны
        return INF              # P + (-P)
    X3 = (R * R - H ** 3 - 2 * U1 * H * H) % p
    Y3 = (R * (U1 * H * H - X3) - S1 * H ** 3) % p
    Z3 = H * P1.Z * P2.Z % p
    return Point(X3, Y3, Z3)


def multiply(k, P):
    # обычный Double-and-Add
    R = INF
    for bit in bin(k)[2:]:
        R = double(R)
        if bit == '1':
            R = add(R, P)
    return R
