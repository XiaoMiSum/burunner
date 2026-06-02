"""Agent 执行封装 - 处理 browser-use Agent 的初始化和运行。"""

from __future__ import annotations

import logging
from typing import Any

from burunner.config import RunnerConfig
from burunner.parser.models import TestCase

logger = logging.getLogger("burunner.agent_runner")


def _import_agent_class() -> Any:
    """延迟导入 browser-use Agent 类。"""
    try:
        from browser_use import Agent  # type: ignore

        return Agent
    except ImportError as e:
        raise RuntimeError(
            "无法导入 browser_use.Agent，请检查 browser-use 是否安装且版本 >= 0.12.0"
        ) from e


def _build_agent_kwargs(
    cfg: RunnerConfig, llm: Any, session: Any, task_prompt: str
) -> dict[str, Any]:
    """构建 Agent 初始化参数，处理版本兼容性。"""
    return {
        "task": task_prompt,
        "llm": llm,
        "browser_session": session,
        "use_vision": cfg.use_vision,
        "generate_gif": False,
    }


async def execute_agent(
    case: TestCase,
    cfg: RunnerConfig,
    llm: Any,
    session: Any,
    max_steps: int,
) -> Any:
    """初始化并运行 browser-use Agent，返回 history 对象。

    处理不同 browser-use 版本的兼容性。
    """
    Agent = _import_agent_class()

    task_prompt = case.build_task_prompt()
    agent_kwargs = _build_agent_kwargs(cfg, llm, session, task_prompt)

    try:
        agent = Agent(**agent_kwargs)
    except TypeError:
        # 旧版本可能用 browser= 而非 browser_session=
        agent_kwargs.pop("browser_session", None)
        agent_kwargs["browser"] = session
        agent = Agent(**agent_kwargs)

    # 运行（兼容有无 max_steps 参数的版本）
    run_kwargs: dict[str, Any] = {"max_steps": max_steps}
    try:
        history = await agent.run(**run_kwargs)
    except TypeError:
        # 旧 API 不接受 max_steps kwarg
        history = await agent.run()

    return history
