"""控制台报告器模块单元测试。"""

import sys
from io import StringIO
from unittest.mock import patch

from burunner.reporter.console import (
    ConsoleReporter,
    print_case_line,
    print_summary,
    _color,
    _status_label,
)
from burunner.parser.models import TestCase, TestStep
from burunner.runner.result import CaseResult, CaseStatus, SuiteResult
from burunner.utils.tokens import TokenUsage


class TestColor:
    """_color 函数测试。"""

    @patch.object(sys.stdout, "isatty", return_value=True)
    def test_color_applied(self, mock_isatty):
        result = _color("red text", "31")
        assert "\033[31m" in result
        assert "\033[0m" in result

    @patch.object(sys.stdout, "isatty", return_value=False)
    def test_color_disabled(self, mock_isatty):
        result = _color("text", "31")
        assert result == "text"


class TestStatusLabel:
    """_status_label 函数测试。"""

    @patch("burunner.reporter.console._color", side_effect=lambda text, code: text)
    def test_passed_label(self, mock_color):
        label = _status_label(CaseStatus.PASSED)
        assert "[PASS]" in label

    @patch("burunner.reporter.console._color", side_effect=lambda text, code: text)
    def test_failed_label(self, mock_color):
        label = _status_label(CaseStatus.FAILED)
        assert "[FAIL]" in label

    @patch("burunner.reporter.console._color", side_effect=lambda text, code: text)
    def test_error_label(self, mock_color):
        label = _status_label(CaseStatus.ERROR)
        assert "[ERR ]" in label

    @patch("burunner.reporter.console._color", side_effect=lambda text, code: text)
    def test_incomplete_label(self, mock_color):
        label = _status_label(CaseStatus.INCOMPLETE)
        assert "[INC ]" in label

    @patch("burunner.reporter.console._color", side_effect=lambda text, code: text)
    def test_skipped_label(self, mock_color):
        label = _status_label(CaseStatus.SKIPPED)
        assert "[SKIP]" in label


class TestPrintCaseLine:
    """print_case_line 函数测试。"""

    def test_print_passed(self, capsys):
        case = TestCase(name="测试用例", steps=[TestStep(text="步骤")])
        result = CaseResult(
            case=case,
            status=CaseStatus.PASSED,
            elapsed=1.5,
            tokens=TokenUsage(input_tokens=100, output_tokens=50),
        )
        print_case_line(result)
        captured = capsys.readouterr()
        assert "测试用例" in captured.out
        assert "elapsed=1.50s" in captured.out
        assert "tokens(in/out/total)=100/50/150" in captured.out

    def test_print_failed(self, capsys):
        case = TestCase(name="失败用例")
        result = CaseResult(
            case=case,
            status=CaseStatus.FAILED,
            elapsed=2.0,
            error_message="断言失败",
        )
        print_case_line(result)
        captured = capsys.readouterr()
        assert "失败用例" in captured.out
        assert "reason=断言失败" in captured.out

    def test_print_with_screenshot(self, capsys):
        from pathlib import Path

        case = TestCase(name="截图用例")
        result = CaseResult(
            case=case,
            status=CaseStatus.FAILED,
            elapsed=1.0,
            screenshot_path=Path("/tmp/screenshot.png"),
        )
        print_case_line(result)
        captured = capsys.readouterr()
        assert "screenshot=/tmp/screenshot.png" in captured.out

    def test_print_error_truncates_message(self, capsys):
        case = TestCase(name="长错误消息")
        long_msg = "错误" * 50  # 100 字符
        result = CaseResult(
            case=case,
            status=CaseStatus.ERROR,
            elapsed=0.5,
            error_message=long_msg,
        )
        print_case_line(result)
        captured = capsys.readouterr()
        # 错误消息应该被截断到 80 字符
        assert "reason=" in captured.out
        # 找到 reason= 后面的内容
        reason_start = captured.out.find("reason=") + 7
        reason_text = captured.out[reason_start:].strip()
        assert len(reason_text) <= 80


