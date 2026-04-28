import unittest

from rate_limiter import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def now(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class SlidingWindowRateLimiterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.limiter = SlidingWindowRateLimiter(2, 1.0, now_func=self.clock.now)

    def test_allows_up_to_limit_inside_window(self) -> None:
        self.assertTrue(self.limiter.allow("u1"))
        self.assertTrue(self.limiter.allow("u1"))
        self.assertFalse(self.limiter.allow("u1"))

    def test_users_are_isolated(self) -> None:
        self.assertTrue(self.limiter.allow("u1"))
        self.assertTrue(self.limiter.allow("u1"))
        self.assertTrue(self.limiter.allow("u2"))
        self.assertTrue(self.limiter.allow("u2"))
        self.assertFalse(self.limiter.allow("u1"))
        self.assertFalse(self.limiter.allow("u2"))

    def test_expired_requests_are_pruned(self) -> None:
        self.assertTrue(self.limiter.allow("u1"))
        self.assertTrue(self.limiter.allow("u1"))
        self.clock.advance(1.1)
        self.assertTrue(self.limiter.allow("u1"))
        self.assertTrue(self.limiter.allow("u1"))
        self.assertFalse(self.limiter.allow("u1"))

    def test_window_is_sliding_not_fixed(self) -> None:
        self.assertTrue(self.limiter.allow("u1"))
        self.clock.advance(0.5)
        self.assertTrue(self.limiter.allow("u1"))
        self.clock.advance(0.49)
        self.assertFalse(self.limiter.allow("u1"))

    def test_invalid_configuration_raises(self) -> None:
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(0, 1.0)
        with self.assertRaises(ValueError):
            SlidingWindowRateLimiter(1, 0)


if __name__ == "__main__":
    unittest.main()
