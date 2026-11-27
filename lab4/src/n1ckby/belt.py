from struct import pack, unpack

H = bytes.fromhex(
    "B194BAC80A08F53B366D008E584A5DE4"
    "8504FA9D1BB6C7AC252E72C202FDCE0D"
    "5BE3D61217B96181FE6786AD716B890B"
    "5CB0C0FF33C356B835C405AED8E07F99"
    "E12BDC1AE28257EC703FCCF095EE8DF1"
    "C1AB76389FE678CAF7C6F860D5BB9C4F"
    "F33C657B637C306ADD4EA7799EB23D31"
    "3E98B56E27D3BCCF591E181F4C5AB793"
    "E9DEE72C8F0C0FA62DDB49F46F739647"
    "06075316ED247A3739CBA38303A98BF6"
    "92BD9B1CE5D141015445FBC95E4D0EF2"
    "682080AA227D642F2687F93490405511"
    "BE32971343FC9A48A02A885F194B09A1"
    "7ECDA4D01544AF8CA58450BF66D2E88A"
    "A2D7465242A8DFB36974C551EB232921"
    "D4EFD9B43A622875911410EA776CDA1D"
)
MASK = 0xffffffff


def g(value, shift):
    word = (value & MASK).to_bytes(4, "little").translate(H)
    n = int.from_bytes(word, "little")
    return ((n << shift) | (n >> (32-shift))) & MASK


def encrypt(block, key):
    a, b, c, d = unpack("<4I", block)
    words = unpack("<8I", key)
    for i in range(8):
        j = 7*i
        b ^= g(a + words[j % 8], 5)
        c ^= g(d + words[(j+1) % 8], 21)
        a = (a - g(b + words[(j+2) % 8], 13)) & MASK
        e = g(b + c + words[(j+3) % 8], 21) ^ (i+1)
        b, c = (b+e) & MASK, (c-e) & MASK
        d = (d + g(c + words[(j+4) % 8], 13)) & MASK
        b ^= g(a + words[(j+5) % 8], 21)
        c ^= g(d + words[(j+6) % 8], 5)
        a, b, c, d = b, d, a, c
    return pack("<4I", b, d, a, c)


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def compress(h, block):
    left, right = block[:16], block[16:]
    v = xor(h[:16], h[16:])
    s = xor(encrypt(v, block), v)
    key1 = s + h[16:]
    key2 = bytes(x ^ 255 for x in s) + h[:16]
    return s, xor(encrypt(left, key1), left) + xor(encrypt(right, key2), right)


def belt_hash(message):
    h, total = H[:32], bytes(16)
    for i in range(0, len(message), 32):
        block = message[i:i+32].ljust(32, b"\0")
        s, h = compress(h, block)
        total = xor(total, s)
    length = (8*len(message)).to_bytes(16, "little")
    return compress(h, length + total)[1]
