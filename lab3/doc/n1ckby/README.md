# Лабораторная работа №3
# Блочные шифры и классические режимы шифрования

# Выполнил: Вавдийчик Никита
# Группа АС-65
**Вариант 1. AES-128, ECB и CBC.**

## 1. Цель и задание

Цель: программно реализовать блочный шифр AES-128 и режимы ECB и CBC
с дополнением PKCS#7 без сторонних криптографических библиотек.
Исследовать, как режимы скрывают повторяющиеся блоки данных.
Основание работы — предоставленная методичка `theory(2).md`, вариант 1.
Для независимой проверки использованы контрольные примеры NIST SP 800-38A.

## 2. Теоретическая часть

### 2.1. AES-128

AES — подстановочно-перестановочная сеть (SP-сеть). Размер блока и ключа
в AES-128 равен 128 битам, то есть 16 байтам. Выполняется 10 раундов.
Состояние — матрица 4 × 4 байта, заполненная по столбцам:

$$s_{r,c}=P_{4c+r},\quad 0\le r,c<4.$$

Начальное преобразование:

$$S\leftarrow S\oplus K^{(0)}.$$

Раунды 1–9:

$$S\leftarrow\operatorname{AddRoundKey}(\operatorname{MixColumns}(\operatorname{ShiftRows}(\operatorname{SubBytes}(S))),K^{(r)}).$$

В раунде 10 выполняются SubBytes, ShiftRows и AddRoundKey без MixColumns.

- **SubBytes:** каждый байт заменяется значением фиксированной таблицы S-box: $s'_{r,c}=Sbox[s_{r,c}]$.
- **ShiftRows:** строка r сдвигается влево на r байт: $s'_{r,c}=s_{r,(c+r)\bmod4}$.
- **MixColumns:** каждый столбец умножается на матрицу в поле $GF(2^8)$.
- **AddRoundKey:** байты состояния складываются с байтами раундового ключа операцией XOR.

Матрица MixColumns:

$$\begin{pmatrix}02&03&01&01\\01&02&03&01\\01&01&02&03\\03&01&01&02\end{pmatrix}.$$

Сложение в поле — XOR. Умножение реализовано через операцию xtime:

$$\operatorname{xtime}(b)=\begin{cases}(b\ll1)\bmod256,&b_7=0,\\((b\ll1)\oplus\text{0x1B})\bmod256,&b_7=1.\end{cases}$$

Умножение на 3: $3\cdot b=\operatorname{xtime}(b)\oplus b$.

**Расширение ключа.** Формируются 44 слова по 4 байта. Первые четыре —
исходный ключ. Для i от 4 до 43:

$$W_i=\begin{cases}W_{i-4}\oplus\operatorname{SubWord}(\operatorname{RotWord}(W_{i-1}))\oplus Rcon[i/4],&i\bmod4=0,\\W_{i-4}\oplus W_{i-1},&\text{иначе}.\end{cases}$$

RotWord сдвигает слово на один байт влево, SubWord применяет S-box.
$Rcon[j]=(rc_j,0,0,0)$, $rc_1=1$, $rc_{j+1}=\operatorname{xtime}(rc_j)$.
Каждые четыре слова образуют один раундовый ключ: всего 11 ключей.

**Расшифрование.** Сначала применяется ключ 10. Затем для раундов 9–1
выполняются InvShiftRows, InvSubBytes, AddRoundKey и InvMixColumns.
В конце — InvShiftRows, InvSubBytes и ключ 0.
InvShiftRows сдвигает строки вправо; InvSubBytes использует обратную таблицу.
Матрица InvMixColumns (коэффициенты в hex):

$$\begin{pmatrix}0e&0b&0d&09\\09&0e&0b&0d\\0d&09&0e&0b\\0b&0d&09&0e\end{pmatrix}.$$

### 2.2. Режим ECB

$$C_i=E_K(P_i),\qquad P_i=D_K(C_i).$$

Каждый блок обрабатывается независимо. При одном ключе одинаковые
исходные блоки всегда дают одинаковые зашифрованные блоки.
Поэтому повторяемость данных остаётся видна.

### 2.3. Режим CBC

$$C_0=IV,\qquad C_i=E_K(P_i\oplus C_{i-1}).$$

$$P_i=D_K(C_i)\oplus C_{i-1}.$$

