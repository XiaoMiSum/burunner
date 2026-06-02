"""进度追踪模块单元测试。"""

import time
from unittest.mock import patch

from burunner.runner.progress import (
    ProgressTracker,
    _format_duration,
    _is_tty,
    _color,
)
from burunner.parser.models import TestCase, TestStep
from burunner.runner.result import CaseResult, CaseStatus


class TestFormatDuration:
    """_format_duration 函数测试。"""

    def test_zero_seconds(self):
        assert _format_duration(0) == "00:00"

    def test_seconds_only(self):
        assert _format_duration(45) == "00:45"

    def test_minutes_and_seconds(self):
        assert _format_duration(125) == "02:05"

    def test_hours_minutes_seconds(self):
        assert _format_duration(3661) == "01:01:01"

    def test_negative_seconds(self):
        assert _format_duration(-1) == "--:--"

    def test_exact_minute(self):
        assert _format_duration(120) == "02:00"

    def test_exact_hour(self):
        assert _format_duration(3600) == "01:00:00"


class TestIsTty:
    """_is_tty 函数测试。"""

    def test_returns_boolean(self):
        result = _is_tty()
        assert isinstance(result, bool)


class TestColor:
    """_color 函数测试。"""

    @patch("burunner.runner.progress._is_tty", return_value=True)
    def test_color_applied(self, mock_is_tty):
        result = _color("red text", "31")
        assert "\033[31m" in result
        assert "\033[0m" in result

    @patch("burunner.runner.progress._is_tty", return_value=False)
    def test_color_disabled(self, mock_is_tty):
        result = _color("text", "31")
        assert result == "text"


class TestProgressTracker:
    """ProgressTracker 类测试。"""

    def _make_tracker(self, total=5, enabled=True, **kwargs):
        """创建 tracker 并强制启用。"""
        tracker = ProgressTracker(total=total, enabled=enabled, **kwargs)
        # 强制启用,忽略 TTY 检查
        tracker._enabled = enabled
        return tracker

    def test_create_tracker(self):
        tracker = ProgressTracker(total=10, parallel=1, enabled=False)
        assert tracker._total == 10
        assert tracker._parallel == 1
        assert tracker._completed == 0

    @patch.object(ProgressTracker, '_render', return_value=None)
    def test_on_case_start(self, mock_render):
        tracker = self._make_tracker(total=5)
        case = TestCase(name="测试用例", steps=[TestStep(text="步骤")])
        tracker.on_case_start(case, 1)
        # 应该记录运行中的用例
        assert "测试用例" in tracker._running

    @patch.object(ProgressTracker, '_render', return_value=None)
    def test_on_case_complete_passed(self, mock_render):
        tracker = self._make_tracker(total=5)
        case = TestCase(name="测试用例")
        result = CaseResult(case=case, status=CaseStatus.PASSED, elapsed=1.5)

        tracker.on_case_start(case, 1)
        tracker.on_case_complete(result)

        assert tracker._completed == 1
        assert tracker._passed == 1
        assert "测试用例" not in tracker._running  # 应该移除

    @patch.object(ProgressTracker, '_render', return_value=None)
    def test_on_case_complete_failed(self, mock_render):
        tracker = self._make_tracker(total=5)
        case = TestCase(name="失败用例")
        result = CaseResult(case=case, status=CaseStatus.FAILED, elapsed=2.0)

        tracker.on_case_start(case, 1)
        tracker.on_case_complete(result)

        assert tracker._completed == 1
        assert tracker._failed == 1

    @patch.object(ProgressTracker, '_render', return_value=None)
    def test_on_case_complete_error(self, mock_render):
        tracker = self._make_tracker(total=5)
        case = TestCase(name="错误用例")
        result = CaseResult(case=case, status=CaseStatus.ERROR, elapsed=0.5)

        tracker.on_case_start(case, 1)
        tracker.on_case_complete(result)

        assert tracker._completed == 1
        assert tracker._errors == 1

    @patch.object(ProgressTracker, '_render', return_value=None)
    def test_on_case_complete_incomplete(self, mock_render):
        tracker = self._make_tracker(total=5)
        case = TestCase(name="未完成用例")
        result = CaseResult(
            case=case, status=CaseStatus.INCOMPLETE, elapsed=3.0)

        tracker.on_case_start(case, 1)
        tracker.on_case_complete(result)

        assert tracker._completed == 1
        assert tracker._incomplete == 1

    @patch.object(ProgressTracker, '_render', return_value=None)
    def test_multiple_cases(self, mock_render):
        tracker = self._make_tracker(total=3)

        for i in range(3):
            case = TestCase(name=f"用例{i+1}")
            status = [CaseStatus.PASSED,
                      CaseStatus.FAILED, CaseStatus.PASSED][i]
            result = CaseResult(case=case, status=status, elapsed=1.0)

            tracker.on_case_start(case, i + 1)
            tracker.on_case_complete(result)

        assert tracker._completed == 3
        assert tracker._passed == 2
        assert tracker._failed == 1

    @patch.object(ProgressTracker, '_render', return_value=None)
    def test_parallel_tracking(self, mock_render):
        """并行执行时跟踪多个运行中的用例。"""
        tracker = self._make_tracker(total=5, parallel=2)

        case1 = TestCase(name="用例1")
        case2 = TestCase(name="用例2")

        tracker.on_case_start(case1, 1)
        tracker.on_case_start(case2, 2)

        # 两个用例都应该在运行中
        assert "用例1" in tracker._running
        assert "用例2" in tracker._running
        assert len(tracker._running) == 2

    def test_finish(self):
        tracker = ProgressTracker(total=2, enabled=False)

        for i in range(2):
            case = TestCase(name=f"用例{i+1}")
            result = CaseResult(
                case=case, status=CaseStatus.PASSED, elapsed=1.0)
            tracker.on_case_start(case, i + 1)
            tracker.on_case_complete(result)

        # finish 不应该报错
        tracker.finish()

    def test_disabled_tracker(self):
        """禁用的 tracker 不应该更新状态。"""
        tracker = ProgressTracker(total=1, enabled=False)
        case = TestCase(name="测试")
        result = CaseResult(case=case, status=CaseStatus.PASSED, elapsed=1.0)

        tracker.on_case_start(case, 1)
        tracker.on_case_complete(result)
        tracker.finish()

        # 不应该有状态更新
        assert tracker._completed == 0
        assert tracker._passed == 0
        assert len(tracker._running) == 0
