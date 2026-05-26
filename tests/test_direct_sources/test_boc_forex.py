"""Tests for direct_sources: Bank of China forex rates."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.direct_sources.boc_forex import (
    get_boc_forex_rates,
    get_forex_summary,
    get_forex_data_boc,
)


_SAMPLE_HTML = """<html><body><table></table>
<table>
<tr><th>Currency</th><th>Buy</th><th>Sell</th></tr>
<tr><td>美元</td><td>7.10</td><td>7.15</td><td>7.08</td><td>7.18</td><td>7.12</td><td>2025-01-15</td></tr>
<tr><td>欧元</td><td>7.80</td><td>7.85</td><td>7.78</td><td>7.88</td><td>7.82</td><td>2025-01-15</td></tr>
</table></body></html>"""


@pytest.mark.unit
class TestGetBocForexRates(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.boc_forex.requests.get")
    def test_parse_html(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = _SAMPLE_HTML
        mock_resp.encoding = "utf-8"
        mock_get.return_value = mock_resp

        df = get_boc_forex_rates()
        self.assertFalse(df.empty)
        self.assertIn("name", df.columns)
        self.assertEqual(len(df), 2)

    @patch("tradingagents.dataflows.direct_sources.boc_forex.requests.get")
    def test_empty_page(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body></body></html>"
        mock_resp.encoding = "utf-8"
        mock_get.return_value = mock_resp

        df = get_boc_forex_rates()
        self.assertTrue(df.empty)


@pytest.mark.unit
class TestGetForexSummary(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.boc_forex.get_boc_forex_rates")
    def test_formatted_output(self, mock_rates):
        import pandas as pd
        mock_rates.return_value = pd.DataFrame([
            {"name": "美元", "spot_buy": 7.10, "cash_buy": 7.08, "spot_sell": 7.15, "cash_sell": 7.18, "conversion_price": 7.12},
            {"name": "欧元", "spot_buy": 7.80, "cash_buy": 7.78, "spot_sell": 7.85, "cash_sell": 7.88, "conversion_price": 7.82},
        ])
        result = get_forex_summary()
        self.assertIn("外汇牌价", result)
        self.assertIn("美元", result)
        self.assertIn("欧元", result)

    @patch("tradingagents.dataflows.direct_sources.boc_forex.get_boc_forex_rates")
    def test_empty_rates(self, mock_rates):
        import pandas as pd
        mock_rates.return_value = pd.DataFrame()
        result = get_forex_summary()
        self.assertIn("No forex data", result)


@pytest.mark.unit
class TestVendorWrapper(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.boc_forex.get_forex_summary")
    def test_get_forex_data_boc(self, mock_summary):
        mock_summary.return_value = "BOC Forex Data"
        result = get_forex_data_boc()
        self.assertEqual(result, "BOC Forex Data")
