
from ec import p

N_BYTES = 32


def ct_equal(x, y):
    
    acc = 0
    for i in range(N_BYTES):
        bx = (x >> (8 * i)) & 0xFF
        by = (y >> (8 * i)) & 0xFF
        acc |= bx ^ by
    return acc == 0     


def ct_point_equal(P1, P2):
   
    x1 = P1.X * P2.Z * P2.Z % p
    x2 = P2.X * P1.Z * P1.Z % p
    y1 = P1.Y * pow(P2.Z, 3, p) % p
    y2 = P2.Y * pow(P1.Z, 3, p) % p
    acc = (x1 ^ x2) | (y1 ^ y2)     
    return ct_equal(acc, 0)


def secure_multiply(k, P):
    from ec import multiply
    return multiply(k, P)
