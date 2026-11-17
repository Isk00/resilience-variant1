"""Тесты паттерна failover без кластера: call_dep и call_dep_b подменяются."""
import time
import unittest
import urllib.error

import core


def ok(timeout=10.0):
    return {"source": "ok"}


def down(timeout=10.0):
    raise urllib.error.HTTPError("http://dep", 503, "down", None, None)


def slow(timeout=10.0):                   # станция "тормозит" дольше таймаута
    time.sleep(timeout)
    raise TimeoutError


class FailoverTest(unittest.TestCase):
    def setUp(self):
        self.orig = (core.call_dep, core.call_dep_b, core.FAILBACK)
        core.PATTERN = True
        core.a_down_until = 0.0
        self.calls = []

    def tearDown(self):
        core.call_dep, core.call_dep_b, core.FAILBACK = self.orig
        core.PATTERN = False

    def track(self, name, fn):
        def wrapper(timeout=10.0):
            self.calls.append(name)
            return fn(timeout)
        return wrapper

    def test_a_ok_answer_from_a(self):
        core.call_dep = self.track("a", ok)
        core.call_dep_b = self.track("b", ok)
        core.do_work()
        self.assertEqual(self.calls, ["a"])

    def test_a_down_answer_from_b(self):
        core.call_dep = self.track("a", down)
        core.call_dep_b = self.track("b", lambda t: {"source": "dep-b"})
        r = core.do_work()
        self.assertEqual(r["source"], "dep-b")
        self.assertEqual(self.calls, ["a", "b"])

    def test_a_slow_answer_faster_than_user_timeout(self):
        core.call_dep = slow
        core.call_dep_b = ok
        start = time.time()
        core.do_work()
        self.assertLess(time.time() - start, 1.5)     # пользователь ждет 1,5 с

    def test_after_failure_a_is_skipped(self):
        core.call_dep = self.track("a", down)
        core.call_dep_b = self.track("b", ok)
        for _ in range(3):
            core.do_work()
        self.assertEqual(self.calls.count("a"), 1)

    def test_failback_to_a_after_pause(self):
        core.FAILBACK = 0.05
        core.call_dep = self.track("a", down)
        core.call_dep_b = self.track("b", ok)
        core.do_work()
        core.call_dep = self.track("a", ok)          # основную станцию починили
        time.sleep(0.1)
        self.calls.clear()
        core.do_work()
        self.assertEqual(self.calls, ["a"])

    def test_both_down_error(self):
        core.call_dep = down
        core.call_dep_b = down
        with self.assertRaises(urllib.error.HTTPError):
            core.do_work()

    def test_pattern_off_only_a(self):
        core.PATTERN = False
        core.call_dep = self.track("a", down)
        core.call_dep_b = self.track("b", ok)
        with self.assertRaises(urllib.error.HTTPError):
            core.do_work()
        self.assertEqual(self.calls, ["a"])


if __name__ == "__main__":
    unittest.main()
