"""测试结果数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from burunner.parser.models import TestCase
from burunner.utils.metrics import TokenUsage


class CaseStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"   # 框架层异常 / 浏览器异常 / Agent 抛错
    SKIPPED = "SKIPPED"
    INCOMPLETE = "INCOMPLETE"  # 执行未完成，超过最大步骤数

    def label(self) -> str:
        return {
            CaseStatus.PASSED: "PASS",
            CaseStatus.FAILED: "FAIL",
            CaseStatus.ERROR: "ERR ",
            CaseStatus.SKIPPED: "SKIP",
            CaseStatus.INCOMPLETE: "INC ",
        }[self]


@dataclass
class StepOutcome:
    """单个测试步骤的执行结果。"""

    step_index: int                     # 对应 TestCase.steps 的索引
    step_text: str                      # 步骤描述文本
    status: str                         # PASSED / FAILED / INCOMPLETE / UNKNOWN
    duration: float = 0.0               # 该步骤的总耗时（秒）
    started_at: float = 0.0             # 开始时间戳
    stopped_at: float = 0.0             # 结束时间戳
    iterations: int = 0                 # 该步骤占用的 Agent 迭代数
    errors: list[str] = field(default_factory=list)  # 该步骤期间的错误信息
    actions: list[str] = field(default_factory=list)  # 执行的动作名称列表
    url: str | None = None              # 该步骤结束时的页面 URL


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
    step_outcomes: list[StepOutcome] = field(
        default_factory=list)  # 每步执行结果，可选


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
    def incomplete(self) -> int:
        return sum(1 for r in self.case_results if r.status == CaseStatus.INCOMPLETE)

    @property
    def total_tokens(self) -> TokenUsage:
        agg = TokenUsage()
        for r in self.case_results:
            agg = agg + r.tokens
        return agg

    @property
    def is_success(self) -> bool:
        return self.failed == 0 and self.error == 0 and self.incomplete == 0
