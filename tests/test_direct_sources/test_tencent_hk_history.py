"""Tests for direct_sources: Tencent HK historical data."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.direct_sources.tencent_hk_history import (
    _normalize_symbol,
    tencent_get_hk_hist,
)


@pytest.mark.unit
class TestNormalizeSymbol(unittest.TestCase):
    def test_numeric_code_padding(self):
        self.assertEqual(_normalize_symbol("hk00700"), "hk00700")

    def test_short_numeric_code(self):
        self.assertEqual(_normalize_symbol("hk700"), "hk00700")

    def test_index_uppercase(self):
        self.assertEqual(_normalize_symbol("hkHSI"), "hkHSI")

    def test_plain_numeric(self):
        self.assertEqual(_normalize_symbol("00700"), "hk00700")

    def test_none_too_short(self):
        self.assertIsNone(_normalize_symbol("hk"))

    def test_empty(self):
        self.assertIsNone(_normalize_symbol(""))


@pytest.mark.unit
class TestTencentGetHkHist(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.tencent_hk_history.requests.get")
    def test_normal_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "hk00700": {
                    "day": [
                        ["2025-01-15", "378.00", "380.00", "382.00", "377.00", "50000000"],
                        ["2025-01-14", "375.00", "378.00", "379.00", "374.00", "45000000"],
                    ]
                }
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        df = tencent_get_hk_hist("hk00700", "2025-01-01", "2025-01-15")
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertIn("Date", df.columns)
        self.assertIn("Open", df.columns)

    @patch("tradingagents.dataflows.direct_sources.tencent_hk_history.requests.get")
    def test_empty_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        df = tencent_get_hk_hist("hk00700", "2025-01-01", "2025-01-15")
        self.assertTrue(df.empty)

    @patch("tradingagents.dataflows.direct_sources.tencent_hk_history.requests.get")
    def test_qfqday_fallback(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "hk00700": {
                    "qfqday": [
                        ["2025-01-15", "378.00", "380.00", "382.00", "377.00", "50000000"],
                    ]
                }
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        df = tencent_get_hk_hist("hk00700", "2025-01-01", "2025-01-15")
        self.assertEqual(len(df), 1)
