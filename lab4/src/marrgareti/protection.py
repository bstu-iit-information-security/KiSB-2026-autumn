from curve import O, P, Q, add, double, select


def secure_multiply(k, t):
    result = O
    for shift in range(Q.bit_length() - 1, -1, -1):
        twice = double(result)
        candidate = add(twice, t)
        result = select(twice, candidate, (k >> shift) & 1)
    return result


def same_point(t, u):
    # Сравниваем X/Z² и Y/Z³ без деления. Флаг различает O и конечную точку.
    left_x = (t.x * u.z**2 % P).to_bytes(32, "big")
    right_x = (u.x * t.z**2 % P).to_bytes(32, "big")
    left_y = (t.y * u.z**3 % P).to_bytes(32, "big")
    right_y = (u.y * t.z**3 % P).to_bytes(32, "big")
    diff = (t.z == 0) ^ (u.z == 0)
    for i in range(32):
        diff |= left_x[i] ^ right_x[i]
        diff |= left_y[i] ^ right_y[i]
    return diff == 0
