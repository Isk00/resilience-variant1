"""timeline.py - что происходило во время прогона, по 5 секунд.

Запуск:  python3 timeline.py results/off.csv results/on.csv

Для каждого промежутка показывает, сколько запросов пользователей
прошло успешно (█) и сколько упало (░). Можно передать один файл
или два - тогда они будут рядом для сравнения.
"""
import csv
import sys

STEP = 5      # секунд в одной строке
WIDTH = 20    # ширина полоски


def load(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.reader(f):
            try:
                rows.append((float(r[0]), int(r[1])))
            except (ValueError, IndexError):
                continue
    t0 = min(t for t, _ in rows)
    buckets = {}
    for t, s in rows:
        b = int((t - t0) // STEP)
        ok, bad = buckets.get(b, (0, 0))
        buckets[b] = (ok + (s == 200), bad + (s != 200))
    return buckets


def bar(ok, bad):
    n = ok + bad
    if n == 0:
        return " " * WIDTH + "   нет данных"
    full = round(WIDTH * ok / n)
    return "█" * full + "░" * (WIDTH - full) + f" {ok:3d}/{n:<3d}"


def phase(sec):
    if 30 <= sec < 60:
        return "<- dep-a сломана"
    return ""


def main(paths):
    data = [load(p) for p in paths]
    last = max(max(d) for d in data)
    names = ["без паттерна (off)" if "off" in p else "с паттерном (on)" if "on" in p else p for p in paths]
    head = " время    | " + " | ".join(f"{n:<28}" for n in names)
    print(head)
    print("-" * len(head))
    for b in range(last + 1):
        sec = b * STEP
        cols = [f"{bar(*d.get(b, (0, 0))):<28}" for d in data]
        print(f"{sec:3d}-{sec + STEP:<3d} с | " + " | ".join(cols) + "  " + phase(sec))
    print()
    print("█ - успешный ответ пользователю, ░ - ошибка (неудачный запрос)")
    for p, d in zip(paths, data):
        ok = sum(v[0] for v in d.values())
        bad = sum(v[1] for v in d.values())
        print(f"{p}: успешных {ok}, неудачных {bad} из {ok + bad}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
