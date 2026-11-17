from belt import Belt
from modes import *
import os

# --- 1. тестовые векторы СТБ 34.101.31 ---
k1 = bytes.fromhex("E9DEE72C8F0C0FA62DDB49F46F73964706075316ED247A3739CBA38303A98BF6")
x1 = bytes.fromhex("B194BAC80A08F53B366D008E584A5DE4")
y1 = bytes.fromhex("69CCA1C93557C9E3D66BC3E0FA88FA6E")
k2 = bytes.fromhex("92BD9B1CE5D141015445FBC95E4D0EF2682080AA227D642F2687F93490405511")
y2 = bytes.fromhex("E12BDC1AE28257EC703FCCF095EE8DF1")
x2 = bytes.fromhex("0DC5300600CAB840B38448E5E993F421")
assert Belt(k1).encrypt_block(x1) == y1
assert Belt(k2).decrypt_block(y2) == x2
assert Belt(k2).encrypt_block(x2) == y2
print("test vectors OK")