Перед AES блок складывается с предыдущим шифроблоком.
Для первого блока используется случайный IV размером 16 байт.
В программе IV создаётся `secrets.token_bytes(16)` для каждого сообщения.
Для расшифрования сохраняется тот же IV; он не является секретным ключом.
Фиксированный IV в тестах применяется только для проверки контрольных примеров.

### 2.4. PKCS#7

Для длины L байт и размера блока B = 16:

$$k=16-(L\bmod16),\qquad M_{pad}=M\parallel[k]^k.$$

Добавляются k байтов со значением k. При длине, кратной 16, добавляется
полный блок `10 10 ... 10` (hex). Пустое сообщение также получает 16 байт.
При снятии дополнения проверяются непустая длина, кратность 16,
диапазон последнего байта 1–16 и равенство всех последних k байтов k.

## 3. Архитектура программы

Основная реализация разделена на два независимых по назначению модуля:

| Модуль | Ответственность |
| --- | --- |
| aes.py | AES-128: S-box, обратная таблица, GF(2^8), расширение ключа, шифрование/расшифрование одного блока |
| modes.py | ECB, CBC, дополнение PKCS#7 и его проверка; вызывает функции aes.py |

`main.py` отвечает только за ввод и демонстрацию, `test_lab.py` — за проверки.
AES не знает о сообщениях, IV и паддинге. Режимы не реализуют раунды AES.
Функции `encrypt_block(pt_block, key)` и `decrypt_block(ct_block, key)`
принимают строго 16 байт. Все режимы работают с байтами.
Строки преобразуются в UTF-8, поэтому число символов может отличаться от числа байтов.

## 4. Листинг ключевых функций

Ниже приведён код из файлов проверенной программы.

### aes.py

```python
def encrypt_block(pt_block: bytes, key: bytes) -> bytes:
    """Зашифровать строго один блок, без паддинга."""
    if len(pt_block) != BLOCK_SIZE:
        raise ValueError("Блок AES должен содержать ровно 16 байт.")
    round_keys = expand_key(key)
    state = add_round_key(list(pt_block), round_keys[0])

    for round_number in range(1, 10):
        state = sub_bytes(state)
        state = shift_rows(state)
        state = mix_columns(state)
        state = add_round_key(state, round_keys[round_number])

    state = sub_bytes(state)
    state = shift_rows(state)
    state = add_round_key(state, round_keys[10])
    return bytes(state)

def decrypt_block(ct_block: bytes, key: bytes) -> bytes:
    """Расшифровать строго один блок, без снятия паддинга."""
    if len(ct_block) != BLOCK_SIZE:
        raise ValueError("Блок AES должен содержать ровно 16 байт.")
    round_keys = expand_key(key)
    state = add_round_key(list(ct_block), round_keys[10])

    for round_number in range(9, 0, -1):
        state = shift_rows(state, inverse=True)
        state = sub_bytes(state, inverse=True)
        state = add_round_key(state, round_keys[round_number])
        state = mix_columns(state, inverse=True)

    state = shift_rows(state, inverse=True)
    state = sub_bytes(state, inverse=True)
    state = add_round_key(state, round_keys[0])
    return bytes(state)

```

### modes.py

```python
def pad(data: bytes) -> bytes:
    padding_length = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + bytes([padding_length]) * padding_length

def unpad(data: bytes) -> bytes:
    if not data or len(data) % BLOCK_SIZE != 0:
        raise ValueError("Некорректное дополнение PKCS#7.")
    padding_length = data[-1]
    if not 1 <= padding_length <= BLOCK_SIZE:
        raise ValueError("Некорректное дополнение PKCS#7.")
    expected = bytes([padding_length]) * padding_length
    if data[-padding_length:] != expected:
        raise ValueError("Некорректное дополнение PKCS#7.")
    return data[:-padding_length]

def encrypt_ecb(data: bytes, key: bytes) -> bytes:
    padded = pad(data)
    result = bytearray()
    for offset in range(0, len(padded), BLOCK_SIZE):
        result.extend(encrypt_block(padded[offset:offset + BLOCK_SIZE], key))
    return bytes(result)

def decrypt_ecb(data: bytes, key: bytes) -> bytes:
    validate_ciphertext(data)
    result = bytearray()
    for offset in range(0, len(data), BLOCK_SIZE):
        result.extend(decrypt_block(data[offset:offset + BLOCK_SIZE], key))
    return unpad(bytes(result))

def encrypt_cbc(data: bytes, key: bytes, iv: bytes) -> bytes:
    validate_iv(iv)
    padded = pad(data)
    previous = iv
    result = bytearray()
    for offset in range(0, len(padded), BLOCK_SIZE):
        block = padded[offset:offset + BLOCK_SIZE]
        encrypted = encrypt_block(xor_blocks(block, previous), key)
        result.extend(encrypted)
        previous = encrypted
    return bytes(result)

def decrypt_cbc(data: bytes, key: bytes, iv: bytes) -> bytes:
    validate_iv(iv)
    validate_ciphertext(data)
    previous = iv
    result = bytearray()
    for offset in range(0, len(data), BLOCK_SIZE):
        block = data[offset:offset + BLOCK_SIZE]
        decrypted = xor_blocks(decrypt_block(block, key), previous)
        result.extend(decrypted)
        previous = block
    return unpad(bytes(result))

```

