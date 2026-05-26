"""Tests for direct_sources: Sina Finance stock data."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.direct_sources.sina_stock import (
    _calc_change_percent,
    _calc_updown,
    _format_number,
    _parse_a_stock,
    _parse_domestic_future,
    _parse_intl_future,
    _parse_us_stock,
    sina_get_realtime,
    sina_search_future,
    get_stock_data_sina,
    get_futures_data_sina,
)


@pytest.mark.unit
class TestFormatNumber(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(_format_number("123.456"), "123.46")

    def test_zero(self):
        self.assertEqual(_format_number("0"), "0.00")

    def test_invalid(self):
        self.assertEqual(_format_number("abc"), "--")


@pytest.mark.unit
class TestCalcChangePercent(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(_calc_change_percent("11", "10"), "+10.00")

    def test_negative(self):
        self.assertEqual(_calc_change_percent("9", "10"), "-10.00")

    def test_zero_yestclose(self):
        self.assertEqual(_calc_change_percent("10", "0"), "0.00")


@pytest.mark.unit
class TestCalcUpdown(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(_calc_updown("11", "10"), "1.00")


@pytest.mark.unit
class TestParseAStock(unittest.TestCase):
    def test_normal_parse(self):
        # Simulate Sina response: name, open, yestclose, price, high, low,
        # buy1, sell1, vol, amount, ... date(30), time(31)
        params = ["平安银行", "12.00", "11.80", "12.10", "12.20", "11.90",
                   "12.10", "12.11", "100000", "1200000"]
        params += [""] * 20  # pad to 32
        params += ["2025-01-15", "15:00:00"]

        result = _parse_a_stock("sz000001", params)
        self.assertEqual(result["code"], "sz000001")
        self.assertEqual(result["name"], "平安银行")
        self.assertEqual(result["price"], "12.10")
        self.assertEqual(result["type"], "a_stock")
        self.assertIn("time", result)

    def test_zero_price_fallback_to_buy1(self):
        params = ["TEST", "10", "10", "0", "0", "0", "10.5", "10.6", "0", "0"]
        params += [""] * 22
        result = _parse_a_stock("sh600000", params)
        self.assertEqual(result["price"], "10.50")

    def test_zero_price_fallback_to_yestclose(self):
        params = ["TEST", "10", "10", "0", "0", "0", "0", "0", "0", "0"]
        params += [""] * 22
        result = _parse_a_stock("sh600000", params)
        self.assertEqual(result["price"], "10.00")


@pytest.mark.unit
class TestParseUSStock(unittest.TestCase):
    def test_normal_parse(self):
        params = ["英伟达", "198.69", "-3.96", "2025-01-15", "-8.19",
                   "203.00", "203.97", "197.93"]
        params += ["", ""]  # 8-9
        params += ["189303100"]  # 10 volume
        params += [""] * 10  # 11-20
        params += ["197.63"]  # 21 pre price
        params += ["-0.53"]  # 22 pre pct
        params += [""] * 3
        params += ["Nov 05 04:27AM EST"]  # 26 time (yest)
        params += ["206.88"]  # 26 yestclose

        result = _parse_us_stock("usr_nvda", params)
        self.assertEqual(result["name"], "英伟达")
        self.assertEqual(result["type"], "us_stock")
        self.assertIn("pre_market_price", result)


@pytest.mark.unit
class TestParseDomesticFuture(unittest.TestCase):
    def test_commodity_future(self):
        # Commodity futures: name, X, open(2), high(3), low(4), yestclose(5),
        # buy1(6), sell1(7), price(8), avg(9), settlement(10), ...
        params = ["PVC2501", "", "8585", "8692", "8467", "", "8673", "8674",
                   "8675", "8630", "8821", "109", "2", "289274", "230643"]
        params += [""] * 10

        result = _parse_domestic_future("nf_V2501", params)
        self.assertIn("name", result)
        self.assertEqual(result["type"], "domestic_future")
        self.assertIn("yest_settlement", result)

    def test_stock_index_future(self):
        # Stock index: open(0), high(1), low(2), close(3), volume(4), ...
        # yestclose(13), yest_settlement(14), ... name(49)
        params = ["5372.0", "5585.0", "5343.0", "5581.6", "47855"]
        params += ["", "", ""]  # 5-7
        params += ["261716510.0"]  # 8
        params += ["124729.0"]  # 9
        params += ["5581.6"]  # 10
        params += [""] * 2  # 11-12
        params += ["5342.8"]  # 13 yestclose
        params += ["5318.0"]  # 14 yest_settlement
        params += [""] * 34
        params += ['中证500指数期货2206"']  # 49 name

        result = _parse_domestic_future("nf_IC0", params)
        self.assertEqual(result["type"], "domestic_future")


@pytest.mark.unit
class TestParseIntlFuture(unittest.TestCase):
    def test_normal_parse(self):
        params = ["105.306", "", "105.270", "105.290", "105.540", "102.950",
                   "15:51:34", "102.410", "103.500", "250168.000", "5", "2",
                   "2022-05-04", "WTI纽约原油2206", "28346\""]

        result = _parse_intl_future("hf_OIL", params)
        self.assertEqual(result["type"], "intl_future")
        self.assertIn("WTI", result.get("name", ""))


@pytest.mark.unit
class TestSinaGetRealtime(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.sina_stock.requests.get")
    def test_empty_codes(self, mock_get):
        result = sina_get_realtime([])
        self.assertEqual(result, [])
        mock_get.assert_not_called()

    @patch("tradingagents.dataflows.direct_sources.sina_stock.requests.get")
    def test_a_stock_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.content = (
            'var hq_str_sh600036="招商银行,35.00,34.80,35.10,35.20,34.90,'
            '35.10,35.11,100000,3500000,--,--,--,--,--,--,--,--,--,--,'
            ',--,--,--,--,--,--,--,--,--,--,2025-01-15,15:00:00";'
        ).encode("gb18030")
        mock_get.return_value = mock_resp

        results = sina_get_realtime(["sh600036"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["code"], "sh600036")
        self.assertEqual(results[0]["name"], "招商银行")
        self.assertEqual(results[0]["type"], "a_stock")


@pytest.mark.unit
class TestSinaSearchFuture(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.sina_stock.requests.get")
    def test_empty_keyword(self, mock_get):
        result = sina_search_future("")
        self.assertEqual(result, [])

    @patch("tradingagents.dataflows.direct_sources.sina_stock.requests.get")
    def test_search_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.content = (
            'var suggestvalue="IF2501,85,期货,if2501,沪深300股指期货主力,;'

            'hf_OIL,86,期货,hf_oil,WTI原油期货,;"'
        ).encode("gb18030")
        mock_get.return_value = mock_resp

        results = sina_search_future("原油")
        self.assertIsInstance(results, list)


@pytest.mark.unit
class TestVendorWrappers(unittest.TestCase):
    @patch("tradingagents.dataflows.direct_sources.sina_stock.sina_get_realtime")
    def test_get_futures_data_sina(self, mock_realtime):
        mock_realtime.return_value = [{
            "code": "nf_IF0", "name": "沪深300主力", "type": "domestic_future",
            "price": "3800.00", "updown": "20.00", "percent": "+0.53",
            "open": "3780.00", "high": "3810.00", "low": "3770.00",
            "yestclose": "3780.00", "yest_settlement": "3780.00",
            "volume": "100000", "time": "2025-01-15 15:00",
        }]
        result = get_futures_data_sina("nf_IF0", "2025-01-01", "2025-01-15")
        self.assertIn("沪深300主力", result)
        self.assertIn("3800.00", result)
