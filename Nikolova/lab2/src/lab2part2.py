
N = 4

planes = [
    [[0, 1, 1, 1], [1, 0, 1, 0], [0, 0, 1, 0], [1, 1, 0, 0]],  # а
    [[0, 1, 1, 0], [1, 0, 1, 0], [0, 0, 1, 0], [1, 1, 0, 0]],  # б
    [[0, 1, 1, 1], [1, 0, 1, 0], [0, 0, 1, 0], [0, 1, 0, 0]],  # в
    [[0, 1, 1, 1], [1, 0, 1, 0], [0, 0, 1, 0], [1, 1, 0, 0]],  # г
]
names = ["а", "б", "в", "г"]

for p in range(4):
    d = planes[p]

    hor = []
    for i in range(N):
        hor.append(sum(d[i]) % 2)

    ver = []
    for j in range(N):
        s = 0
        for i in range(N):
            s += d[i][j]
        ver.append(s % 2)

    diag1 = []
    for k in range(N):
        s = 0
        for i in range(N):
            for j in range(N):
                if (i + j) % N == k:
                    s += d[i][j]
        diag1.append(s % 2)

   
    diag2 = []
    for k in range(N):
        s = 0
        for i in range(N):
            for j in range(N):
                if (i - j) % N == N - 1 - k:
                    s += d[i][j]
        diag2.append(s % 2)

    xhv = sum(hor) % 2

    print("Плоскость", names[p])
    print("Информационные биты + горизонтальные паритеты:")
    for i in range(N):
        print(*d[i], "|", hor[i])
    print("Вертикальные паритеты:", *ver, "|", xhv)
    print("Диагональные 1:", *diag1)
    print("Диагональные 2:", *diag2)
    print()


print("z-паритеты:")
for i in range(N):
    row = []
    for j in range(N):
        s = 0
        for p in range(4):
            s += planes[p][i][j]
        row.append(s % 2)
    print(*row)