## 5. Результаты тестирования

Тесты фактически выполнены в Python. Все 9 тестовых методов завершились успешно;
внутри тестов дополнительно проверяются разные длины сообщений и ошибки ввода.

| Проверка | Результат |
| --- | --- |
| Один блок AES: контрольный пример NIST | Совпадение шифротекста и восстановление блока |
| ECB: четыре блока NIST | Все четыре блока совпали |
| CBC: четыре блока NIST | Все четыре блока совпали |
| PKCS#7 для длин 0–64 байта | Дополнение и удаление корректны |
| Неверное дополнение | Отклонено с ValueError |
| Обратное преобразование в ECB/CBC | Длины 0–64, русский текст, все значения байтов восстановлены |
| Файл с повторяющимися блоками | ECB: 1 уникальный блок из 8; CBC: 8 из 8 |
| Изменение IV | Шифротекст CBC изменился |
| Неверные длины ключа, блока, IV, шифротекста | Отклонены с ValueError |

Векторы NIST не содержат PKCS#7, поэтому проверяются первые 64 байта
результата режимов. Дополнительный пятый блок является паддингом.
Расшифрование проверяется на эталонных блоках с отдельно построенным блоком дополнения.

### 5.1. Дополнение и тестовые строки

| Исходная строка | Байт UTF-8 | Добавлено | Байт шифротекста ECB / CBC |
| --- | ---: | ---: | ---: |
| Hello | 5 | 11 | 16 / 16 |
| 1234567890ABCDEF | 16 | 16 | 32 / 32 |
| 1234567890ABCDEFG | 17 | 15 | 32 / 32 |
| Привет, мир! | 21 | 11 | 32 / 32 |
| Пустая строка | 0 | 16 | 16 / 16 |

Все строки после расшифрования совпали с исходными.
Длины шифротекста в таблице указаны без IV.

### 5.2. Сравнение паттернов

Создан файл `patterns.bin`: строка `0123456789ABCDEF` повторена восемь раз.
Каждая копия занимает ровно один блок. Общий размер — 128 байт.
Результаты обоих режимов занимают по 144 байта с учётом полного блока PKCS#7.
Сравниваются первые восемь блоков, без блока дополнения.

В ECB все восемь шифроблоков одинаковы. В CBC в данном эксперименте
все восемь различаются. Таблица ниже содержит фактический вывод программы,
а не смоделированные результаты. CBC скрывает прямое повторение блоков,
поскольку вход AES зависит от предыдущего шифроблока.
Это не означает невозможность любых совпадений для произвольных данных.

### 5.3. Полный вывод демонстрации