class TestPrintSummary:
    """print_summary 函数测试。"""

    def test_print_summary_all_passed(self, capsys):
        case = TestCase(name="测试")
        suite = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED, elapsed=1.0),
                CaseResult(case=case, status=CaseStatus.PASSED, elapsed=1.5),
            ],
            total_elapsed=2.5,
        )
        print_summary(suite)
        captured = capsys.readouterr()
        assert "Total: 2" in captured.out
        assert "Passed: 2" in captured.out
        assert "Failed: 0" in captured.out
        assert "Total elapsed: 2.50s" in captured.out

    def test_print_summary_with_failures(self, capsys):
        case = TestCase(name="测试")
        suite = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED, elapsed=1.0),
                CaseResult(case=case, status=CaseStatus.FAILED, elapsed=2.0),
                CaseResult(case=case, status=CaseStatus.ERROR, elapsed=0.5),
            ],
            total_elapsed=3.5,
        )
        print_summary(suite)
        captured = capsys.readouterr()
        assert "Total: 3" in captured.out
        assert "Passed: 1" in captured.out
        assert "Failed: 1" in captured.out
        assert "Error:  1" in captured.out

    def test_print_summary_with_tokens(self, capsys):
        case = TestCase(name="测试")
        suite = SuiteResult(
            case_results=[
                CaseResult(
                    case=case,
                    status=CaseStatus.PASSED,
                    tokens=TokenUsage(input_tokens=100, output_tokens=50),
                ),
            ]
        )
        print_summary(suite)
        captured = capsys.readouterr()
        assert "Total tokens: in=100" in captured.out
        assert "out=50" in captured.out
        assert "total=150" in captured.out

    def test_print_summary_with_results_dir(self, capsys):
        case = TestCase(name="测试")
        suite = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED),
            ]
        )
        print_summary(suite, results_dir="./allure-results")
        captured = capsys.readouterr()
        assert "Allure results: ./allure-results" in captured.out
        assert "allure serve" in captured.out


class TestConsoleReporter:
    """ConsoleReporter 类测试。"""

    def test_create_reporter(self):
        reporter = ConsoleReporter()
        assert reporter._results_dir is None
        assert reporter._results == []

    def test_create_reporter_with_results_dir(self):
        reporter = ConsoleReporter(results_dir="./test-results")
        assert reporter._results_dir == "./test-results"

    def test_start_suite(self, capsys):
        reporter = ConsoleReporter()
        reporter.start_suite("测试套件")
        # start_suite 不应该输出
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_write_case(self, capsys):
        reporter = ConsoleReporter()
        case = TestCase(name="测试用例")
        result = CaseResult(case=case, status=CaseStatus.PASSED, elapsed=1.0)

        reporter.write_case(result)

        assert len(reporter._results) == 1
        assert reporter._results[0] == result

        captured = capsys.readouterr()
        assert "测试用例" in captured.out

    def test_write_multiple_cases(self, capsys):
        reporter = ConsoleReporter()

        for i in range(3):
            case = TestCase(name=f"用例{i+1}")
            result = CaseResult(
                case=case, status=CaseStatus.PASSED, elapsed=1.0)
            reporter.write_case(result)

        assert len(reporter._results) == 3

    def test_finish(self, capsys):
        reporter = ConsoleReporter()

        case = TestCase(name="测试")
        result = CaseResult(case=case, status=CaseStatus.PASSED, elapsed=1.0)
        reporter.write_case(result)

        reporter.finish()

        captured = capsys.readouterr()
        assert "Total: 1" in captured.out
        assert "Passed: 1" in captured.out

    def test_finish_with_results_dir(self, capsys):
        reporter = ConsoleReporter(results_dir="./allure-results")

        case = TestCase(name="测试")
        result = CaseResult(case=case, status=CaseStatus.PASSED)
        reporter.write_case(result)

        reporter.finish()

        captured = capsys.readouterr()
        assert "Allure results: ./allure-results" in captured.out

    def test_full_workflow(self, capsys):
        """完整工作流测试。"""
        reporter = ConsoleReporter(results_dir="./results")

        # 开始套件
        reporter.start_suite("测试套件")

        # 写入多个用例
        cases = [
            ("用例1", CaseStatus.PASSED, 1.0),
            ("用例2", CaseStatus.FAILED, 2.0),
            ("用例3", CaseStatus.PASSED, 1.5),
        ]

        for name, status, elapsed in cases:
            case = TestCase(name=name)
            result = CaseResult(case=case, status=status, elapsed=elapsed)
            reporter.write_case(result)

        # 完成报告
        reporter.finish()

        captured = capsys.readouterr()
        assert "Total: 3" in captured.out
        assert "Passed: 2" in captured.out
        assert "Failed: 1" in captured.out
