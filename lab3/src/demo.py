import json, os
from PIL import Image, ImageDraw, ImageFont
from belt import Belt
from modes import *

key = bytes.fromhex("E9DEE72C8F0C0FA62DDB49F46F73964706075316ED247A3739CBA38303A98BF6")
cipher = Belt(key)
S = bytes.fromhex("BE32971343FC9A48A02A885F194B09A1")
res = {}

# --- тестовые строки и паддинг ---
msgs = {"меньше 16 байт (5 байт)": b"Hello",
        "ровно 16 байт": b"0123456789ABCDEF",
        "больше 16 байт (37 байт)": b"The quick brown fox jumps over the dog"[:37]}
rows = []
for name, m in msgs.items():
    padded = pad(m)
    ct = ecb_encrypt(cipher, m)
    assert ecb_decrypt(cipher, ct) == m
    cc = ctr_crypt(cipher, m, S)
    assert ctr_crypt(cipher, cc, S) == m
    rows.append(dict(name=name, plain=m.decode(), n=len(m), padded_n=len(padded),
                     pad_hex=padded[-(len(padded)-len(m)):].hex().upper(),
                     blocks=len(ct)//16, ecb=ct.hex().upper(), ctr=cc.hex().upper(), ctr_n=len(cc)))
res["msgs"] = rows

# --- русский текст (UTF-8) ---
t = "Брестский государственный технический университет".encode("utf-8")
ct = ecb_encrypt(cipher, t); ct2 = ctr_crypt(cipher, t, S)
assert ecb_decrypt(cipher, ct) == t and ctr_crypt(cipher, ct2, S) == t
res["ru"] = dict(n=len(t), ecb=ct.hex().upper(), ctr=ct2.hex().upper(), back=ecb_decrypt(cipher, ct).decode())

# --- счётчик: порядок байт ---
s0 = cipher.encrypt_block(S)
v = bytearray(s0); v[0:4] = bytes.fromhex("FFFFFFFF")  # демонстрация переноса
from modes import _inc_counter
demo_in = bytes.fromhex("FFFFFFFF000000000000000000000000")
res["ctr_demo"] = dict(inp=demo_in.hex().upper(), le=_inc_counter(demo_in).hex().upper(),
        be=((int.from_bytes(demo_in,'big')+1)%(1<<128)).to_bytes(16,'big').hex().upper(),
        s0=s0.hex().upper(), s1=_inc_counter(s0).hex().upper())
# если ошибочно использовать big-endian счётчик - результат отличается
def ctr_be(cipher, data, synchro):
    s = cipher.encrypt_block(synchro); out = bytearray()
    for i in range(0, len(data), 16):
        s = ((int.from_bytes(s,'big')+1)%(1<<128)).to_bytes(16,'big')
        out += bytes(a^b for a,b in zip(data[i:i+16], cipher.encrypt_block(s)))
    return bytes(out)
m = b"A"*32
res["ctr_demo"]["le_ct"] = ctr_crypt(cipher, m, S).hex().upper()
res["ctr_demo"]["be_ct"] = ctr_be(cipher, m, S).hex().upper()
assert res["ctr_demo"]["le_ct"] != res["ctr_demo"]["be_ct"]

# --- CTR: одинаковые блоки -> разные шифрблоки; ECB -> одинаковые ---
rep = b"SECRETSECRETSECR" * 4
e = ecb_encrypt(cipher, rep, False); c = ctr_crypt(cipher, rep, S)
res["rep"] = dict(ecb=[e[i:i+16].hex().upper() for i in range(0,64,16)],
                  ctr=[c[i:i+16].hex().upper() for i in range(0,64,16)])

# --- изображение ---
W = H = 256
im = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(im)
d.rectangle([0,0,W-1,H-1], fill=(255,255,255))
d.rectangle([16,16,112,112], fill=(200,30,30))
d.ellipse([144,16,240,112], fill=(30,60,200))
d.polygon([(128,128),(240,240),(16,240)], fill=(20,150,60))
d.rectangle([16,128,96,160], fill=(0,0,0))
try:
    f = ImageFont.load_default(size=40)
except TypeError:
    f = None
d.text((40,180), "BelT", fill=(255,255,255), font=f)
im.save("plain.bmp")
raw = open("plain.bmp","rb").read()
off = int.from_bytes(raw[10:14],"little"); hdr, pix = raw[:off], raw[off:]
assert len(pix) % 16 == 0
def save(name, data):
    open(name+".bmp","wb").write(hdr+data)
    Image.open(name+".bmp").save(name+".png")
save("ecb", ecb_encrypt(cipher, pix, False))
save("ctr", ctr_crypt(cipher, pix, S))
Image.open("plain.bmp").save("plain.png")
pe = open("ecb.bmp","rb").read()[off:]
nb = len(pe)//16
res["img"] = dict(blocks=nb, uniq_plain=len({pix[i:i+16] for i in range(0,len(pix),16)}),
   uniq_ecb=len({pe[i:i+16] for i in range(0,len(pe),16)}),
   uniq_ctr=len({open("ctr.bmp","rb").read()[off:][i:i+16] for i in range(0,len(pe),16)}))
json.dump(res, open("res.json","w"), ensure_ascii=False, indent=1)
print(json.dumps(res["img"]), res["ctr_demo"]["le"], res["ctr_demo"]["be"])
