"""Agent Runner 模块单元测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from burunner.config import RunnerConfig
from burunner.parser.models import TestCase, TestStep
from burunner.runner.agent_runner import (
    _build_agent_kwargs,
    _import_agent_class,
    execute_agent,
)


class TestImportAgentClass:
    """_import_agent_class 函数测试。"""

    def test_import_success(self):
        """成功导入 Agent 类。"""
        # 由于实际环境中可能没有 browser-use,我们直接测试函数逻辑
        # 如果 browser-use 已安装,_import_agent_class 应该返回 Agent 类
        # 这里我们只测试函数可以被调用而不抛异常
        try:
            agent_class = _import_agent_class()
            # 如果导入成功,Agent 类应该不为 None
            assert agent_class is not None
        except RuntimeError:
            # 如果 browser-use 未安装,应该抛 RuntimeError
            pytest.skip("browser-use 未安装")

    def test_import_failure(self):
        """导入失败时抛出 RuntimeError。"""
        import sys
        # 临时移除 browser_use 模块
        original_module = sys.modules.get("browser_use")
        try:
            sys.modules["browser_use"] = None

            with pytest.raises(RuntimeError) as exc_info:
                _import_agent_class()

            assert "browser_use.Agent" in str(exc_info.value)
        finally:
            # 恢复原模块
            if original_module is not None:
                sys.modules["browser_use"] = original_module


class TestBuildAgentKwargs:
    """_build_agent_kwargs 函数测试。"""

    def test_build_kwargs(self):
        """构建 Agent 参数。"""
        cfg = RunnerConfig()
        cfg.use_vision = True
        mock_llm = MagicMock()
        mock_session = MagicMock()
        task_prompt = "测试任务"

        kwargs = _build_agent_kwargs(cfg, mock_llm, mock_session, task_prompt)

        assert kwargs["task"] == task_prompt
        assert kwargs["llm"] == mock_llm
        assert kwargs["browser_session"] == mock_session
        assert kwargs["use_vision"] is True
        assert kwargs["generate_gif"] is False

    def test_build_kwargs_without_vision(self):
        """不使用 vision。"""
        cfg = RunnerConfig()
        cfg.use_vision = False
        mock_llm = MagicMock()
        mock_session = MagicMock()
        task_prompt = "测试任务"

        kwargs = _build_agent_kwargs(cfg, mock_llm, mock_session, task_prompt)

        assert kwargs["use_vision"] is False


class TestExecuteAgent:
    """execute_agent 函数测试。"""

    @pytest.mark.asyncio
    async def test_execute_agent_success(self):
        """成功执行 Agent。"""
        case = TestCase(name="测试", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()
        mock_session = MagicMock()

        mock_agent_class = MagicMock()
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_agent_class.return_value = mock_agent

        with patch("burunner.runner.agent_runner._import_agent_class", return_value=mock_agent_class):
            history = await execute_agent(case, cfg, mock_llm, mock_session, max_steps=50)

            mock_agent_class.assert_called_once()
            mock_agent.run.assert_called_once_with(max_steps=50)
            assert history is not None

    @pytest.mark.asyncio
    async def test_execute_agent_fallback_browser_param(self):
        """旧版本使用 browser 参数。"""
        case = TestCase(name="测试", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()
        mock_session = MagicMock()

        mock_agent_class = MagicMock()
        mock_agent = MagicMock()

        # 使用 AsyncMock 并设置 side_effect 来模拟 TypeError
        async def mock_run_with_fallback(**kwargs):
            return MagicMock()

        mock_agent.run = mock_run_with_fallback

        # 第一次调用失败 (TypeError),第二次成功
        call_count = [0]

        def create_agent(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TypeError("不支持 browser_session")
            return mock_agent

        mock_agent_class.side_effect = create_agent

        with patch("burunner.runner.agent_runner._import_agent_class", return_value=mock_agent_class):
            history = await execute_agent(case, cfg, mock_llm, mock_session, max_steps=50)

            # 应该调用两次 (第一次失败,第二次成功)
            assert call_count[0] == 2
            assert history is not None

    @pytest.mark.asyncio
    async def test_execute_agent_fallback_no_max_steps(self):
        """旧版本不接受 max_steps 参数。"""
        case = TestCase(name="测试", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()
        mock_llm = MagicMock()
        mock_session = MagicMock()

        mock_agent_class = MagicMock()
        mock_agent = MagicMock()

        # 第一次 run 失败 (TypeError),第二次成功
        async def run_with_fallback(**kwargs):
            if "max_steps" in kwargs:
                raise TypeError("不接受 max_steps")
            return MagicMock()

        mock_agent.run = run_with_fallback
        mock_agent_class.return_value = mock_agent

        with patch("burunner.runner.agent_runner._import_agent_class", return_value=mock_agent_class):
            history = await execute_agent(case, cfg, mock_llm, mock_session, max_steps=50)

            assert history is not None

    @pytest.mark.asyncio
    async def test_execute_agent_with_task_prompt(self):
        """使用正确的任务提示。"""
        case = TestCase(name="测试用例", steps=[
            TestStep(text="打开百度"),
            TestStep(text="搜索测试"),
        ])
        cfg = RunnerConfig()
        mock_llm = MagicMock()
        mock_session = MagicMock()

        mock_agent_class = MagicMock()
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_agent_class.return_value = mock_agent

        with patch("burunner.runner.agent_runner._import_agent_class", return_value=mock_agent_class):
            await execute_agent(case, cfg, mock_llm, mock_session, max_steps=50)

            # 验证调用了 Agent,并且传入了正确的参数
            call_kwargs = mock_agent_class.call_args[1]
            assert "task" in call_kwargs
            assert "llm" in call_kwargs
            assert "browser_session" in call_kwargs
