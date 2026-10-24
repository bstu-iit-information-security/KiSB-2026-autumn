from main import MacLarenMarsaglia, cycle

# Полный перебор выбранного семейства: два ЛКГ по модулям 10 и 5.
maximum = checked = 0
for a in range(1, 10):
    for c in range(10):
        for b in range(1, 5):
            for d in range(5):
                for x in range(10):
                    for y in range(5):
                        period = cycle(MacLarenMarsaglia(a, c, b, d, x, y))[2]
                        maximum = max(maximum, period)
                        checked += 1
assert maximum == 10
print(f'Проверено сочетаний: {checked}; максимальный период выходов: {maximum}')
