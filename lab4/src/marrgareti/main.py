import re
import sys
from curve import G, O, P, Q, Point, affine, double, multiply
from protection import same_point
from protocols import ecdh, keypair, sign, sign_once, verify

# Сообщения и их заранее вычисленные хэши Стрибог-256.
VECTORS = {
    "616263": "4e2919cf137ed41ec4fb6270c61826cc4fffb660341e0af3688cd0626d23b481",
    "6c616234": "9470b4496a8ffd566866755c3f6584966f30ceb702c2db02d53a4b44999d6515",
}


def run(digests):
    d = int("7a929ade789bb9be10ed359dd39a72c11b60961f49397eee1d19ce9891ec3b28", 16)
    k = int("77105c9b20bcd3122823c8cf6fcc7b956de33814e95b7fe64fed924594dceab3", 16)
    e = int("2dfbc1b372d89a1188c09c52e0eec61fce52032ab1022e8e67ece6672b043ee5", 16)
    expected_r = int("41aa28d2f1ab148280cd9ed56feda41974053554a42767b83ad043fd39dc0493", 16)
    expected_s = int("1456c64ba4642a1653c235a98a60249bcd6d3f746b631df928014f6c5bf9c40", 16)
    pair = sign_once(d, e, k)
    assert pair == (expected_r, expected_s) and verify(multiply(d, G), e, *pair)
    print("RFC 7091: OK")
    scaled = Point(4*G.x % P, 8*G.y % P, 2)
    assert same_point(G, scaled) and not same_point(G, double(G))
    assert same_point(O, multiply(Q, G)) and not same_point(O, G)
    print("Сравнение точек: OK")
    da, qa = keypair()
    db, qb = keypair()
    alice, bob = ecdh(da, qb), ecdh(db, qa)
    for label, point in (("QA", qa), ("QB", qb), ("SA", alice), ("SB", bob)):
        x, y = affine(point)
        print(f"{label}.x={x:064x}\n{label}.y={y:064x}")
    assert same_point(alice, bob)
    print("ECDH: OK")
    for message, digest in digests:
        e = int(digest, 16)
        r, s = sign(da, e)
        damaged = s ^ 1
        good = verify(qa, e, r, s)
        bad = verify(qa, e, r, damaged)
        assert good and not bad
        if message:
            print("M=" + message)
        print(f"H={digest}\nr={r:064x}\ns={s:064x}\ns'={damaged:064x}")
        print(f"Проверка: {good}; после изменения байта: {bad}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and (len(args) != 1 or not re.fullmatch("[0-9a-fA-F]{64}", args[0])):
        sys.exit("Ожидается хэш из 64 hex-цифр.")
    run([(None, args[0])] if args else VECTORS.items())
