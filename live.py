"""live.py - живой вывод прогона: читает CSV нагрузки построчно (из kubectl logs -f)
и каждые 3 секунды печатает, сколько запросов прошло успешно.

Используется внутри demo.sh, отдельно запускать не нужно.
"""
import sys

STEP = 3
WIDTH = 20


def phase(sec):
    if sec < 30:
        return "норма          "
    if sec < 60:
        return "ОТКАЗ dep-a    "
    return "dep-a починили "


def bar(ok, n):
    full = round(WIDTH * ok / n) if n else 0
    return "█" * full + "░" * (WIDTH - full)


def main():
    print(" время      | фаза            | ответы пользователям (█ успех, ░ ошибка)")
    print("------------+-----------------+------------------------------------------")
    t0 = None
    buckets = {}
    printed = -1

    def flush(upto):
        nonlocal printed
        for b in range(printed + 1, upto + 1):
            ok, bad = buckets.pop(b, (0, 0))
            n = ok + bad
            sec = b * STEP
            mark = "  <- ошибки!" if bad else ""
            print(f"{sec:3d}-{sec + STEP:<3d} с  | {phase(sec)} | {bar(ok, n)} {ok:3d}/{n:<3d}{mark}", flush=True)
            printed = b

    for line in sys.stdin:
        parts = line.strip().split(",")
        try:
            ts, status = float(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            continue
        if t0 is None:
            t0 = ts
        b = int((ts - t0) // STEP)
        ok, bad = buckets.get(b, (0, 0))
        buckets[b] = (ok + (status == 200), bad + (status != 200))
        # ответы приходят с задержкой до 1,5 с, поэтому печатаем промежуток,
        # когда уже пошли запросы на 2 промежутка позже
        if b - 2 > printed:
            flush(b - 2)
    if buckets:
        flush(max(buckets))


if __name__ == "__main__":
    main()