import ec
from ec import G, q, INF
import protocols
from secure import ct_equal, ct_point_equal

print("G на кривой:", ec.on_curve(ec.Gx, ec.Gy))
print("q*G = O:", ec.is_inf(ec.multiply(q, G)))

P = ec.multiply(5, G)
P2 = ec.add(ec.multiply(2, G), ec.multiply(3, G))  
print("5G == 2G+3G:", ct_point_equal(P, P2))
print("5G == 6G:", ct_point_equal(P, ec.multiply(6, G)))
print("ct_equal(5, 5):", ct_equal(5, 5), " ct_equal(5, 6):", ct_equal(5, 6))

dA, QA = protocols.gen_keys()
dB, QB = protocols.gen_keys()
KA = protocols.ecdh(dA, QB)
KB = protocols.ecdh(dB, QA)
print("QA:", ["%x" % c for c in ec.to_affine(QA)])
print("QB:", ["%x" % c for c in ec.to_affine(QB)])
print("Secret A: %x" % KA)
print("Secret B: %x" % KB)
print("Секреты совпали:", ct_equal(KA, KB))

d = 0x7A929ADE789BB9BE10ED359DD39A72C11B60961F49397EEE1D19CE9891EC3B28
e = 0x2DFBC1B372D89A1188C09C52E0EEC61FCE52032AB1022E8E67ECE6672B043EE5
k = 0x77105C9B20BCD3122823C8CF6FCC7B956DE33814E95B7FE64FED924594DCEAB3
Q = ec.multiply(d, G)
print("Q.x: %x" % ec.to_affine(Q)[0])
print("Q.y: %x" % ec.to_affine(Q)[1])
r, s = protocols.sign(e, d, k)
print("r: %x" % r)
print("s: %x" % s)
print("Подпись верна:", protocols.verify(e, r, s, Q))
print("Испорчен 1 байт s:", protocols.verify(e, r, s ^ 0x01, Q))

d2, Q2 = protocols.gen_keys()
e2 = 0x1234567890ABCDEF
r2, s2 = protocols.sign(e2, d2)
print("Случайная подпись верна:", protocols.verify(e2, r2, s2, Q2))
