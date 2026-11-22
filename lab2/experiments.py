import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import hamming
import iterative

OUT = "results"
TRIALS_H = 2000
TRIALS_I = 3000


def hamming_examples(text, bits):
    cases = [(3, 0, 5), (3, 1, 5), (3, 2, 12), (4, 1, 5), (4, 2, 7)]
    bits = bits[:24]
    text = text[:3]
    import random
    for d, e, seed in cases:
        rng = random.Random(seed)
        n = len(bits) + len(hamming.build_matrix(len(bits), d))
        pos = sorted(rng.sample(range(n), e))
        out = hamming.make_report(text, bits, d, pos, seed)
        with open(f"{OUT}/hamming_d{d}_e{e}.txt", "w", encoding="utf-8") as f:
            f.write(out + "\n")


def iterative_examples():
    import random
    rng = random.Random(10)
    code = iterative.Code(5, 8, 1, 3)
    xk = [rng.randint(0, 1) for _ in range(code.k)]
    for name, errs in (("e1", [30]), ("e2", [3, 50]), ("e3", [2, 9, 20])):
        with open(f"{OUT}/iterative_{name}.txt", "w", encoding="utf-8") as f:
            f.write(iterative.show(code, xk, errs) + "\n")


def charts(rows):
    cfgs = iterative.VARIANTS[5]
    fig, axs = plt.subplots(2, 2, figsize=(9, 6.5))
    for ax, cfg in zip(axs.flat, cfgs):
        sel = [r for r in rows if r["cfg"] == cfg]
        gs = [r["groups"] for r in sel]
        for i in (1, 2, 3, 4):
            ax.plot(gs, [r[i][1] for r in sel], marker="o", label=f"{i} ош.")
        ax.set_title(f"{cfg[0]}x{cfg[1]}" + (f"x{cfg[2]}" if cfg[2] > 1 else ""))
        ax.set_xticks(gs)
        ax.set_ylim(-0.03, 1.03)
        ax.set_xlabel("групп паритетов")
        ax.set_ylabel("N3/N1")
        ax.grid(alpha=0.3)
    axs[0][0].legend()
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_iterative.png", dpi=150)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    text = open("input.txt", encoding="utf-8").read().strip()
    bits = hamming.text_to_bits(text)
    hamming_examples(text, bits)
    iterative_examples()
    hs = hamming.run_stat(bits, [16, 24, 64, 256, 1024], TRIALS_H, 1)
    rows = iterative.run_stat(5, TRIALS_I, [1, 2, 3, 4], 1)
    charts(rows)
    with open(f"{OUT}/hamming_stat.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["k", "r", "n", "d", "1 ошибка: исправлено", "2 ошибки: исправлено неверно",
                    "2 ошибки: обнаружено"])
        for r in hs:
            w.writerow([r["k"], r["r"], r["n"], r["d"], r[1][0], r[2][1], r[2][2]])
    with open(f"{OUT}/iterative_stat.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["k1", "k2", "z", "групп", "r", "n"] + [f"N2/N1 ({i})" for i in range(1, 5)]
                   + [f"N3/N1 ({i})" for i in range(1, 5)])
        for r in rows:
            w.writerow(list(r["cfg"]) + [r["groups"], r["r"], r["n"]]
                       + [r[i][0] for i in range(1, 5)] + [r[i][1] for i in range(1, 5)])
    json.dump({"hamming": hs, "iterative": [{**r, "cfg": list(r["cfg"])} for r in rows]},
              open(f"{OUT}/stat.json", "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
