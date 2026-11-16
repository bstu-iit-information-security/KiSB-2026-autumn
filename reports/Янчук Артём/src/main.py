import ctypes
from module1_ec_algebra import EllipticCurveAlgebra
from module2_protocols import CryptoProtocols


def main():
    # Стандартизированные параметры кривой ГОСТ Р 34.10-2012 (Приложение А, 256 бит) в сыром Hex
    P_HEX  = "8000000000000000000000000000000000000000000000000000000000000431"
    A_HEX  = "0000000000000000000000000000000000000000000000000000000000000007"
    B_HEX  = "5FBFF498AA938CE739B8E022FBAFEF40563F6E6A3472FC2A514C0CE9DAE23B7E"
    Q_HEX  = "8000000000000000000000000000000050FE8A1892976154C59CFC193ACCF5B3"
    GX_HEX = "0000000000000000000000000000000000000000000000000000000000000002"
    GY_HEX = "08E2A8A0E65147D4BD6316030E16D19C85C97F0A9CA267122B96ABBCEA7E8FC8"

    curve = EllipticCurveAlgebra(P_HEX, A_HEX, B_HEX, Q_HEX, GX_HEX, GY_HEX)
    protocols = CryptoProtocols(curve)

    print("=" * 80)
    print("ЛАБОРАТОРНАЯ РАБОТА №4 | ВАРИАНТ 13 (ГОСТ Р 34.10-2012, ЯКОБИ, HEAP-FREE)")
    print("=" * 80)
    print(f"Параметр p  : {P_HEX}")
    print(f"Параметр a  : {A_HEX}")
    print(f"Параметр b  : {B_HEX}")
    print(f"Порядок  q  : {Q_HEX}")
    print(f"База     Gx : {GX_HEX}")
    print(f"База     Gy : {GY_HEX}")
    print(f"Проверка G на кривой : {curve.is_on_curve_affine(curve.gx, curve.gy)}")
    print(f"Размер статической арены точек: {ctypes.sizeof(curve.arena._buf)} байт "
          f"({curve.arena.TOTAL_SLOTS} слотов по 96 байт)")

    # --------------------------------------------------------------------------
    # 1. ТЕСТИРОВАНИЕ ПРОТОКОЛА СОГЛАСОВАНИЯ КЛЮЧЕЙ ECDH
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("1. ПРОТОКОЛ ДИФФИ-ХЕЛЛМАНА НА ЭЛЛИПТИЧЕСКОЙ КРИВОЙ (ECDH)")
    print("-" * 80)
    DA_HEX = "1F66B5B84B7339674533F0329C74F21834281FED27B97230427902FEC904F823"
    DB_HEX = "5A0E2894E350C40B1A266A55B9D1E1960F29E2693A77C51F4B990D2E9B832F15"

    da, qa_x, qa_y = protocols.generate_keypair(DA_HEX)
    db, qb_x, qb_y = protocols.generate_keypair(DB_HEX)

    print(f"Секретный ключ Алисы dA : {da}")
    print(f"Открытый ключ Алисы QAx : {qa_x}")
    print(f"Открытый ключ Алисы QAy : {qa_y}")
    print(f"Секретный ключ Боба  dB : {db}")
    print(f"Открытый ключ Боба  QBx : {qb_x}")
    print(f"Открытый ключ Боба  QBy : {qb_y}")

    alice_kx, _ = protocols.ecdh_shared_secret(da, qb_x, qb_y)
    bob_kx, _   = protocols.ecdh_shared_secret(db, qa_x, qa_y)

    print(f"Shared Secret Алисы (Kx): {alice_kx}")
    print(f"Shared Secret Боба  (Kx): {bob_kx}")
    secrets_match = curve.arena.ct_eq(int(alice_kx, 16), int(bob_kx, 16)) == 1
    print(f"Совпадение Shared Secret: {secrets_match}")

    # --------------------------------------------------------------------------
    # 2. ТЕСТИРОВАНИЕ ЭЦП ГОСТ Р 34.10-2012 НА КОНТРОЛЬНОМ ВЕКТОРЕ СТАНДАРТА
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("2. ВЫРАБОТКА И ПРОВЕРКА ЭЦП ГОСТ Р 34.10-2012 (ТЕСТОВЫЙ ВЕКТОР)")
    print("-" * 80)
    D_SIGN_HEX = "7A929ADE789BB9BE10ED359DD39A72C11B60961F49397EEE1D19CE9891EC3B28"
    K_EPH_HEX  = "77105C9B20BCD3122823C8CF6FCC7B956DE33814E95B7FE64FED924594DCEAB3"
    HASH_E_HEX = "2DFBC1B372D89A1188C09C52E0EEC61FCE52032AB1022E8E67ECE6672B043EE5"

    _, q_sign_x, q_sign_y = protocols.generate_keypair(D_SIGN_HEX)
    print(f"Секретный ключ подписи d : {D_SIGN_HEX}")
    print(f"Открытый ключ проверки Qx: {q_sign_x}")
    print(f"Открытый ключ проверки Qy: {q_sign_y}")
    print(f"Хэш сообщения e (Hex)    : {HASH_E_HEX}")

    r_hex, s_hex = protocols.sign_gost_2012(D_SIGN_HEX, HASH_E_HEX, K_EPH_HEX)
    print(f"Компонент подписи r      : {r_hex}")
    print(f"Компонент подписи s      : {s_hex}")

    valid, r_calc_hex = protocols.verify_gost_2012(q_sign_x, q_sign_y, HASH_E_HEX, r_hex, s_hex)
    print(f"Вычисленный R при вериф. : {r_calc_hex}")
    print(f"Результат проверки (R==r): {valid}")

    # --------------------------------------------------------------------------
    # 3. ДЕМОНСТРАЦИЯ ОТБРАКОВКИ ПОДПИСИ ПРИ ИСКАЖЕНИИ ОДНОГО БАЙТА В ПАРАМЕТРЕ s
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("3. ТЕСТ ЦЕЛОСТНОСТИ: ПРЕДНАМЕРЕННОЕ ИСКАЖЕНИЕ ОДНОГО БАЙТА В ПАРАМЕТРЕ s")
    print("-" * 80)
    # Инвертируем младший байт параметра s (XOR с 0xFF)
    s_corrupted_int = int(s_hex, 16) ^ 0xFF
    s_corrupted_hex = f"{s_corrupted_int:064X}"
    print(f"Оригинальный параметр s  : {s_hex}")
    print(f"Искаженный параметр   s' : {s_corrupted_hex}")

    valid_corrupted, r_corrupted_hex = protocols.verify_gost_2012(
        q_sign_x, q_sign_y, HASH_E_HEX, r_hex, s_corrupted_hex
    )
    print(f"Ожидаемый компонент   r  : {r_hex}")
    print(f"Вычисленный компонент R' : {r_corrupted_hex}")
    print(f"Результат проверки (R'==r): {valid_corrupted} (Подпись отбракована)")
    print("=" * 80)


if __name__ == "__main__":
    main()