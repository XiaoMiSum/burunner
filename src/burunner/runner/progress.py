"""实时进度跟踪与显示。

提供类 tqdm 风格的进度条，支持：
- 当前用例名称和序号
- 已完成/总数和百分比
- 预估剩余时间 (ETA)
- 并行执行时各线程状态
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any

from burunner.parser.models import TestCase
from burunner.runner.result import CaseResult, CaseStatus


def _is_tty() -> bool:
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def _color(text: str, code: str) -> str:
    if not _is_tty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _format_duration(seconds: float) -> str:
    """格式化时长为 mm:ss 或 hh:mm:ss。"""
    if seconds < 0:
        return "--:--"
    seconds = int(seconds)
    if seconds < 3600:
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class _RunningCase:
    """正在执行的用例信息。"""
    case: TestCase
    index: int
    start_time: float = field(default_factory=time.perf_counter)


class ProgressTracker:
    """测试执行进度跟踪器。

    通过回调方式集成到 orchestrator 中，在终端实时显示进度信息。
    """

    def __init__(
        self,
        total: int,
        parallel: int = 1,
        *,
        enabled: bool = True,
    ) -> None:
        self._total = total
        self._parallel = parallel
        self._enabled = enabled and _is_tty()

        self._completed = 0
        self._passed = 0
        self._failed = 0
        self._errors = 0
        self._incomplete = 0

        self._running: dict[str, _RunningCase] = {}  # case.name -> info

        self._start_time = time.perf_counter()
        self._completed_times: list[float] = []  # 各用例耗时列表

        # 上次渲染的行数（用于清除）
        self._last_lines = 0

    def on_case_start(self, case: TestCase, index: int) -> None:
        """用例开始执行时调用。"""
        if not self._enabled:
            return
        self._running[case.name] = _RunningCase(case=case, index=index)
        self._render()

    def on_case_complete(self, result: CaseResult) -> None:
        """用例完成时调用。"""
        if not self._enabled:
            return
        self._running.pop(result.case.name, None)
        self._completed += 1
        self._completed_times.append(result.elapsed)
        if result.status == CaseStatus.PASSED:
            self._passed += 1
        elif result.status == CaseStatus.FAILED:
            self._failed += 1
        elif result.status == CaseStatus.ERROR:
            self._errors += 1
        elif result.status == CaseStatus.INCOMPLETE:
            self._incomplete += 1
        self._render()

    def finish(self) -> None:
        """所有用例执行完毕，清除进度显示。"""
        if not self._enabled:
            return
        self._clear_lines()
        sys.stderr.flush()

    def _render(self) -> None:
        """渲染进度信息到终端。"""
        self._clear_lines()

        lines: list[str] = []

        # 1) 进度条
        bar_line = self._build_progress_bar()
        lines.append(bar_line)

        # 2) 状态统计行
        elapsed = time.perf_counter() - self._start_time
        eta = self._estimate_eta()
        stats = (
            f"  {_color('PASS', '32')}:{self._passed}  "
            f"{_color('FAIL', '31')}:{self._failed}  "
            f"{_color('ERR', '33')}:{self._errors}  "
            f"{_color('INC', '35')}:{self._incomplete}  "
            f"Elapsed: {_format_duration(elapsed)}  "
            f"ETA: {_format_duration(eta)}"
        )
        lines.append(stats)

        # 3) 正在运行的用例（并行时显示多个）
        if self._running:
            running_header = (
                f"  Running ({len(self._running)}"
                f"{'/' + str(self._parallel) if self._parallel > 1 else ''}):"
            )
            lines.append(running_header)
            for name, info in list(self._running.items())[:self._parallel]:
                case_elapsed = time.perf_counter() - info.start_time
                indicator = _color("●", "36")  # cyan dot
                case_label = (
                    f"    {indicator} [{info.index}/{self._total}] "
                    f"{name[:40]}{'...' if len(name) > 40 else ''}"
                    f"  ({_format_duration(case_elapsed)})"
                )
                lines.append(case_label)

        # 输出到 stderr（不影响 stdout 的日志输出）
        output = "\n".join(lines)
        sys.stderr.write(output)
        sys.stderr.flush()

        self._last_lines = len(lines)

    def _build_progress_bar(self) -> str:
        """构建进度条字符串。"""
        try:
            term_width = _get_terminal_width()
        except Exception:
            term_width = 80

        pct = (self._completed / self._total * 100) if self._total > 0 else 0
        pct_str = f" {pct:5.1f}% "
        counter_str = f" {self._completed}/{self._total} "

        # 计算进度条可用宽度
        fixed_len = len(pct_str) + len(counter_str) + 4  # [] + spaces
        bar_width = max(10, term_width - fixed_len)

        filled = int(bar_width * self._completed /
                     self._total) if self._total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)

        if _is_tty():
            # 绿色已完成部分
            bar_colored = f"\033[32m{'█' * filled}\033[0m{'░' * (bar_width - filled)}"
            return f"{pct_str}[{bar_colored}]{counter_str}"
        return f"{pct_str}[{bar}]{counter_str}"

    def _estimate_eta(self) -> float:
        """估算剩余时间。"""
        if not self._completed_times:
            return -1.0
        remaining = self._total - self._completed
        if remaining <= 0:
            return 0.0
        avg_time = sum(self._completed_times) / len(self._completed_times)
        # 考虑并行度
        effective_parallel = min(self._parallel, remaining)
        eta = (avg_time * remaining) / max(effective_parallel, 1)
        return eta

    def _clear_lines(self) -> None:
        """清除上次渲染的行。"""
        if self._last_lines > 0 and _is_tty():
            # 移动光标到上方并清除各行
            sys.stderr.write(f"\033[{self._last_lines}A")
            for _ in range(self._last_lines):
                sys.stderr.write("\033[2K\n")
            sys.stderr.write(f"\033[{self._last_lines}A")
            sys.stderr.flush()
            self._last_lines = 0


def _get_terminal_width() -> int:
    """获取终端宽度。"""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except Exception:
        return 80
