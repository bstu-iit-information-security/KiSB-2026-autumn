
from module1.curves import get_test_curve, get_secp256k1
from module1.elliptic_curve import Point

from module2.ecdh import ECDH
from module2.ecdsa import ECDSA

from module3.secure_operations import SecureOperations
def read_hex(prompt):
    """Чтение шестнадцатеричного числа."""

    value = input(prompt).strip()

    if value.lower().startswith("0x"):
        value = value[2:]

    if not value:
        raise ValueError("Пустое значение")

    return int(value, 16)


def print_point(point):
    """Вывод точки в шестнадцатеричном формате."""

    if point.is_infinity:
        print("O (бесконечно удаленная точка)")
        return

    print("X =", format(point.x, "X"))
    print("Y =", format(point.y, "X"))


def choose_curve():
    return get_secp256k1()


def field_menu(curve):
    field = curve.field

    print("\n=== АРИФМЕТИКА КОНЕЧНОГО ПОЛЯ ===")
    print("1. Сложение")
    print("2. Вычитание")
    print("3. Умножение")
    print("4. Инверсия")
    print("5. Деление")

    choice = input("Операция: ")

    a = read_hex("Введите A (Hex): ")

    if choice == "4":
        result = field.inverse(a)

    else:
        b = read_hex("Введите B (Hex): ")

        if choice == "1":
            result = field.add(a, b)
        elif choice == "2":
            result = field.sub(a, b)
        elif choice == "3":
            result = field.mul(a, b)
        elif choice == "5":
            result = field.div(a, b)
        else:
            print("Неизвестная операция")
            return

    print("Результат (Hex):", format(result, "X"))

def point_menu(curve):
    print("\n=== ОПЕРАЦИИ С ТОЧКАМИ ===")
    print("1. Проверить точку")
    print("2. Сложить две точки")
    print("3. Удвоить точку")
    print("4. Скалярное умножение")

    choice = input("Ваш выбор: ").strip()

    x1 = read_hex("Введите X1 (Hex): ")
    y1 = read_hex("Введите Y1 (Hex): ")

    P = Point(x1, y1)

    if choice == "1":
        print("Принадлежит кривой:", curve.is_on_curve(P))
        return

    if not curve.is_on_curve(P):
        print("Ошибка: точка не принадлежит кривой")
        return

    if choice == "2":
        x2 = read_hex("Введите X2 (Hex): ")
        y2 = read_hex("Введите Y2 (Hex): ")

        Q = Point(x2, y2)
        result = curve.add(P, Q)

    elif choice == "3":
        result = curve.double(P)

    elif choice == "4":
        k = read_hex("Введите скаляр K (Hex): ")
        result = curve.multiply(k, P)

    else:
        print("Неизвестная операция")
        return

    print("\nРезультат:")
    print_point(result)


def ecdh_menu(curve):
    print("\n=== ПРОТОКОЛ ECDH ===")

    protocol = ECDH(curve)

    print("1. Сгенерировать ключи автоматически")
    print("2. Ввести секретные ключи вручную")

    choice = input("Ваш выбор: ").strip()

    if choice == "1":
        dA = protocol.generate_private_key()
        dB = protocol.generate_private_key()

    elif choice == "2":
        dA = read_hex("Секретный ключ Алисы dA (Hex): ")
        dB = read_hex("Секретный ключ Боба dB (Hex): ")

    else:
        print("Неизвестная операция")
        return

    QA = protocol.generate_public_key(dA)
    QB = protocol.generate_public_key(dB)

    print("\nОткрытый ключ Алисы QA:")
    print_point(QA)

    print("\nОткрытый ключ Боба QB:")
    print_point(QB)

    KA = protocol.compute_shared_secret(dA, QB)
    KB = protocol.compute_shared_secret(dB, QA)

    print("\nОбщий секрет Алисы:")
    print(format(KA, "X"))

    print("\nОбщий секрет Боба:")
    print(format(KB, "X"))

    print("\nСовпадение секретов:", KA == KB)


