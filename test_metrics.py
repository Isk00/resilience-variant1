"""Проверка metrics.py на примере из задания: 20 запросов за 10 с."""
import unittest

import metrics

STATUS = [200] * 8 + [500, 500, 500, 503, 503, 500] + [200] * 6
OK_LAT = [38, 39, 39, 40, 40, 41, 42, 43, 44, 45, 46, 47, 51, 180]
BAD_LAT = [1000, 1001, 1001, 1002, 1003, 1004]


def rows():
    ok, bad = iter(OK_LAT), iter(BAD_LAT)
    return [(1000 + i * 0.5, s, next(ok) if s == 200 else next(bad)) for i, s in enumerate(STATUS)]


class MetricsTest(unittest.TestCase):
    def test_example(self):
        m = metrics.compute(rows())
        self.assertAlmostEqual(m["pofod"], 0.30)
        self.assertEqual(m["episodes"], 1)
        self.assertAlmostEqual(m["rocof"], 360)
        self.assertAlmostEqual(m["avail"], 0.70)
        self.assertEqual((m["p50"], m["p95"], m["p99"]), (45, 1003, 1004))

    def test_two_episodes(self):
        r = [(0, 500, 1), (1, 500, 1), (5, 500, 1), (9, 200, 1)]
        self.assertEqual(metrics.compute(r)["episodes"], 2)


if __name__ == "__main__":
    unittest.main()
