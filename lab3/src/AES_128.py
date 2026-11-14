from functools import lru_cache

def _xtime(b):
    return ((b << 1) ^ 0x1B) & 0xFF if b & 0x80 else b << 1

def _mul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r

def _make_sbox():
    sbox = [0] * 256
    p = q = 1
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)  # p *= 3
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        rot = lambda v, n: ((v << n) | (v >> (8 - n))) & 0xFF
        sbox[p] = q ^ rot(q, 1) ^ rot(q, 2) ^ rot(q, 3) ^ rot(q, 4) ^ 0x63
        if p == 1:
            break
    sbox[0] = 0x63
    return sbox

SBOX = _make_sbox()
INV_SBOX = [0] * 256
for _i, _v in enumerate(SBOX):
    INV_SBOX[_v] = _i

@lru_cache(maxsize=16)
def _expand(key):
    if len(key) != 16:
        raise ValueError("ключ AES-128 должен быть 16 байт")
    w = [list(key[4 * i:4 * i + 4]) for i in range(4)]
    rc = 1
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [SBOX[x] for x in t]
            t[0] ^= rc
            rc = _xtime(rc)
        w.append([a ^ b for a, b in zip(w[i - 4], t)])
    return tuple(bytes(sum(w[4 * r:4 * r + 4], [])) for r in range(11))

def _add_key(s, k):
    return [a ^ b for a, b in zip(s, k)]

def _shift_rows(s):
    return [s[4 * ((c + r) % 4) + r] for c in range(4) for r in range(4)]

def _inv_shift_rows(s):
    out = [0] * 16
    for c in range(4):
        for r in range(4):
            out[4 * ((c + r) % 4) + r] = s[4 * c + r]
    return out

def _mix(s):
    out = []
    for c in range(4):
        a0, a1, a2, a3 = s[4 * c:4 * c + 4]
        out += [_xtime(a0) ^ (_xtime(a1) ^ a1) ^ a2 ^ a3,
                a0 ^ _xtime(a1) ^ (_xtime(a2) ^ a2) ^ a3,
                a0 ^ a1 ^ _xtime(a2) ^ (_xtime(a3) ^ a3),
                (_xtime(a0) ^ a0) ^ a1 ^ a2 ^ _xtime(a3)]
    return out

def _inv_mix(s):
    out = []
    for c in range(4):
        a0, a1, a2, a3 = s[4 * c:4 * c + 4]
        out += [_mul(a0, 14) ^ _mul(a1, 11) ^ _mul(a2, 13) ^ _mul(a3, 9),
                _mul(a0, 9) ^ _mul(a1, 14) ^ _mul(a2, 11) ^ _mul(a3, 13),
                _mul(a0, 13) ^ _mul(a1, 9) ^ _mul(a2, 14) ^ _mul(a3, 11),
                _mul(a0, 11) ^ _mul(a1, 13) ^ _mul(a2, 9) ^ _mul(a3, 14)]
    return out

def encrypt_block(pt_block, key):
    if len(pt_block) != 16:
        raise ValueError("блок должен быть 16 байт")
    rk = _expand(bytes(key))
    s = _add_key(list(pt_block), rk[0])
    for r in range(1, 10):
        s = [SBOX[x] for x in s]
        s = _shift_rows(s)
        s = _mix(s)
        s = _add_key(s, rk[r])
    s = _shift_rows([SBOX[x] for x in s])
    return bytes(_add_key(s, rk[10]))

def decrypt_block(ct_block, key):
    if len(ct_block) != 16:
        raise ValueError("блок должен быть 16 байт")
    rk = _expand(bytes(key))
    s = _add_key(list(ct_block), rk[10])
    for r in range(9, 0, -1):
        s = _inv_shift_rows(s)
        s = [INV_SBOX[x] for x in s]
        s = _inv_mix(_add_key(s, rk[r]))
    s = [INV_SBOX[x] for x in _inv_shift_rows(s)]
    return bytes(_add_key(s, rk[0]))