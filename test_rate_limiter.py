import unittest

from rate_limiter import RateLimiter


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RateLimiterTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_allows_up_to_limit_then_blocks(self) -> None:
        clock = _Clock()
        limiter = RateLimiter(max_requests=2, window_seconds=10, time_func=clock.time)

        self.assertTrue(await limiter.check(123))
        self.assertTrue(await limiter.check(123))
        self.assertFalse(await limiter.check(123))

    async def test_allows_again_after_window_passes(self) -> None:
        clock = _Clock()
        limiter = RateLimiter(max_requests=2, window_seconds=10, time_func=clock.time)

        await limiter.check(123)
        await limiter.check(123)
        clock.advance(10)

        self.assertTrue(await limiter.check(123))

    async def test_retry_after_reports_remaining_seconds(self) -> None:
        clock = _Clock()
        limiter = RateLimiter(max_requests=2, window_seconds=10, time_func=clock.time)

        await limiter.check(123)
        clock.advance(1.2)
        await limiter.check(123)
        clock.advance(1.3)

        self.assertEqual(await limiter.get_retry_after(123), 8)

    async def test_owner_is_exempt(self) -> None:
        limiter = RateLimiter(max_requests=1, window_seconds=30, exempt_user_ids={999})

        self.assertTrue(await limiter.check(999))
        self.assertTrue(await limiter.check(999))
        self.assertEqual(await limiter.get_retry_after(999), 0)

    async def test_retry_after_is_zero_after_window_expires(self) -> None:
        clock = _Clock()
        limiter = RateLimiter(max_requests=1, window_seconds=10, time_func=clock.time)

        await limiter.check(123)
        clock.advance(10)

        self.assertEqual(await limiter.get_retry_after(123), 0)
