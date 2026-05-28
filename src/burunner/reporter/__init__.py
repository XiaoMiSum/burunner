"""测试报告（控制台 + Allure）。"""

from burunner.reporter.base import BaseReporter
from burunner.reporter.console import ConsoleReporter, print_case_line, print_summary
from burunner.reporter.allure_reporter import AllureReporter
from burunner.reporter.registry import (
    REPORTER_REGISTRY,
    create_reporter,
    register_reporter,
)

# 注册内置报告器
register_reporter("allure", AllureReporter)
register_reporter("console", ConsoleReporter)

__all__ = [
    "BaseReporter",
    "AllureReporter",
    "ConsoleReporter",
    "REPORTER_REGISTRY",
    "register_reporter",
    "create_reporter",
    "print_case_line",
    "print_summary",
]
