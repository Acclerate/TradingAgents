"""Encoding utilities for Chinese financial data sources.

Sina Finance returns GB18030, Tencent returns GBK.
These helpers decode raw bytes to Python str (UTF-8 internally).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def decode_gb18030(data) -> str:
    """Decode bytes or bytearray from GB18030 (Sina Finance encoding).

    Falls back to latin-1 if GB18030 decoding fails.
    """
    if isinstance(data, str):
        return data
    try:
        return data.decode("gb18030")
    except (UnicodeDecodeError, AttributeError):
        try:
            return data.decode("latin-1")
        except Exception:
            return str(data)


def decode_gbk(data) -> str:
    """Decode bytes or bytearray from GBK (Tencent stock API encoding).

    Falls back to latin-1 if GBK decoding fails.
    """
    if isinstance(data, str):
        return data
    try:
        return data.decode("gbk")
    except (UnicodeDecodeError, AttributeError):
        try:
            return data.decode("latin-1")
        except Exception:
            return str(data)
