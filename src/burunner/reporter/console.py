"""控制台输出 —— 单用例耗时/Tokens 与全局总计。"""

from __future__ import annotations

import sys

from burunner.reporter.base import BaseReporter
from burunner.runner.result import CaseResult, CaseStatus, SuiteResult

_SEP = "=" * 65


def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _status_label(status: CaseStatus) -> str:
    label = status.label()
    if status == CaseStatus.PASSED:
        return _color(f"[{label}]", "32")    # green
    if status == CaseStatus.FAILED:
        return _color(f"[{label}]", "31")    # red
    if status == CaseStatus.ERROR:
        return _color(f"[{label}]", "33")    # yellow
    if status == CaseStatus.INCOMPLETE:
        return _color(f"[{label}]", "35")    # magenta
    return f"[{label}]"


def print_case_line(result: CaseResult) -> None:
    """单个用例完成时打印一行结果。"""
    parts = [
        _status_label(result.status),
        f"{result.case.name:<32}",
        f"elapsed={result.elapsed:.2f}s",
        (
            f"tokens(in/out/total)={result.tokens.input_tokens}"
            f"/{result.tokens.output_tokens}/{result.tokens.total}"
        ),
    ]
    if result.screenshot_path:
        parts.append(f"screenshot={result.screenshot_path}")
    if result.error_message and result.status != CaseStatus.PASSED:
        parts.append(f"reason={result.error_message[:80]}")
    print("  ".join(parts), flush=True)


def print_summary(suite: SuiteResult, *, results_dir: str | None = None) -> None:
    """全部完成后打印总计。"""
    print(_SEP, flush=True)
    print(
        f"Total: {suite.total}  "
        f"Passed: {_color(str(suite.passed), '32')}  "
        f"Failed: {_color(str(suite.failed), '31')}  "
        f"Error:  {_color(str(suite.error), '33')}  "
        f"Incomplete: {_color(str(suite.incomplete), '35')}",
        flush=True,
    )
    print(f"Total elapsed: {suite.total_elapsed:.2f}s", flush=True)
    tokens = suite.total_tokens
    print(
        f"Total tokens: in={tokens.input_tokens}  "
        f"out={tokens.output_tokens}  total={tokens.total}",
        flush=True,
    )
    if results_dir:
        print(
            f"Allure results: {results_dir}  "
            f"(run: allure serve {results_dir})",
            flush=True,
        )
    print(_SEP, flush=True)


class ConsoleReporter(BaseReporter):
    """基于控制台的报告器，实时打印用例结果与最终汇总。"""

    def __init__(self, *, results_dir: str | None = None) -> None:
        self._results_dir = results_dir
        self._results: list[CaseResult] = []

    def start_suite(self, suite_name: str) -> None:  # noqa: D102
        pass

    def write_case(self, result: CaseResult, **kwargs) -> None:  # noqa: D102
        self._results.append(result)
        print_case_line(result)

    def finish(self) -> None:  # noqa: D102
        suite = SuiteResult(case_results=self._results)
        print_summary(suite, results_dir=self._results_dir)
