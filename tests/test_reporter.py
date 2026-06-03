"""报告器模块单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from burunner.reporter.base import BaseReporter
from burunner.reporter.registry import (
    REPORTER_REGISTRY,
    register_reporter,
    create_reporter as registry_create_reporter,
)
from burunner.reporter.factory import create_reporter, _discover_reporters
from burunner.parser.models import TestCase, TestStep
from burunner.runner.result import CaseResult, CaseStatus, SuiteResult
from burunner.utils.metrics import TokenUsage


class TestBaseReporter:
    """BaseReporter 抽象类测试。"""

    def test_abstract_methods(self):
        """BaseReporter 不能被直接实例化。"""
        with pytest.raises(TypeError):
            BaseReporter()

    def test_concrete_implementation(self):
        """可以创建具体实现。"""

        class MockReporter(BaseReporter):
            def start_suite(self, suite_name: str) -> None:
                pass

            def write_case(self, result: CaseResult, **kwargs) -> None:
                pass

            def finish(self) -> None:
                pass

        reporter = MockReporter()
        assert isinstance(reporter, BaseReporter)

    def test_write_environment_default(self):
        """write_environment 默认无操作。"""

        class MockReporter(BaseReporter):
            def start_suite(self, suite_name: str) -> None:
                pass

            def write_case(self, result: CaseResult, **kwargs) -> None:
                pass

            def finish(self) -> None:
                pass

        reporter = MockReporter()
        # 不应该抛出异常
        reporter.write_environment({"ENV": "test"})


class TestReporterRegistry:
    """报告器注册表测试。"""

    def setup_method(self):
        """每个测试前清空注册表。"""
        REPORTER_REGISTRY.clear()

    def test_register_reporter(self):
        """注册报告器。"""

        class MockReporter(BaseReporter):
            def start_suite(self, suite_name: str) -> None:
                pass

            def write_case(self, result: CaseResult, **kwargs) -> None:
                pass

            def finish(self) -> None:
                pass

        register_reporter("mock", MockReporter)
        assert "mock" in REPORTER_REGISTRY
        assert REPORTER_REGISTRY["mock"] == MockReporter

    def test_create_reporter(self):
        """创建报告器实例。"""

        class MockReporter(BaseReporter):
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def start_suite(self, suite_name: str) -> None:
                pass

            def write_case(self, result: CaseResult, **kwargs) -> None:
                pass

            def finish(self) -> None:
                pass

        register_reporter("mock", MockReporter)
        reporter = registry_create_reporter("mock", results_dir="./test")

        assert isinstance(reporter, MockReporter)
        assert reporter.kwargs == {"results_dir": "./test"}

    def test_create_reporter_unknown_name(self):
        """创建未知报告器抛出异常。"""
        with pytest.raises(ValueError) as exc_info:
            registry_create_reporter("unknown")

        assert "未知的报告格式: unknown" in str(exc_info.value)
        assert "可用:" in str(exc_info.value)

    def test_registry_multiple_reporters(self):
        """注册多个报告器。"""

        class Reporter1(BaseReporter):
            def start_suite(self, suite_name: str) -> None:
                pass

            def write_case(self, result: CaseResult, **kwargs) -> None:
                pass

            def finish(self) -> None:
                pass

        class Reporter2(BaseReporter):
            def start_suite(self, suite_name: str) -> None:
                pass

            def write_case(self, result: CaseResult, **kwargs) -> None:
                pass

            def finish(self) -> None:
                pass

        register_reporter("r1", Reporter1)
        register_reporter("r2", Reporter2)

        assert len(REPORTER_REGISTRY) == 2
        assert "r1" in REPORTER_REGISTRY
        assert "r2" in REPORTER_REGISTRY

    def test_registry_overwrite(self):
        """注册同名报告器会覆盖。"""

        class Reporter1(BaseReporter):
            def start_suite(self, suite_name: str) -> None:
                pass

            def write_case(self, result: CaseResult, **kwargs) -> None:
                pass

            def finish(self) -> None:
                pass

        class Reporter2(BaseReporter):
            def start_suite(self, suite_name: str) -> None:
                pass

            def write_case(self, result: CaseResult, **kwargs) -> None:
                pass

            def finish(self) -> None:
                pass

        register_reporter("test", Reporter1)
        register_reporter("test", Reporter2)

        assert REPORTER_REGISTRY["test"] == Reporter2


class TestAllureReporterIntegration:
    """AllureReporter 集成测试 (如果 allure-commons 可用)。"""

    def test_allure_import(self):
        """测试 allure-commons 是否可用。"""
        try:
            from allure_commons.lifecycle import AllureLifecycle
            assert AllureLifecycle is not None
        except ImportError:
            pytest.skip("allure-commons 未安装")

    def test_allure_reporter_create(self, tmp_path):
        """创建 AllureReporter 实例。"""
        try:
            from burunner.reporter.allure_reporter import AllureReporter
        except ImportError:
            pytest.skip("allure-commons 未安装")

        reporter = AllureReporter(results_dir=tmp_path / "allure-results")
        assert reporter.results_dir.exists()

    def test_allure_reporter_lifecycle(self, tmp_path):
        """AllureReporter 生命周期方法。"""
        try:
            from burunner.reporter.allure_reporter import AllureReporter
        except ImportError:
            pytest.skip("allure-commons 未安装")

        reporter = AllureReporter(results_dir=tmp_path / "allure-results")

        # start_suite 和 finish 应该是空操作
        reporter.start_suite("测试套件")
        reporter.finish()

        # 不应该抛出异常
        assert True


class TestReporterFactory:
    """报告器工厂（factory.py）测试。"""

    def test_create_reporter_allure(self, tmp_path):
        """create_reporter('allure') 返回 AllureReporter 实例。"""
        try:
            from burunner.reporter.allure_reporter import AllureReporter
        except ImportError:
            pytest.skip("allure-commons 未安装")

        reporter = create_reporter(
            "allure", results_dir=tmp_path / "allure-results")
        assert reporter is not None
        assert isinstance(reporter, AllureReporter)

    def test_create_reporter_console(self):
        """create_reporter('console') 返回 ConsoleReporter 实例。"""
        from burunner.reporter.console import ConsoleReporter

        reporter = create_reporter("console")
        assert reporter is not None
        assert isinstance(reporter, ConsoleReporter)

    def test_create_reporter_unknown_returns_none(self):
        """create_reporter('unknown') 返回 None。"""
        result = create_reporter("unknown")
        assert result is None

    def test_discover_reporters_contains_builtin(self):
        """_discover_reporters() 包含 'allure' 和 'console'。"""
        reporters = _discover_reporters()
        assert "allure" in reporters
        assert "console" in reporters

    def test_discover_reporters_values_are_subclasses(self):
        """_discover_reporters() 返回的值都是 BaseReporter 的子类。"""
        reporters = _discover_reporters()
        for name, cls in reporters.items():
            assert issubclass(
                cls, BaseReporter), f"{name} is not a BaseReporter subclass"
