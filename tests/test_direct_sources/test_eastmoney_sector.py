"""Tests for direct_sources: East Money sector capital flow."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.direct_sources.eastmoney_sector import (
    _convert_to_yi,
    _to_dataframe,
    get_sector_capital_flow,
)


@pytest.mark.unit
class TestConvertToYi(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(_convert_to_yi(1e8), 1.0)

    def test_large_number(self):
        self.assertEqual(_convert_to_yi(5.5e9), 55.0)

    def test_zero(self):
        self.assertEqual(_convert_to_yi(0), 0.0)

    def test_invalid(self):
        self.assertEqual(_convert_to_yi("abc"), 0.0)


@pytest.mark.unit
class TestToDataframe(unittest.TestCase):
    def test_empty_data(self):
        df = _to_dataframe({"data": {}})
        self.assertTrue(df.empty)

    def test_normal_data(self):
        raw = {
            "data": {
                "diff": [
                    {"f14": "电子元件", "f174": 500000000},
                    {"f14": "银行", "f174": -300000000},
                ]
            }
        }
        df = _to_dataframe(raw)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["name"], "电子元件")  # sorted by inflow desc

    def test_exclude_filter(self):
        raw = {
            "data": {
                "diff": [
                    {"f14": "沪深", "f174": 100000000},
                    {"f14": "电子元件", "f174": 200000000},
                ]
            }
        }
        df = _to_dataframe(raw, exclude=["沪深"])
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["name"], "电子元件")


@pytest.mark.unit
class TestGetSectorCapitalFlow(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.eastmoney_sector._fetch_sector_data")
    def test_formatted_output(self, mock_fetch):
        mock_fetch.return_value = {
            "data": {
                "diff": [
                    {"f14": "电子元件", "f174": 5e8},
                    {"f14": "银行", "f174": -3e8},
                ]
            }
        }
        result = get_sector_capital_flow("industry")
        self.assertIn("电子元件", result)
        self.assertIn("银行", result)
        self.assertIn("行业板块资金流向", result)

    @patch("tradingagents.dataflows.direct_sources.eastmoney_sector._fetch_sector_data")
    def test_empty_data(self, mock_fetch):
        mock_fetch.return_value = {"data": {}}
        result = get_sector_capital_flow("industry")
        self.assertIn("No", result)

    def test_invalid_sector_type(self):
        with self.assertRaises(ValueError):
            from tradingagents.dataflows.direct_sources.eastmoney_sector import _fetch_sector_data
            _fetch_sector_data("invalid")
