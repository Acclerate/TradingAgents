"""Tests for direct_sources: Xuangubao flash news."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.direct_sources.xuangubao import (
    get_xuangubao_flash_news,
    get_xuangubao_news_formatted,
)


_SAMPLE_RESPONSE = {
    "data": {
        "messages": [
            {
                "id": "1",
                "title": "半导体板块异动拉升",
                "summary": "中芯国际涨超5%",
                "created_at": 1700000000,
            },
            {
                "id": "2",
                "title": "北向资金净流入超50亿",
                "summary": "沪深股通持续净买入",
                "created_at": 1700000100,
            },
        ]
    }
}


@pytest.mark.unit
class TestGetXuangubaoFlashNews(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.xuangubao.requests.get")
    def test_normal_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        results = get_xuangubao_flash_news(limit=5)
        self.assertIsInstance(results, list)
        # Should have results from multiple subject IDs (may deduplicate)
        self.assertTrue(len(results) >= 1)
        self.assertIn("source", results[0])
        self.assertEqual(results[0]["source"], "选股宝")

    @patch("tradingagents.dataflows.direct_sources.xuangubao.requests.get")
    def test_api_failure(self, mock_get):
        mock_get.side_effect = Exception("network error")
        results = get_xuangubao_flash_news(limit=5)
        self.assertEqual(results, [])


@pytest.mark.unit
class TestGetXuangubaoNewsFormatted(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.xuangubao.get_xuangubao_flash_news")
    def test_formatted_output(self, mock_news):
        mock_news.return_value = [
            {"title": "测试新闻", "summary": "摘要", "created_at": 1700000000, "id": "1"},
        ]
        result = get_xuangubao_news_formatted(limit=5)
        self.assertIn("选股宝异动快讯", result)
        self.assertIn("测试新闻", result)

    @patch("tradingagents.dataflows.direct_sources.xuangubao.get_xuangubao_flash_news")
    def test_empty_news(self, mock_news):
        mock_news.return_value = []
        result = get_xuangubao_news_formatted(limit=5)
        self.assertIn("No flash news", result)
