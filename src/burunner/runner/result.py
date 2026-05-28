"""测试结果数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from burunner.parser.models import TestCase
from burunner.utils.tokens import TokenUsage


class CaseStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"   # 框架层异常 / 浏览器异常 / Agent 抛错
    SKIPPED = "SKIPPED"

    def label(self) -> str:
        return {
            CaseStatus.PASSED: "PASS",
            CaseStatus.FAILED: "FAIL",
            CaseStatus.ERROR: "ERR ",
            CaseStatus.SKIPPED: "SKIP",
        }[self]


@dataclass
class CaseResult:
    case: TestCase
    status: CaseStatus
    elapsed: float = 0.0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    final_result: str | None = None       # Agent 的最终输出文本
    error_message: str | None = None
    error_trace: str | None = None
    screenshot_path: Path | None = None
    started_at: float = 0.0               # epoch ms
    stopped_at: float = 0.0               # epoch ms
    step_outcomes: list[dict] = field(default_factory=list)  # 每步 status/desc，可选


@dataclass
class SuiteResult:
    case_results: list[CaseResult] = field(default_factory=list)
    total_elapsed: float = 0.0

    @property
    def total(self) -> int:
        return len(self.case_results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.case_results if r.status == CaseStatus.PASSED)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.case_results if r.status == CaseStatus.FAILED)

    @property
    def error(self) -> int:
        return sum(1 for r in self.case_results if r.status == CaseStatus.ERROR)

    @property
    def total_tokens(self) -> TokenUsage:
        agg = TokenUsage()
        for r in self.case_results:
            agg = agg + r.tokens
        return agg

    @property
    def is_success(self) -> bool:
        return self.failed == 0 and self.error == 0
