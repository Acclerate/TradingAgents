"""Integration tests: vendor routing and agent tool registration."""

import ast
import importlib
import unittest
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestInterfaceRegistration(unittest.TestCase):
    """Verify all new methods and vendors are registered in interface.py."""

    def _get_vendor_methods(self):
        """Parse VENDOR_METHODS from interface.py via AST (no import needed)."""
        with open("tradingagents/dataflows/interface.py", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "VENDOR_METHODS":
                        return node.value
        return None

    def test_new_methods_in_source(self):
        """Check source code contains all new method registrations."""
        with open("tradingagents/dataflows/interface.py", encoding="utf-8") as f:
            source = f.read()

        required_methods = [
            "get_hk_stock_data",
            "get_futures_data",
            "get_forex_data",
            "get_sector_flow",
        ]
        for method in required_methods:
            self.assertIn(f'"{method}"', source, f"Method {method} not registered")

    def test_new_vendors_in_source(self):
        with open("tradingagents/dataflows/interface.py", encoding="utf-8") as f:
            source = f.read()

        required_vendors = [
            "sina_direct",
            "tencent_direct",
            "eastmoney_direct",
            "boc_direct",
        ]
        for vendor in required_vendors:
            self.assertIn(f'"{vendor}"', source, f"Vendor {vendor} not registered")


@pytest.mark.unit
class TestToolFilesSyntax(unittest.TestCase):
    """Verify all agent tool files have valid Python syntax and @tool decorator."""

    TOOL_FILES = [
        "tradingagents/agents/utils/futures_tools.py",
        "tradingagents/agents/utils/forex_tools.py",
        "tradingagents/agents/utils/sector_flow_tools.py",
        "tradingagents/agents/utils/hk_stock_tools.py",
    ]

    def test_syntax_valid(self):
        for path in self.TOOL_FILES:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            self.assertTrue(len(funcs) >= 1, f"{path} has no functions")

    def test_has_tool_decorator(self):
        for path in self.TOOL_FILES:
            with open(path, encoding="utf-8") as f:
                source = f.read()
            self.assertIn("@tool", source, f"{path} missing @tool decorator")

    def test_calls_route_to_vendor(self):
        for path in self.TOOL_FILES:
            with open(path, encoding="utf-8") as f:
                source = f.read()
            self.assertIn("route_to_vendor", source, f"{path} missing route_to_vendor call")


@pytest.mark.unit
class TestDefaultConfigUpdate(unittest.TestCase):
    """Verify default_config.py has new vendor settings."""

    def test_new_vendor_categories(self):
        with open("tradingagents/default_config.py", encoding="utf-8") as f:
            source = f.read()

        for key in ["hk_stock_data", "futures_data", "forex_data", "sector_flow"]:
            self.assertIn(f'"{key}"', source, f"Config key {key} missing")

    def test_direct_source_settings(self):
        with open("tradingagents/default_config.py", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("direct_source_settings", source)


@pytest.mark.unit
class TestDirectSourcesDirectory(unittest.TestCase):
    """Verify all direct_sources modules exist and have correct structure."""

    REQUIRED_MODULES = [
        "__init__",
        "anti_scraping",
        "encoding_utils",
        "sina_stock",
        "tencent_hk",
        "eastmoney_sector",
        "xuangubao",
        "boc_forex",
        "sohu_history",
        "tencent_hk_history",
        "xueqiu_direct",
    ]

    def test_all_modules_exist(self):
        import os
        base = "tradingagents/dataflows/direct_sources"
        for mod in self.REQUIRED_MODULES:
            path = os.path.join(base, f"{mod}.py")
            self.assertTrue(os.path.exists(path), f"{path} does not exist")

    def test_init_has_docstring(self):
        with open("tradingagents/dataflows/direct_sources/__init__.py", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('"""', content)


@pytest.mark.unit
class TestAkshareFallback(unittest.TestCase):
    """Verify fallback integrations in akshare_data.py and akshare_news.py."""

    def test_sohu_fallback_in_akshare_data(self):
        with open("tradingagents/dataflows/akshare_data.py", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("sohu_get_hist_data", source)
        self.assertIn("sohu_direct", source)

    def test_xuangubao_fallback_in_akshare_news(self):
        with open("tradingagents/dataflows/akshare_news.py", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("xuangubao", source.lower())
        self.assertIn("选股宝", source)

    def test_agent_utils_imports(self):
        with open("tradingagents/agents/utils/agent_utils.py", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("get_futures_data", source)
        self.assertIn("get_forex_data", source)
        self.assertIn("get_sector_flow", source)
        self.assertIn("get_hk_stock_data", source)

    def test_trading_graph_registers_new_tools(self):
        with open("tradingagents/graph/trading_graph.py", encoding="utf-8") as f:
            source = f.read()
        for tool_name in ["get_futures_data", "get_forex_data", "get_sector_flow", "get_hk_stock_data"]:
            self.assertIn(tool_name, source, f"{tool_name} not in trading_graph.py")
