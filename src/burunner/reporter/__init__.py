"""测试报告（控制台 + Allure）。"""

from burunner.reporter.base import BaseReporter
from burunner.reporter.console import ConsoleReporter, print_case_line, print_summary
from burunner.reporter.allure_reporter import AllureReporter
from burunner.reporter.factory import create_reporter, _discover_reporters

# 向后兼容：保留旧注册表导出（已废弃）
from burunner.reporter.registry import (
    REPORTER_REGISTRY,
    register_reporter,
)

# 注册内置报告器（向后兼容）
register_reporter("allure", AllureReporter)
register_reporter("console", ConsoleReporter)

__all__ = [
    "BaseReporter",
    "AllureReporter",
    "ConsoleReporter",
    "create_reporter",
    "_discover_reporters",
    # 以下已废弃，保留向后兼容
    "REPORTER_REGISTRY",
    "register_reporter",
    "print_case_line",
    "print_summary",
]
