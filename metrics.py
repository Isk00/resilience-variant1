"""metrics.py - метрики надежности по CSV прогона (ts,status,latency_ms).

POFOD  = неудачных запросов / всех запросов (неудачный - код не 200)
эпизод = серия неудачных запросов с промежутками меньше 2 с
ROCOF  = эпизодов / длительность в часах
AVAIL  = доля секунд, в которые был хотя бы один удачный ответ
pXX    = сортировка задержек и элемент с номером ceil(p * n)

Запуск: python3 metrics.py results/off.csv
"""
import csv
import math
import sys

GAP = 2.0


def load(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.reader(f):
            try:
                rows.append((float(r[0]), int(r[1]), float(r[2])))
            except (ValueError, IndexError):
                continue                       # заголовок и посторонние строки
    return rows


def perc(vals, p):
    return vals[max(1, math.ceil(p * len(vals))) - 1]


def compute(rows):
    n = len(rows)
    t0 = min(r[0] for r in rows)
    fails = sorted(r[0] for r in rows if r[1] != 200)

    episodes, prev = 0, None
    for t in fails:
        if prev is None or t - prev >= GAP:
            episodes += 1
        prev = t

    seconds = math.floor(max(r[0] for r in rows) - t0) + 1
    ok = {math.floor(r[0] - t0) for r in rows if r[1] == 200}
    lat = sorted(r[2] for r in rows)
    return {
        "n": n, "failed": len(fails),
        "pofod": len(fails) / n,
        "episodes": episodes,
        "rocof": episodes / (seconds / 3600),
        "avail": len(ok) / seconds,
        "p50": perc(lat, 0.50), "p95": perc(lat, 0.95), "p99": perc(lat, 0.99),
    }


if __name__ == "__main__":
    for path in sys.argv[1:]:
        m = compute(load(path))
        print(f"{path}: запросов={m['n']} неудачных={m['failed']} "
              f"POFOD={m['pofod']:.4f} эпизодов={m['episodes']} ROCOF={m['rocof']:.1f}/ч "
              f"AVAIL={m['avail']:.4f} p50/p95/p99={m['p50']:.0f}/{m['p95']:.0f}/{m['p99']:.0f} мс")
