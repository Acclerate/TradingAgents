"""Tests for direct_sources: anti_scraping utilities."""

import threading
import time
import unittest

import pytest

from tradingagents.dataflows.direct_sources.anti_scraping import (
    RateLimiter,
    _UA_POOL,
    _REFERER_MAP,
    random_headers,
    random_ua,
    retry_with_backoff,
    get_limiter,
)


@pytest.mark.unit
class TestUserAgentPool(unittest.TestCase):
    def test_random_ua_returns_string(self):
        ua = random_ua()
        self.assertIsInstance(ua, str)
        self.assertTrue(len(ua) > 50)

    def test_random_ua_is_from_pool(self):
        for _ in range(20):
            self.assertIn(random_ua(), _UA_POOL)


@pytest.mark.unit
class TestRandomHeaders(unittest.TestCase):
    def test_default_referer_is_sina(self):
        h = random_headers()
        self.assertIn("finance.sina.com.cn", h["Referer"])

    def test_custom_referer_key(self):
        h = random_headers("xueqiu")
        self.assertEqual(h["Referer"], "https://xueqiu.com/")

    def test_full_url_referer(self):
        h = random_headers("https://example.com/api")
        self.assertEqual(h["Referer"], "https://example.com/api")

    def test_has_required_headers(self):
        h = random_headers()
        self.assertIn("User-Agent", h)
        self.assertIn("Referer", h)
        self.assertIn("Accept", h)
        self.assertIn("Accept-Language", h)


@pytest.mark.unit
class TestRateLimiter(unittest.TestCase):
    def test_high_rate_limiter_does_not_block(self):
        limiter = RateLimiter(rate=1000)
        start = time.monotonic()
        limiter.wait()
        limiter.wait()
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.1)

    def test_thread_safety(self):
        limiter = RateLimiter(rate=100)
        errors = []

        def worker():
            try:
                for _ in range(5):
                    limiter.wait()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


@pytest.mark.unit
class TestRetryWithBackoff(unittest.TestCase):
    def test_success_no_retry(self):
        call_count = 0

        @retry_with_backoff(retries=3, delay_base=0.01)
        def ok_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = ok_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)

    def test_retries_on_failure(self):
        call_count = 0

        @retry_with_backoff(retries=2, delay_base=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("fail")
            return "ok"

        result = flaky_func()
        self.assertEqual(result, "ok")
        self.assertEqual(call_count, 3)

    def test_raises_after_max_retries(self):
        @retry_with_backoff(retries=1, delay_base=0.01)
        def always_fail():
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            always_fail()


@pytest.mark.unit
class TestGetLimiter(unittest.TestCase):
    def test_known_source(self):
        limiter = get_limiter("sina")
        self.assertIsInstance(limiter, RateLimiter)

    def test_unknown_source_returns_default(self):
        limiter = get_limiter("nonexistent")
        self.assertIsInstance(limiter, RateLimiter)
