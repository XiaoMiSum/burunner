"""测试结果模块单元测试。"""

import pytest

from burunner.parser.models import TestCase, TestStep
from burunner.runner.result import CaseResult, CaseStatus, SuiteResult
from burunner.utils.metrics import TokenUsage


class TestCaseStatus:
    """CaseStatus 枚举测试。"""

    def test_status_values(self):
        assert CaseStatus.PASSED.value == "PASSED"
        assert CaseStatus.FAILED.value == "FAILED"
        assert CaseStatus.ERROR.value == "ERROR"
        assert CaseStatus.SKIPPED.value == "SKIPPED"
        assert CaseStatus.INCOMPLETE.value == "INCOMPLETE"

    def test_status_labels(self):
        assert CaseStatus.PASSED.label() == "PASS"
        assert CaseStatus.FAILED.label() == "FAIL"
        assert CaseStatus.ERROR.label() == "ERR "
        assert CaseStatus.SKIPPED.label() == "SKIP"
        assert CaseStatus.INCOMPLETE.label() == "INC "


class TestCaseResult:
    """CaseResult 数据类测试。"""

    def test_create_result_default(self):
        case = TestCase(name="测试用例", steps=[TestStep(text="步骤1")])
        result = CaseResult(case=case, status=CaseStatus.PASSED)

        assert result.case == case
        assert result.status == CaseStatus.PASSED
        assert result.elapsed == 0.0
        assert result.tokens == TokenUsage()
        assert result.final_result is None
        assert result.error_message is None
        assert result.error_trace is None
        assert result.screenshot_path is None
        assert result.started_at == 0.0
        assert result.stopped_at == 0.0
        assert result.step_outcomes == []

    def test_create_result_full(self):
        case = TestCase(name="测试用例")
        result = CaseResult(
            case=case,
            status=CaseStatus.FAILED,
            elapsed=5.5,
            final_result="操作失败",
            error_message="断言失败",
            error_trace="Traceback...",
        )

        assert result.status == CaseStatus.FAILED
        assert result.elapsed == 5.5
        assert result.final_result == "操作失败"
        assert result.error_message == "断言失败"
        assert result.error_trace == "Traceback..."


class TestSuiteResult:
    """SuiteResult 数据类测试。"""

    def test_create_result_default(self):
        result = SuiteResult()
        assert result.case_results == []
        assert result.total_elapsed == 0.0

    def test_total(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED),
                CaseResult(case=case, status=CaseStatus.FAILED),
            ]
        )
        assert results.total == 2

    def test_passed_count(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED),
                CaseResult(case=case, status=CaseStatus.FAILED),
                CaseResult(case=case, status=CaseStatus.PASSED),
            ]
        )
        assert results.passed == 2

    def test_failed_count(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.FAILED),
                CaseResult(case=case, status=CaseStatus.PASSED),
                CaseResult(case=case, status=CaseStatus.FAILED),
            ]
        )
        assert results.failed == 2

    def test_error_count(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.ERROR),
                CaseResult(case=case, status=CaseStatus.PASSED),
            ]
        )
        assert results.error == 1

    def test_incomplete_count(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.INCOMPLETE),
                CaseResult(case=case, status=CaseStatus.PASSED),
            ]
        )
        assert results.incomplete == 1

    def test_total_tokens(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(
                    case=case,
                    status=CaseStatus.PASSED,
                    tokens=TokenUsage(input_tokens=100, output_tokens=50),
                ),
                CaseResult(
                    case=case,
                    status=CaseStatus.PASSED,
                    tokens=TokenUsage(input_tokens=200, output_tokens=100),
                ),
            ]
        )
        total = results.total_tokens
        assert total.input_tokens == 300
        assert total.output_tokens == 150
        assert total.total == 450

    def test_is_success_all_passed(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED),
                CaseResult(case=case, status=CaseStatus.PASSED),
            ]
        )
        assert results.is_success is True

    def test_is_success_with_failed(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED),
                CaseResult(case=case, status=CaseStatus.FAILED),
            ]
        )
        assert results.is_success is False

    def test_is_success_with_error(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED),
                CaseResult(case=case, status=CaseStatus.ERROR),
            ]
        )
        assert results.is_success is False

    def test_is_success_with_incomplete(self):
        case = TestCase(name="测试")
        results = SuiteResult(
            case_results=[
                CaseResult(case=case, status=CaseStatus.PASSED),
                CaseResult(case=case, status=CaseStatus.INCOMPLETE),
            ]
        )
        assert results.is_success is False

    def test_is_success_empty(self):
        results = SuiteResult()
        assert results.is_success is True


class TestStepOutcome:
    """StepOutcome 数据类测试。"""

    def test_default_values(self):
        """默认值正确。"""
        from burunner.runner.result import StepOutcome

        outcome = StepOutcome(step_index=0, step_text="步骤1", status="PASSED")
        assert outcome.step_index == 0
        assert outcome.step_text == "步骤1"
        assert outcome.status == "PASSED"
        assert outcome.duration == 0.0
        assert outcome.started_at == 0.0
        assert outcome.stopped_at == 0.0
        assert outcome.iterations == 0
        assert outcome.errors == []
        assert outcome.actions == []
        assert outcome.url is None

    def test_all_fields(self):
        """全字段赋值正确。"""
        from burunner.runner.result import StepOutcome

        outcome = StepOutcome(
            step_index=2,
            step_text="输入用户名",
            status="FAILED",
            duration=3.5,
            started_at=1000.0,
            stopped_at=1003.5,
            iterations=5,
            errors=["元素未找到", "超时"],
            actions=["click", "type"],
            url="https://example.com/login",
        )
        assert outcome.step_index == 2
        assert outcome.step_text == "输入用户名"
        assert outcome.status == "FAILED"
        assert outcome.duration == 3.5
        assert outcome.started_at == 1000.0
        assert outcome.stopped_at == 1003.5
        assert outcome.iterations == 5
        assert outcome.errors == ["元素未找到", "超时"]
        assert outcome.actions == ["click", "type"]
        assert outcome.url == "https://example.com/login"

    def test_status_values(self):
        """status 可以是 PASSED/FAILED/INCOMPLETE/UNKNOWN。"""
        from burunner.runner.result import StepOutcome

        for status in ("PASSED", "FAILED", "INCOMPLETE", "UNKNOWN"):
            outcome = StepOutcome(step_index=0, step_text="x", status=status)
            assert outcome.status == status
