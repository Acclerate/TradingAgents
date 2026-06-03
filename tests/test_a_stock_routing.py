import unittest

import pytest

from tradingagents.dataflows.ticker_utils import (
    is_a_stock_ticker,
    normalize_a_stock_ticker,
    normalize_input_ticker,
    should_use_akshare_for_ticker,
)


@pytest.mark.unit
class TestAStockRouting(unittest.TestCase):
    def test_normalize_input_ticker_maps_chinese_alias(self):
        self.assertEqual(normalize_input_ticker("数据港"), "603881")

    def test_sh_suffix_is_compatible_with_a_stock_detection(self):
        self.assertEqual(normalize_input_ticker("603881.SH"), "603881.SS")
        self.assertTrue(is_a_stock_ticker("603881.SH"))
        self.assertEqual(normalize_a_stock_ticker("603881.SH"), "603881")

    def test_routing_helper_forces_akshare_for_sh_suffix_and_alias(self):
        self.assertTrue(should_use_akshare_for_ticker("603881.SH"))
        self.assertTrue(should_use_akshare_for_ticker("数据港"))
        self.assertFalse(should_use_akshare_for_ticker("AAPL"))


if __name__ == "__main__":
    unittest.main()