def ecdsa_menu(curve):
    print("\n=== ЭЛЕКТРОННАЯ ЦИФРОВАЯ ПОДПИСЬ ECDSA ===")

    algorithm = ECDSA(curve)

    print("1. Создать ключи автоматически")
    print("2. Ввести секретный ключ вручную")

    choice = input("Ваш выбор: ").strip()

    if choice == "1":
        private_key = algorithm.generate_private_key()

    elif choice == "2":
        private_key = read_hex("Секретный ключ d (Hex): ")

    else:
        print("Неизвестная операция")
        return

    public_key = algorithm.generate_public_key(private_key)

    print("\nОткрытый ключ:")
    print_point(public_key)

    message_hex = input(
        "\nВведите сообщение в Hex (байты): "
    ).strip()

    if message_hex.lower().startswith("0x"):
        message_hex = message_hex[2:]

    if len(message_hex) % 2 != 0:
        raise ValueError("Hex сообщения должен содержать четное число символов")

    message = bytes.fromhex(message_hex)

    signature = algorithm.sign(message, private_key)

    r, s = signature

    print("\nПодпись:")
    print("r =", format(r, "X"))
    print("s =", format(s, "X"))

    valid = algorithm.verify(
        message,
        signature,
        public_key
    )

    print("\nПроверка исходного сообщения:", valid)

    modified_message = message + b"\x01"

    modified_valid = algorithm.verify(
        modified_message,
        signature,
        public_key
    )

    print("Проверка измененного сообщения:", modified_valid)


def secure_menu(curve):
    print("\n=== CONSTANT-TIME ОПЕРАЦИИ ===")
    print("1. Модульная инверсия")
    print("2. Защищенное скалярное умножение")
    print("3. Ослепление скаляра")

    choice = input("Ваш выбор: ").strip()

    secure = SecureOperations(curve)

    if choice == "1":
        a = read_hex("Введите A (Hex): ")

        result = secure.secure_inverse(a)

        print("Обратный элемент:")
        print(format(result, "X"))

        print(
            "Проверка:",
            (a * result) % curve.p == 1
        )

    elif choice == "2":
        k = read_hex("Введите скаляр K (Hex): ")

        result = secure.secure_multiply(k, curve.G)

        print("Результат защищенного умножения:")
        print_point(result)

        ordinary = curve.multiply(k, curve.G)

        print(
            "Совпадение с Double-and-Add:",
            result == ordinary
        )

    elif choice == "3":
        d = read_hex("Введите скаляр D (Hex): ")

        blinded = secure.blind_scalar(d)

        print("Исходный скаляр:", format(d, "X"))
        print("Ослепленный скаляр:", format(blinded, "X"))

        original = curve.multiply(d, curve.G)
        protected = curve.multiply(blinded, curve.G)

        print("Совпадение точек:", original == protected)

    else:
        print("Неизвестная операция")


def main():
        curve = choose_curve()

        print("\nКривая успешно загружена.")
        print("Модуль p:", format(curve.p, "X"))
        print("Коэффициент a:", format(curve.a, "X"))
        print("Коэффициент b:", format(curve.b, "X"))
        print("Порядок q:", format(curve.q, "X"))

        while True:

            print("\n========== ГЛАВНОЕ МЕНЮ ==========")
            print("1. Арифметика конечного поля")
            print("2. Операции с точками")
            print("3. Протокол ECDH")
            print("4. Цифровая подпись ECDSA")
            print("5. Constant-Time операции")
            print("6. Выход")

            choice = input("\nВыберите пункт: ").strip()

            try:
                if choice == "1":
                    field_menu(curve)

                elif choice == "2":
                    point_menu(curve)

                elif choice == "3":
                    ecdh_menu(curve)

                elif choice == "4":
                    ecdsa_menu(curve)

                elif choice == "5":
                    secure_menu(curve)

                elif choice == "6":
                    print("Завершение программы.")
                    break

                else:
                    print("Неверный пункт меню.")

            except (ValueError, ZeroDivisionError) as error:
                print("Ошибка:", error)

    # except (ValueError, ZeroDivisionError) as error:
    #     print("Ошибка инициализации:", error)


if __name__ == "__main__":
    main()
