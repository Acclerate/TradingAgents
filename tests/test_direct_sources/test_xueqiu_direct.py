"""Tests for direct_sources: Xueqiu direct API."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.direct_sources.xueqiu_direct import (
    xueqiu_get_token,
    xueqiu_get_user_timeline,
    xueqiu_get_user_info,
    _get_headers,
)


@pytest.mark.unit
class TestXueqiuGetToken(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct.requests.get")
    def test_successful_token(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.headers = {"set-cookie": "xq_a_token=abc123; Path=/; device_id=xyz;"}
        mock_get.return_value = mock_resp

        token = xueqiu_get_token()
        self.assertIn("xq_a_token=abc123", token)

    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct.requests.get")
    def test_failure_returns_fallback(self, mock_get):
        mock_get.side_effect = Exception("network error")
        token = xueqiu_get_token()
        self.assertIn("device_id=", token)


@pytest.mark.unit
class TestGetHeaders(unittest.TestCase):
    def test_contains_cookies(self):
        headers = _get_headers()
        self.assertIn("Cookie", headers)
        self.assertIn("User-Agent", headers)


@pytest.mark.unit
class TestXueqiuGetUserTimeline(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct.requests.get")
    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct._cookies", "test_cookie")
    def test_normal_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "statuses": [
                {"id": "1", "user_id": "123", "title": "市场分析", "text": "大盘走势",
                 "created_at": 1700000000, "retweet_count": 10, "reply_count": 5, "like_count": 20},
            ]
        }
        mock_get.return_value = mock_resp

        results = xueqiu_get_user_timeline("123")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "市场分析")
        self.assertEqual(results[0]["source"], "雪球")

    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct.requests.get")
    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct._cookies", "test_cookie")
    def test_api_failure(self, mock_get):
        mock_get.side_effect = Exception("network error")
        results = xueqiu_get_user_timeline("123")
        self.assertEqual(results, [])


@pytest.mark.unit
class TestXueqiuGetUserInfo(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct.requests.get")
    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct._cookies", "test_cookie")
    def test_normal_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {"user": {"screen_name": "测试用户", "id": 123}}
        }
        mock_get.return_value = mock_resp

        info = xueqiu_get_user_info("123")
        self.assertIsNotNone(info)
        self.assertEqual(info["screen_name"], "测试用户")

    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct.requests.get")
    @patch("tradingagents.dataflows.direct_sources.xueqiu_direct._cookies", "test_cookie")
    def test_failure_returns_none(self, mock_get):
        mock_get.side_effect = Exception("network error")
        info = xueqiu_get_user_info("123")
        self.assertIsNone(info)
