BELT_SBOX = bytes.fromhex(
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


def belt_g(value, shift):
    encoded = value.to_bytes(4, "little")
    substituted = int.from_bytes(bytes(BELT_SBOX[byte] for byte in encoded), "little")
    return ((substituted << shift) | (substituted >> (32 - shift))) & 0xFFFFFFFF


def belt_block(block, key):
    words = [int.from_bytes(block[i:i + 4], "little") for i in range(0, 16, 4)]
    key_words = [int.from_bytes(key[i:i + 4], "little") for i in range(0, 32, 4)]
    a, b, c, d = words
    for round_number in range(1, 9):
        offset = 7 * (round_number - 1)
        b ^= belt_g((a + key_words[offset % 8]) & 0xFFFFFFFF, 5)
        c ^= belt_g((d + key_words[(offset + 1) % 8]) & 0xFFFFFFFF, 21)
        a = (a - belt_g((b + key_words[(offset + 2) % 8]) & 0xFFFFFFFF, 13)) & 0xFFFFFFFF
        e = belt_g((b + c + key_words[(offset + 3) % 8]) & 0xFFFFFFFF, 21) ^ round_number
        b = (b + e) & 0xFFFFFFFF
        c = (c - e) & 0xFFFFFFFF
        d = (d + belt_g((c + key_words[(offset + 4) % 8]) & 0xFFFFFFFF, 13)) & 0xFFFFFFFF
        b ^= belt_g((a + key_words[(offset + 5) % 8]) & 0xFFFFFFFF, 21)
        c ^= belt_g((d + key_words[(offset + 6) % 8]) & 0xFFFFFFFF, 5)
        a, b = b, a
        c, d = d, c
        b, c = c, b
    return (b.to_bytes(4, "little") + d.to_bytes(4, "little") +
            a.to_bytes(4, "little") + c.to_bytes(4, "little"))


def xor_bytes(first, second):
    return bytes(left ^ right for left, right in zip(first, second))


def belt_compress(data):
    x1, x2, x3, x4 = (data[i:i + 16] for i in range(0, 64, 16))
    x34 = xor_bytes(x3, x4)
    state = xor_bytes(belt_block(x34, x1 + x2), x34)
    y1 = xor_bytes(belt_block(x1, state + x4), x1)
    y2 = xor_bytes(belt_block(x2, xor_bytes(state, b"\xff" * 16) + x3), x2)
    return state, y1 + y2


def belt_hash(data):
    length = (8 * len(data)).to_bytes(16, "little")
    state = bytes(16)
    digest = BELT_SBOX[:32]
    for offset in range(0, len(data), 32):
        block = data[offset:offset + 32].ljust(32, b"\x00")
        contribution, digest = belt_compress(block + digest)
        state = xor_bytes(state, contribution)
    return belt_compress(length + state + digest)[1]