```text
ЛР3. Вариант 1. AES-128 / ECB / CBC / PKCS#7
Учебный ключ: 000102030405060708090a0b0c0d0e0f

Текст: 'Hello'
Длина UTF-8: 5 байт
Добавлено PKCS#7: 11 байт
ECB (16 байт): 94e11c4e7b21b9e66c0082a5089604ea
CBC (16 байт): 4eb776c0e33a04f4acee982118fa28a9
IV: e078a83fb3305f84f5152d975ec821a2
После ECB: 'Hello'
После CBC: 'Hello'

Текст: '1234567890ABCDEF'
Длина UTF-8: 16 байт
Добавлено PKCS#7: 16 байт
ECB (32 байт): 106406de0a60c6f5a7e9c5b2fe2bbdff954f64f2e4e86e9eee82d20216684899
CBC (32 байт): afee4c62a8c3252b4f0536e9db8f76939cb0256fc8614d751b52b09b26b9d4c7
IV: ec94243222546eab571ca4ab0fea5d32
После ECB: '1234567890ABCDEF'
После CBC: '1234567890ABCDEF'

Текст: '1234567890ABCDEFG'
Длина UTF-8: 17 байт
Добавлено PKCS#7: 15 байт
ECB (32 байт): 106406de0a60c6f5a7e9c5b2fe2bbdff9d8936a64546c76e61cd81f0068f7f0a
CBC (32 байт): cc37e0aec3e2985ea850a3c3a30842e8ac760b8fad611df104844a442d7b4606
IV: 99f7f600243e575d423011a3e440feec
После ECB: '1234567890ABCDEFG'
После CBC: '1234567890ABCDEFG'

Текст: 'Привет, мир!'
Длина UTF-8: 21 байт
Добавлено PKCS#7: 11 байт
ECB (32 байт): 9d8a97e4b83c003c44d85dc84d14eaa7bb5519f5659548c98e3414f9d7993781
CBC (32 байт): d7e85d8532847be7e46248d505d487c66f9b443e6ed98a77a7c43e4411e5c389
IV: 3a65d2586c1764590ca7e22f64abdca5
После ECB: 'Привет, мир!'
После CBC: 'Привет, мир!'

Текст: ''
Длина UTF-8: 0 байт
Добавлено PKCS#7: 16 байт
ECB (16 байт): 954f64f2e4e86e9eee82d20216684899
CBC (16 байт): 73c1458af9584d9b37d2e7ff47e0504b
IV: 92c5ae0d923daf60a023649f53d6cbb5
После ECB: ''
После CBC: ''

СРАВНЕНИЕ ПАТТЕРНОВ: 8 одинаковых исходных блоков
IV: f6b98585cfe6edf32aff979ad892647f
 № | ECB                              | CBC
 1 | a5ba2b6280d433bccfe6a0461cb88c4e | 90b154907a11f542034998f88dbb725b
 2 | a5ba2b6280d433bccfe6a0461cb88c4e | 7fd1c2b2ecd217bfdbc6227c4ea994e4
 3 | a5ba2b6280d433bccfe6a0461cb88c4e | e7ceda5f098e54f3c1bbd78a4e5942e3
 4 | a5ba2b6280d433bccfe6a0461cb88c4e | 3993590326d649fe8b63fbd95f703a0d
 5 | a5ba2b6280d433bccfe6a0461cb88c4e | b601652fefde7a6af4a5e4da137a9181
 6 | a5ba2b6280d433bccfe6a0461cb88c4e | e7b1ec4e9feae4b0ca48ae1a33ca5a21
 7 | a5ba2b6280d433bccfe6a0461cb88c4e | 362b45316f8f0edd045a984327b3d3bc
 8 | a5ba2b6280d433bccfe6a0461cb88c4e | 035d8e970076e252742cf34c285c7029
Девятый блок — дополнение PKCS#7, в таблице не показан.
ECB: уникальных блоков данных 1 из 8
CBC: уникальных блоков данных 8 из 8
Обратное восстановление обоих файлов: OK

```

### 5.4. Протокол тестов

```text
test_block_known_answer (test_lab.LabTests.test_block_known_answer) ... ok
test_cbc_nist (test_lab.LabTests.test_cbc_nist) ... ok
test_ecb_nist (test_lab.LabTests.test_ecb_nist) ... ok
test_invalid_lengths (test_lab.LabTests.test_invalid_lengths) ... ok
test_invalid_padding (test_lab.LabTests.test_invalid_padding) ... ok
test_iv_changes_ciphertext (test_lab.LabTests.test_iv_changes_ciphertext) ... ok
test_padding_lengths (test_lab.LabTests.test_padding_lengths) ... ok
test_patterns (test_lab.LabTests.test_patterns) ... ok
test_round_trip (test_lab.LabTests.test_round_trip) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.387s

OK

```

## 6. Вывод

В ходе работы реализованы AES-128, режимы ECB и CBC, а также дополнение
PKCS#7. Корректность проверена контрольными примерами и восстановлением
исходных сообщений. Для сообщений длиной 5, 16 и 17 байт подтверждено
добавление соответственно 11, 16 и 15 байт. Эксперимент с повторяющимися
блоками показал, что ECB сохраняет их повторяемость, а CBC скрывает её
за счёт сцепления блоков и использования IV.


