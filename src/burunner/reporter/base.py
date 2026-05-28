"""报告器抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from burunner.runner.result import CaseResult, SuiteResult


class BaseReporter(ABC):
    """报告器抽象基类，所有报告格式需实现此接口。"""

    @abstractmethod
    def start_suite(self, suite_name: str) -> None:
        """测试套件开始时调用。"""

    @abstractmethod
    def write_case(self, result: "CaseResult", **kwargs) -> None:
        """写入单个用例结果。"""

    @abstractmethod
    def finish(self) -> None:
        """测试套件结束时调用，执行清理或生成最终报告。"""

    def write_environment(self, env: dict[str, str]) -> None:
        """写入环境信息，默认无操作。子类可按需覆写。"""
