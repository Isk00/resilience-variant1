"""FAIR для варианта 1: PERT-средние и Монте-Карло (10 000 лет)."""
import random

def pert(lo, ml, hi, lam=4):
    a = 1 + lam * (ml - lo) / (hi - lo)
    b = 1 + lam * (hi - ml) / (hi - lo)
    return lo + random.betavariate(a, b) * (hi - lo)

def mean(lo, ml, hi):
    return (lo + 4 * ml + hi) / 6

LEF = (3, 7, 15); LM = (10, 30, 86); LM_AFTER = (2.5, 7.5, 21.6); COST = 92
lef, lm, lm2 = mean(*LEF), mean(*LM), mean(*LM_AFTER)
ale, ale2 = lef * lm, lef * lm2
print(f"LEF={lef:.2f} LM={lm:.2f} LM_after={lm2:.2f}")
print(f"ALE до={ale:.1f} после={ale2:.1f} ROSI={(ale - ale2 - COST) / COST:.2f}")

random.seed(1)
N = 10000
before, after = [], []
for _ in range(N):
    n = round(pert(*LEF))
    before.append(sum(pert(*LM) for _ in range(n)))
    after.append(sum(pert(*LM_AFTER) for _ in range(n)))
for name, xs in (("до", before), ("после", after)):
    xs.sort()
    print(f"МК {name}: среднее={sum(xs)/N:.0f} P50={xs[N//2]:.0f} P90={xs[int(N*.9)]:.0f}")
