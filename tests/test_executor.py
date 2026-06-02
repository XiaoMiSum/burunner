"""执行器模块单元测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from burunner.config import RunnerConfig
from burunner.exceptions import BrowserError, ConfigurationError, LLMError
from burunner.parser.models import TestCase, TestStep
from burunner.runner.executor import _resolve_max_steps, run_case
from burunner.runner.result import CaseResult, CaseStatus


class TestResolveMaxSteps:
    """_resolve_max_steps 函数测试。"""

    def test_use_config_value(self):
        """使用配置中的 max_steps。"""
        case = TestCase(name="测试", steps=[TestStep(text="步骤1")])
        cfg = RunnerConfig()
        cfg.max_steps = 50

        result = _resolve_max_steps(case, cfg)
        assert result == 50

    def test_dynamic_calculation_minimum(self):
        """动态计算,最少 20。"""
        case = TestCase(name="测试", steps=[])
        cfg = RunnerConfig()
        cfg.max_steps = 0

        result = _resolve_max_steps(case, cfg)
        assert result == 20  # 最少 20

    def test_dynamic_calculation_with_steps(self):
        """动态计算,根据步骤数计算。"""
        case = TestCase(name="测试", steps=[
            TestStep(text="步骤1"),
            TestStep(text="步骤2"),
            TestStep(text="步骤3"),
        ])
        cfg = RunnerConfig()
        cfg.max_steps = 0

        result = _resolve_max_steps(case, cfg)
        assert result == 60  # 3 * 20

    def test_dynamic_calculation_exceeds_minimum(self):
        """动态计算超过最小值。"""
        case = TestCase(name="测试", steps=[
                        TestStep(text=f"步骤{i}") for i in range(5)])
        cfg = RunnerConfig()
        cfg.max_steps = 0

        result = _resolve_max_steps(case, cfg)
        assert result == 100  # 5 * 20


class TestRunCase:
    """run_case 函数测试。"""

    @pytest.mark.asyncio
    async def test_run_case_success(self):
        """成功执行用例。"""
        case = TestCase(name="测试用例", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        # Mock history
        mock_history = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            with patch("burunner.runner.executor.execute_agent", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_history

                with patch("burunner.runner.executor.HistoryParser") as mock_parser_cls:
                    mock_parser = MagicMock()
                    mock_parser.final_result_text = '{"success": true}'
                    mock_parser.is_done = True
                    mock_parser.total_steps = 5
                    mock_parser_cls.return_value = mock_parser

                    with patch("burunner.runner.executor.VerdictJudge") as mock_judge_cls:
                        mock_judge = MagicMock()
                        mock_judge.judge.return_value = (
                            CaseStatus.PASSED, None)
                        mock_judge_cls.return_value = mock_judge

                        result = await run_case(case, cfg, mock_llm)

                        assert result.status == CaseStatus.PASSED
                        assert result.case == case
                        mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_case_failed(self):
        """用例执行失败。"""
        case = TestCase(name="失败用例", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        mock_history = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            with patch("burunner.runner.executor.execute_agent", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_history

                with patch("burunner.runner.executor.HistoryParser") as mock_parser_cls:
                    mock_parser = MagicMock()
                    mock_parser.final_result_text = '{"success": false, "reason": "断言失败"}'
                    mock_parser.is_done = True
                    mock_parser.total_steps = 5
                    mock_parser_cls.return_value = mock_parser

                    with patch("burunner.runner.executor.VerdictJudge") as mock_judge_cls:
                        mock_judge = MagicMock()
                        mock_judge.judge.return_value = (
                            CaseStatus.FAILED, "断言失败")
                        mock_judge_cls.return_value = mock_judge

                        with patch("burunner.runner.executor.capture_failure_screenshot", new_callable=AsyncMock) as mock_screenshot:
                            mock_screenshot.return_value = None

                            result = await run_case(case, cfg, mock_llm)

                            assert result.status == CaseStatus.FAILED
                            assert "断言失败" in result.error_message

    @pytest.mark.asyncio
    async def test_run_case_configuration_error(self):
        """配置错误。"""
        case = TestCase(name="配置错误用例", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                side_effect=ConfigurationError("配置错误")
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            result = await run_case(case, cfg, mock_llm)

            assert result.status == CaseStatus.ERROR
            assert "配置错误" in result.error_message

    @pytest.mark.asyncio
    async def test_run_case_browser_error(self):
        """浏览器错误。"""
        case = TestCase(name="浏览器错误用例", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                side_effect=BrowserError("浏览器启动失败")
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            result = await run_case(case, cfg, mock_llm)

            assert result.status == CaseStatus.ERROR
            assert "浏览器异常" in result.error_message

    @pytest.mark.asyncio
    async def test_run_case_llm_error(self):
        """LLM 错误。"""
        case = TestCase(name="LLM 错误用例", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                side_effect=LLMError("API 调用失败")
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            result = await run_case(case, cfg, mock_llm)

            assert result.status == CaseStatus.ERROR
            assert "LLM 调用异常" in result.error_message  # 修复: 使用完整消息

    @pytest.mark.asyncio
    async def test_run_case_screenshot_on_failure(self):
        """失败时截图。"""
        case = TestCase(name="截图用例", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        mock_history = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            with patch("burunner.runner.executor.execute_agent", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_history

                with patch("burunner.runner.executor.HistoryParser") as mock_parser_cls:
                    mock_parser = MagicMock()
                    mock_parser.final_result_text = '{"success": false}'
                    mock_parser.is_done = True
                    mock_parser.total_steps = 5
                    mock_parser_cls.return_value = mock_parser

                    with patch("burunner.runner.executor.VerdictJudge") as mock_judge_cls:
                        mock_judge = MagicMock()
                        mock_judge.judge.return_value = (
                            CaseStatus.FAILED, "失败")
                        mock_judge_cls.return_value = mock_judge

                        with patch("burunner.runner.executor.capture_failure_screenshot", new_callable=AsyncMock) as mock_screenshot:
                            from pathlib import Path
                            mock_screenshot.return_value = Path(
                                "/tmp/screenshot.png")

                            result = await run_case(case, cfg, mock_llm)

                            assert result.status == CaseStatus.FAILED
                            mock_screenshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_case_no_screenshot_on_success(self):
        """成功时不截图。"""
        case = TestCase(name="成功用例", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()

        mock_history = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            with patch("burunner.runner.executor.execute_agent", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_history

                with patch("burunner.runner.executor.HistoryParser") as mock_parser_cls:
                    mock_parser = MagicMock()
                    mock_parser.final_result_text = '{"success": true}'
                    mock_parser.is_done = True
                    mock_parser.total_steps = 5
                    mock_parser_cls.return_value = mock_parser

                    with patch("burunner.runner.executor.VerdictJudge") as mock_judge_cls:
                        mock_judge = MagicMock()
                        mock_judge.judge.return_value = (
                            CaseStatus.PASSED, None)
                        mock_judge_cls.return_value = mock_judge

                        with patch("burunner.runner.executor.capture_failure_screenshot", new_callable=AsyncMock) as mock_screenshot:
                            result = await run_case(case, cfg, mock_llm)

                            assert result.status == CaseStatus.PASSED
                            mock_screenshot.assert_not_called()
