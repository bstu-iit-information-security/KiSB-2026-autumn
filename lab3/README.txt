Лабораторная работа №3, вариант 15: AES-128, режимы ECB + CFB

src/aes128.py  - модуль 1, блочный шифр AES-128 (encrypt_block / decrypt_block)
src/modes.py   - модуль 2, режимы ECB и CFB, дополнение PKCS#7
src/lab3.py    - меню, тесты и исследования
rep/           - отчёт
results/       - рисунки, зашифрованные BMP и вывод программы

Запуск (Python 3.8+):
    pip install matplotlib numpy
    cd src
    python lab3.py
Пункт 0 меню выполняет всё сразу; результаты сохраняются в src/results.
matplotlib и numpy нужны только для рисунков, шифр реализован без сторонних библиотек.
