import os
import time

from belt import encrypt_block, decrypt_block
from modes import ecb_encrypt, ecb_decrypt, ctr_crypt, ctr_crypt_parallel


def main():
    key = bytes.fromhex(
        "E9DEE72C8F0C0FA62DDB49F46F73964706075316ED247A3739CBA38303A98BF6")

    x = bytes.fromhex("B194BAC80A08F53B366D008E584A5DE4")
    y = encrypt_block(x, key)
    print("Шифр блока:", y.hex().upper())
    print("Ожидается :", "69CCA1C93557C9E3D66BC3E0FA88FA6E")
    print("Расшифр. OK:", decrypt_block(y, key) == x)

    print("\nECB + PKCS#7")
    for n in (5, 16, 40):
        msg = os.urandom(n)
        ct = ecb_encrypt(msg, key)
        print("длина", n, "-> шифротекст", len(ct), "байт, OK:",
              ecb_decrypt(ct, key) == msg)

    print("\nCTR")
    iv = os.urandom(16)
    for n in (5, 16, 40):
        msg = os.urandom(n)
        ct = ctr_crypt(msg, key, iv)
        print("длина", n, "-> шифротекст", len(ct), "байт, OK:",
              ctr_crypt(ct, key, iv) == msg)

    iv_max = b'\xff' * 16
    msg = os.urandom(48)
    print("Перенос счетчика OK:",
          ctr_crypt(ctr_crypt(msg, key, iv_max), key, iv_max) == msg)

    print("\nСравнение времени")
    data = os.urandom(16 * 20000)  

    t = time.time()
    ecb_encrypt(data, key)
    t_ecb = time.time() - t

    t = time.time()
    c2 = ctr_crypt(data, key, iv)
    t_ctr = time.time() - t

    t = time.time()
    c3 = ctr_crypt_parallel(data, key, iv, 4)
    t_par = time.time() - t

    print("ECB последовательно  : %.2f c" % t_ecb)
    print("CTR последовательно  : %.2f c" % t_ctr)
    print("CTR параллельно (4)  : %.2f c" % t_par)
    print("Результаты CTR совпадают:", c2 == c3)
    print("Ускорение CTR: %.2f раз" % (t_ctr / t_par))
    print("Расшифрование CTR parallel OK:",
          ctr_crypt_parallel(c3, key, iv, 4) == data)


if __name__ == "__main__":
    main()