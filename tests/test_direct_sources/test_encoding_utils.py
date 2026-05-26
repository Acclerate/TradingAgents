"""Tests for direct_sources: encoding utilities."""

import unittest

import pytest

from tradingagents.dataflows.direct_sources.encoding_utils import (
    decode_gb18030,
    decode_gbk,
)


@pytest.mark.unit
class TestDecodeGB18030(unittest.TestCase):
    def test_ascii_passthrough(self):
        self.assertEqual(decode_gb18030(b"hello"), "hello")

    def test_chinese_text(self):
        # "上证指数" in GB18030
        raw = "上证指数".encode("gb18030")
        self.assertEqual(decode_gb18030(raw), "上证指数")

    def test_string_passthrough(self):
        self.assertEqual(decode_gb18030("already str"), "already str")

    def test_latin1_fallback(self):
        # Bytes that are invalid GB18030 should not crash
        invalid = b"\x80\x81\x82"
        result = decode_gb18030(invalid)
        self.assertIsInstance(result, str)


@pytest.mark.unit
class TestDecodeGBK(unittest.TestCase):
    def test_ascii_passthrough(self):
        self.assertEqual(decode_gbk(b"hello"), "hello")

    def test_chinese_text(self):
        raw = "沪深300".encode("gbk")
        self.assertEqual(decode_gbk(raw), "沪深300")

    def test_string_passthrough(self):
        self.assertEqual(decode_gbk("already str"), "already str")

    def test_latin1_fallback(self):
        invalid = b"\x80\x81\x82"
        result = decode_gbk(invalid)
        self.assertIsInstance(result, str)
