"""Runner 核心模块单元测试 (orchestrator, executor)。"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from burunner.config import RunnerConfig
from burunner.parser.models import TestCase, TestStep, CookieItem
from burunner.runner.orchestrator import (
    _maybe_await,
    _should_retry,
    _run_with_timeout,
    _run_with_retry,
)
from burunner.runner.result import CaseResult, CaseStatus
from burunner.utils.metrics import TokenUsage


class TestMaybeAwait:
    """_maybe_await 函数测试。"""

    @pytest.mark.asyncio
    async def test_await_coroutine(self):
        """等待协程。"""
        async def async_func():
            return "result"

        await _maybe_await(async_func())
        # 不应该抛出异常

    @pytest.mark.asyncio
    async def test_skip_non_coroutine(self):
        """跳过非协程。"""
        await _maybe_await("not a coroutine")
        # 不应该抛出异常


class TestShouldRetry:
    """_should_retry 函数测试。"""

    def test_retry_incomplete(self):
        """INCOMPLETE 状态应该重试。"""
        case = TestCase(name="测试")
        result = CaseResult(
            case=case, status=CaseStatus.INCOMPLETE, elapsed=1.0)
        assert _should_retry(result) is True

    def test_retry_error(self):
        """ERROR 状态应该重试。"""
        case = TestCase(name="测试")
        result = CaseResult(case=case, status=CaseStatus.ERROR, elapsed=1.0)
        assert _should_retry(result) is True

    def test_no_retry_failed(self):
        """FAILED 状态不应该重试。"""
        case = TestCase(name="测试")
        result = CaseResult(case=case, status=CaseStatus.FAILED, elapsed=1.0)
        assert _should_retry(result) is False

    def test_no_retry_passed(self):
        """PASSED 状态不应该重试。"""
        case = TestCase(name="测试")
        result = CaseResult(case=case, status=CaseStatus.PASSED, elapsed=1.0)
        assert _should_retry(result) is False

    def test_no_retry_skipped(self):
        """SKIPPED 状态不应该重试。"""
        case = TestCase(name="测试")
        result = CaseResult(case=case, status=CaseStatus.SKIPPED, elapsed=1.0)
        assert _should_retry(result) is False


class TestRunWithTimeout:
    """_run_with_timeout 函数测试。"""

    @pytest.mark.asyncio
    async def test_run_without_timeout(self):
        """不带超时运行。"""
        case = TestCase(name="测试用例")
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        mock_result = CaseResult(
            case=case, status=CaseStatus.PASSED, elapsed=1.0)

        with patch("burunner.runner.orchestrator.run_case", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            result = await _run_with_timeout(case, cfg, mock_llm, timeout=0)

            assert result == mock_result
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        """带超时运行,在超时前完成。"""
        case = TestCase(name="测试用例")
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        mock_result = CaseResult(
            case=case, status=CaseStatus.PASSED, elapsed=1.0)

        with patch("burunner.runner.orchestrator.run_case", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            result = await _run_with_timeout(case, cfg, mock_llm, timeout=30)

            assert result == mock_result

    @pytest.mark.asyncio
    async def test_run_with_timeout_expired(self):
        """带超时运行,超时后返回错误。"""
        case = TestCase(name="测试用例")
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        async def slow_run(*args, **kwargs):
            await asyncio.sleep(10)  # 模拟长时间运行

        with patch("burunner.runner.orchestrator.run_case", side_effect=slow_run):
            result = await _run_with_timeout(case, cfg, mock_llm, timeout=1)

            assert result.status == CaseStatus.ERROR
            assert "超时" in result.error_message
            assert result.elapsed == 1.0


class TestRunWithRetry:
    """_run_with_retry 函数测试。"""

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self):
        """成功时不重试。"""
        case = TestCase(name="测试用例")
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        mock_result = CaseResult(
            case=case, status=CaseStatus.PASSED, elapsed=1.0)

        with patch("burunner.runner.orchestrator._run_with_timeout", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            result = await _run_with_retry(
                case, cfg, mock_llm,
                timeout=30,
                retry_count=3,
                retry_delay=1.0,
            )

            assert result == mock_result
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_error(self):
        """ERROR 状态时重试。"""
        case = TestCase(name="测试用例")
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        error_result = CaseResult(
            case=case, status=CaseStatus.ERROR, elapsed=1.0)
        success_result = CaseResult(
            case=case, status=CaseStatus.PASSED, elapsed=1.0)

        call_count = 0

        async def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return error_result
            return success_result

        with patch("burunner.runner.orchestrator._run_with_timeout", side_effect=mock_run):
            result = await _run_with_retry(
                case, cfg, mock_llm,
                timeout=30,
                retry_count=3,
                retry_delay=0.01,  # 快速测试
            )

            assert result.status == CaseStatus.PASSED
            assert call_count == 2  # 第一次失败,第二次成功

    @pytest.mark.asyncio
    async def test_no_retry_on_failed(self):
        """FAILED 状态不重试。"""
        case = TestCase(name="测试用例")
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        failed_result = CaseResult(
            case=case, status=CaseStatus.FAILED, elapsed=1.0)

        with patch("burunner.runner.orchestrator._run_with_timeout", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = failed_result
            result = await _run_with_retry(
                case, cfg, mock_llm,
                timeout=30,
                retry_count=3,
                retry_delay=0.01,
            )

            assert result.status == CaseStatus.FAILED
            mock_run.assert_called_once()  # 只调用一次

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """重试次数用尽。"""
        case = TestCase(name="测试用例")
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        error_result = CaseResult(
            case=case, status=CaseStatus.ERROR, elapsed=1.0)

        with patch("burunner.runner.orchestrator._run_with_timeout", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = error_result
            result = await _run_with_retry(
                case, cfg, mock_llm,
                timeout=30,
                retry_count=2,
                retry_delay=0.01,
            )

            assert result.status == CaseStatus.ERROR
            assert mock_run.call_count == 3  # 初始 + 2 次重试
