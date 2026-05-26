"""Tests for direct_sources: Tencent HK stock data."""

import json
import unittest
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.direct_sources.tencent_hk import (
    tencent_search_stock,
    tencent_get_hk_stocks,
    get_hk_stock_data_tencent,
)


@pytest.mark.unit
class TestTencentSearchStock(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.tencent_hk.requests.get")
    def test_empty_keyword(self, mock_get):
        result = tencent_search_stock("")
        self.assertEqual(result, [])

    @patch("tradingagents.dataflows.direct_sources.tencent_hk.requests.get")
    def test_search_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "stock": [
                    ["hk", "00700", "腾讯控股", "TX"],
                    ["sh", "600036", "招商银行", "ZSYH"],
                ]
            }
        }
        mock_get.return_value = mock_resp

        results = tencent_search_stock("腾讯")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["market"], "hk")
        self.assertEqual(results[0]["name"], "腾讯控股")


@pytest.mark.unit
class TestTencentGetHKStocks(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.tencent_hk.requests.get")
    def test_empty_codes(self, mock_get):
        result = tencent_get_hk_stocks([])
        self.assertEqual(result, [])

    @patch("tradingagents.dataflows.direct_sources.tencent_hk.requests.get")
    def test_single_stock(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.content = json.dumps({
            "r_hk00700": [
                "", "腾讯控股", "", "380.00", "378.00", "379.00",
                "", "", "", "", "", "", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "", "",
                "2025-01-15 16:00", "", "",
                "382.00", "377.00", "", "50000000", "19000000000",
            ]
        }).encode("gbk")
        mock_get.return_value = mock_resp

        results = tencent_get_hk_stocks(["hk00700"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["code"], "hk00700")
        self.assertEqual(results[0]["name"], "腾讯控股")
        self.assertEqual(results[0]["type"], "hk_stock")
        self.assertIn("percent", results[0])

    @patch("tradingagents.dataflows.direct_sources.tencent_hk.requests.get")
    def test_nodata_stock(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.content = json.dumps({}).encode("gbk")
        mock_get.return_value = mock_resp

        results = tencent_get_hk_stocks(["hk99999"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "NODATA")


@pytest.mark.unit
class TestVendorWrapper(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.tencent_hk.tencent_get_hk_stocks")
    @patch("tradingagents.dataflows.direct_sources.tencent_hk_history.tencent_get_hk_hist")
    def test_realtime_fallback(self, mock_hist, mock_hk):
        import pandas as pd
        mock_hist.return_value = pd.DataFrame()  # Force realtime fallback
        mock_hk.return_value = [{
            "code": "hk00700", "name": "TX", "type": "hk_stock",
            "price": "380.00", "updown": "2.00", "percent": "+0.53",
            "open": "378.00", "high": "382.00", "low": "377.00",
            "volume": "50000000", "time": "2025-01-15 16:00",
        }]
        result = get_hk_stock_data_tencent("hk00700", "2025-01-01", "2025-01-15")
        self.assertIn("380.00", result)
