"""报告器工厂单元测试 - 测试插件化发现机制。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from burunner.reporter.factory import create_reporter, _discover_reporters
from burunner.reporter.base import BaseReporter


class TestDiscoverReporters:
    """_discover_reporters 函数测试。"""

    def test_discover_builtin_reporters(self):
        """测试发现内置报告器。"""
        reporters = _discover_reporters()
        assert "allure" in reporters
        assert "console" in reporters

    def test_allure_reporter_is_class(self):
        """测试 AllureReporter 是类。"""
        reporters = _discover_reporters()
        from burunner.reporter.allure_reporter import AllureReporter
        assert reporters["allure"] is AllureReporter

    def test_console_reporter_is_class(self):
        """测试 ConsoleReporter 是类。"""
        reporters = _discover_reporters()
        from burunner.reporter.console import ConsoleReporter
        assert reporters["console"] is ConsoleReporter

    @patch("importlib.metadata.entry_points")
    def test_discover_external_plugins(self, mock_entry_points):
        """测试发现外部插件。"""
        # Mock 外部插件
        class CustomReporter(BaseReporter):
            def __init__(self, output_dir=None):
                self.output_dir = output_dir

            def write_case(self, result, **kwargs):
                pass

        mock_ep = MagicMock()
        mock_ep.name = "custom"
        mock_ep.load.return_value = CustomReporter
        mock_entry_points.return_value = [mock_ep]

        reporters = _discover_reporters()
        assert "custom" in reporters
        assert reporters["custom"] is CustomReporter

    @patch("importlib.metadata.entry_points")
    def test_invalid_plugin_skipped(self, mock_entry_points):
        """测试无效插件被跳过。"""
        mock_ep = MagicMock()
        mock_ep.name = "invalid"
        mock_ep.load.return_value = "not_a_class"  # 不是类
        mock_entry_points.return_value = [mock_ep]

        reporters = _discover_reporters()
        assert "invalid" not in reporters

    @patch("importlib.metadata.entry_points")
    def test_plugin_load_failure(self, mock_entry_points):
        """测试插件加载失败时被跳过。"""
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("Failed to load")
        mock_entry_points.return_value = [mock_ep]

        # 不应该抛出异常
        reporters = _discover_reporters()
        assert "broken" not in reporters


class TestCreateReporter:
    """create_reporter 函数测试。"""

    def test_create_allure_reporter(self, tmp_path):
        """测试创建 AllureReporter。"""
        reporter = create_reporter("allure", tmp_path)
        assert reporter is not None
        from burunner.reporter.allure_reporter import AllureReporter
        assert isinstance(reporter, AllureReporter)

    def test_create_console_reporter(self):
        """测试创建 ConsoleReporter。"""
        reporter = create_reporter("console")
        assert reporter is not None
        from burunner.reporter.console import ConsoleReporter
        assert isinstance(reporter, ConsoleReporter)

    def test_create_unknown_reporter(self):
        """测试创建未知报告器返回 None。"""
        reporter = create_reporter("unknown")
        assert reporter is None

    def test_create_with_kwargs(self, tmp_path):
        """测试创建时传递关键字参数。"""
        reporter = create_reporter("allure", results_dir=tmp_path)
        assert reporter is not None
        assert reporter.results_dir == tmp_path
