"""Дополнительное сравнение с командой openssl; самой программе она не нужна."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modes import encrypt_ecb, decrypt_ecb, encrypt_cfb, decrypt_cfb

for size in (0, 1, 2, 15, 16, 17, 31, 32, 33, 64, 127, 256, 4097):
    data = bytes((i * 19 + 11) % 256 for i in range(size))
    key = bytes(range(16))
    iv = bytes(range(16, 32))
    for mode in ('ecb', 'cfb'):
        args = ['openssl', 'enc', '-aes-128-' + mode, '-K', key.hex()]
        if mode == 'cfb':
            args += ['-iv', iv.hex()]
        expected = subprocess.run(args, input=data, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, check=True).stdout
        result = encrypt_ecb(data, key) if mode == 'ecb' else encrypt_cfb(data, key, iv)
        if result != expected:
            raise AssertionError((mode, size, 'encrypt'))
        recovered = decrypt_ecb(expected, key) if mode == 'ecb' else decrypt_cfb(expected, key, iv)
        if recovered != data:
            raise AssertionError((mode, size, 'decrypt'))
        print(mode.upper(), size, 'bytes: совпадает с OpenSSL; исходное восстановлено')
print('OK: 26 сравнений')
