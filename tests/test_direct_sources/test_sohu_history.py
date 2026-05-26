"""Tests for direct_sources: Sohu historical data."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.direct_sources.sohu_history import sohu_get_hist_data


_SAMPLE_JSONP = (
    'historySearchHandler({"code":"cn_000001","hq":[["2025-01-15","12.50","12.80","2.40","0.30","100000","12.60","0.85"],["2025-01-14","12.30","12.50","1.63","0.20","80000","12.40","0.68"]]});'
)


@pytest.mark.unit
class TestSohuGetHistData(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.sohu_history.requests.get")
    def test_normal_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = _SAMPLE_JSONP
        mock_get.return_value = mock_resp

        df = sohu_get_hist_data("000001", "20250101", "20250115")
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertIn("Date", df.columns)
        self.assertIn("Open", df.columns)
        self.assertIn("Close", df.columns)

    @patch("tradingagents.dataflows.direct_sources.sohu_history.requests.get")
    def test_empty_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = 'historySearchHandler({"code":"cn_000001","hq":[]});'
        mock_get.return_value = mock_resp

        df = sohu_get_hist_data("000001", "20250101", "20250115")
        self.assertTrue(df.empty)

    @patch("tradingagents.dataflows.direct_sources.sohu_history.requests.get")
    def test_chronological_order(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = _SAMPLE_JSONP
        mock_get.return_value = mock_resp

        df = sohu_get_hist_data("000001", "20250101", "20250115")
        # Should be oldest first (reversed from Sohu's newest-first)
        dates = df["Date"].tolist()
        self.assertLess(dates[0], dates[-1])
