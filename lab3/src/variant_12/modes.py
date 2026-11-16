"""Режимы шифрования ECB и OFB поверх блочного шифра БелТ.

Модуль 2: обработка сообщений произвольной длины. Использует только
атомарные операции над одним блоком из модуля belt и сам ничего не
знает о внутреннем устройстве шифра.

  * ECB — каждый блок шифруется независимо, нужен паддинг PKCS#7.
  * OFB — шифр работает как синхронный потоковый: гамма
    I_i = E_K(I_{i-1}), I_0 = IV, C_i = P_i xor I_i. Паддинг не нужен:
    последний неполный блок XOR-ится с началом очередного блока гаммы.

Оптимизация OFB (вариант 12). Гамма зависит только от (K, IV) и не
зависит от данных, поэтому её можно выработать заранее
(OfbGamma.precompute), а при поступлении данных выполнить одну
операцию XOR. Дополнительно:
  1) ключ разворачивается один раз (BeltCipher), а не на каждом блоке;
  2) G-функции вычисляются по склеенным таблицам (4 обращения вместо
     4 подстановок + сдвига);
  3) состояние обратной связи хранится как четыре 32-битных слова и не
     переводится в байты и обратно между итерациями;
  4) XOR всего сообщения с гаммой делается одной операцией над длинными
     целыми, а не побайтовым циклом.
"""

from belt import BLOCK_SIZE, BeltCipher, encrypt_block, decrypt_block, bytes_to_words, words_to_bytes


# --------------------------------------------------------------------------
# PKCS#7
# --------------------------------------------------------------------------

def pkcs7_pad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    """Дополнение k = B - (L mod B) байтами со значением k (1 <= k <= B)."""
    k = block_size - len(data) % block_size
    return data + bytes([k]) * k


def pkcs7_unpad(data: bytes, block_size: int = BLOCK_SIZE) -> bytes:
    """Проверка и снятие дополнения PKCS#7.

    Проверка выполняется целиком (все B последних байт просматриваются
    всегда), а результат — одно общее исключение, чтобы не выдавать по
    тексту ошибки, на каком именно шаге проверка не прошла.
    """
    if len(data) == 0 or len(data) % block_size != 0:
        raise ValueError("некорректное дополнение PKCS#7")
    k = data[-1]
    bad = int(not (1 <= k <= block_size))
    tail = data[-block_size:]
    for i in range(block_size):
        # байт входит в паддинг, если он среди последних k
        in_pad = int(i >= block_size - k)
        bad |= in_pad & int(tail[i] != k)
    if bad:
        raise ValueError("некорректное дополнение PKCS#7")
    return data[:-k]


def xor_bytes(x: bytes, y: bytes) -> bytes:
    """XOR двух байтовых строк (по длине x) одной операцией над int."""
    n = len(x)
    if n == 0:
        return b""
    return (int.from_bytes(x, "little") ^ int.from_bytes(y[:n], "little")).to_bytes(n, "little")


def _check_iv(iv: bytes):
    if not isinstance(iv, (bytes, bytearray)) or len(iv) != BLOCK_SIZE:
        raise ValueError(f"IV должен быть {BLOCK_SIZE} байт")


# --------------------------------------------------------------------------
# ECB
# --------------------------------------------------------------------------

def ecb_encrypt(data: bytes, key: bytes, pad: bool = True) -> bytes:
    """C_i = E_K(P_i). При pad=False длина должна быть кратна 16."""
    if pad:
        data = pkcs7_pad(data)
    if len(data) % BLOCK_SIZE:
        raise ValueError("длина данных для ECB без паддинга должна быть кратна 16 байт")
    cipher = BeltCipher(key)
    return b"".join(cipher.encrypt_block(data[i:i + BLOCK_SIZE])
                    for i in range(0, len(data), BLOCK_SIZE))


def ecb_decrypt(data: bytes, key: bytes, pad: bool = True) -> bytes:
    """P_i = D_K(C_i), затем проверка и снятие паддинга."""
    if len(data) % BLOCK_SIZE:
        raise ValueError("длина шифротекста ECB должна быть кратна 16 байт")
    cipher = BeltCipher(key)
    out = b"".join(cipher.decrypt_block(data[i:i + BLOCK_SIZE])
                   for i in range(0, len(data), BLOCK_SIZE))
    return pkcs7_unpad(out) if pad else out


# --------------------------------------------------------------------------
# OFB
# --------------------------------------------------------------------------

class OfbGamma:
    """Генератор гаммы OFB с возможностью предварительной выработки.

    gen = OfbGamma(key, iv)
    gen.precompute(n)     # «офлайн»: вырабатываем n байт гаммы заранее
    c = gen.apply(p)      # «онлайн»: только XOR с готовой гаммой

    Если гаммы не хватает, недостающая часть дорабатывается на лету,
    продолжая ту же цепочку I_i = E_K(I_{i-1}).
    """

    def __init__(self, key: bytes, iv: bytes):
        _check_iv(iv)
        self._cipher = BeltCipher(key)
        self._state = bytes_to_words(iv)  # I_{i-1} в виде 4 слов
        self._buf = b""                   # выработанная, но не израсходованная гамма

    def _generate(self, nblocks: int) -> bytes:
        enc = self._cipher.encrypt_words
        a, b, c, d = self._state
        parts = []
        append = parts.append
        for _ in range(nblocks):
            a, b, c, d = enc(a, b, c, d)  # I_i = E_K(I_{i-1}) без перевода в байты
            append(words_to_bytes(a, b, c, d))
        self._state = (a, b, c, d)
        return b"".join(parts)

    def precompute(self, nbytes: int) -> None:
        need = nbytes - len(self._buf)
        if need > 0:
            self._buf += self._generate(-(-need // BLOCK_SIZE))

    def take(self, nbytes: int) -> bytes:
        self.precompute(nbytes)
        g, self._buf = self._buf[:nbytes], self._buf[nbytes:]
        return g

    def apply(self, data: bytes) -> bytes:
        return xor_bytes(data, self.take(len(data)))


def ofb_keystream(key: bytes, iv: bytes, nbytes: int) -> bytes:
    """Первые nbytes байт гаммы OFB для пары (K, IV)."""
    return OfbGamma(key, iv).take(nbytes)


def ofb_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """C = P xor Gamma(K, IV); длина шифротекста равна длине текста."""
    return OfbGamma(key, iv).apply(data)


def ofb_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """P = C xor Gamma(K, IV) — та же операция, используется только E_K."""
    return OfbGamma(key, iv).apply(data)


def ofb_encrypt_naive(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Наивный OFB для сравнения скорости: блок за блоком через
    encrypt_block(block, key) (ключ разворачивается на каждом вызове,
    G считается по определению), XOR — побайтовым циклом."""
    _check_iv(iv)
    out = bytearray()
    state = iv
    for i in range(0, len(data), BLOCK_SIZE):
        state = encrypt_block(state, key)
        chunk = data[i:i + BLOCK_SIZE]
        out.extend(p ^ g for p, g in zip(chunk, state))
    return bytes(out)


__all__ = [
    "pkcs7_pad", "pkcs7_unpad", "xor_bytes",
    "ecb_encrypt", "ecb_decrypt",
    "OfbGamma", "ofb_keystream", "ofb_encrypt", "ofb_decrypt", "ofb_encrypt_naive",
    "encrypt_block", "decrypt_block",
]
