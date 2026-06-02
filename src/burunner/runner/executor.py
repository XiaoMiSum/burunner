"""用例执行器 - 协调各组件完成单个用例的执行。"""

from __future__ import annotations

import logging
import time
import traceback
from typing import Any

from burunner.config import RunnerConfig
from burunner.exceptions import (
    BrowserError,
    BurunnerError,
    ConfigurationError,
    LLMError,
    TransientError,
)
from burunner.parser.models import TestCase
from burunner.runner.agent_runner import execute_agent
from burunner.runner.history_parser import HistoryParser
from burunner.runner.result import CaseResult, CaseStatus
from burunner.runner.session_manager import managed_session
from burunner.runner.verdicts import VerdictJudge
from burunner.utils.screenshot import capture_failure_screenshot

logger = logging.getLogger("burunner.executor")


def _resolve_max_steps(case: TestCase, cfg: RunnerConfig) -> int:
    """动态计算 Agent 最大步骤数。

    优先级：配置值（来自环境变量/YAML/CLI） > 动态计算
    当 cfg.max_steps > 0 时，表示用户显式设置了值（通过 BURUNNER_MAX_STEPS 环境变量、YAML config 或 CLI --max-steps），直接使用。
    当 cfg.max_steps == 0 时，动态计算：len(case.steps) * 20（最少 20）。
    """
    if cfg.max_steps > 0:
        return cfg.max_steps
    return max(len(case.steps) * 20, 20)


async def run_case(case: TestCase, cfg: RunnerConfig, llm: Any) -> CaseResult:
    """执行单个 TestCase，返回 CaseResult（绝不抛异常出来）。"""
    cfg.ensure_dirs()
    started = time.time() * 1000
    t0 = time.perf_counter()
    max_steps = _resolve_max_steps(case, cfg)
    logger.info("用例 %s 使用 max_steps=%d", case.name, max_steps)

    history = None
    session = None
    error_message: str | None = None
    error_trace: str | None = None
    screenshot_path = None

    try:
        async with managed_session(case, cfg) as session:
            history = await execute_agent(case, cfg, llm, session, max_steps)

            # 解析 history
            parsed = HistoryParser(history)

            # 结果判定
            judge = VerdictJudge()
            status, verdict_error = judge.judge(
                parsed=parsed,
                max_steps=max_steps,
                error_occurred=False,
                error_message=None,
            )

            # 失败/异常/未完成时尝试截图（必须在 session 存活时）
            if status in (CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.INCOMPLETE):
                try:
                    screenshot_path = await capture_failure_screenshot(
                        session=session,
                        history=history,
                        output_dir=cfg.screenshots_dir or (
                            cfg.results_dir / "screenshots"),
                        case_name=case.name,
                    )
                except Exception:  # noqa: BLE001
                    logger.debug("截图失败", exc_info=True)

            error_message = verdict_error

    except ConfigurationError as exc:
        error_message = f"配置错误: {exc}"
        error_trace = traceback.format_exc()
        logger.warning("用例 %s 配置异常: %s", case.name, error_message)

    except BrowserError as exc:
        error_message = f"浏览器异常: {exc}"
        error_trace = traceback.format_exc()
        logger.warning("用例 %s 浏览器异常: %s", case.name, error_message)

    except LLMError as exc:
        error_message = f"LLM 调用异常: {exc}"
        error_trace = traceback.format_exc()
        logger.warning("用例 %s LLM 异常: %s", case.name, error_message)

    except TransientError as exc:
        error_message = f"临时错误: {exc}"
        error_trace = traceback.format_exc()
        logger.warning("用例 %s 临时异常: %s", case.name, error_message)

    except BurunnerError as exc:
        error_message = f"执行异常: {exc}"
        error_trace = traceback.format_exc()
        logger.warning("用例 %s 执行异常: %s", case.name, error_message)

    except Exception as exc:  # noqa: BLE001 - 兜底捕获未预期异常
        error_message = f"{type(exc).__name__}: {exc}"
        error_trace = traceback.format_exc()
        logger.warning("用例 %s 执行异常: %s", case.name, error_message)

    elapsed = time.perf_counter() - t0
    stopped = time.time() * 1000

    # 异常路径中 parsed/status 可能未创建
    if "parsed" not in locals():
        parsed = HistoryParser(history)
        judge = VerdictJudge()
        status, verdict_error = judge.judge(
            parsed=parsed,
            max_steps=max_steps,
            error_occurred=True,
            error_message=error_message,
        )
        # 异常路径下尝试从 history 截图（session 已关闭，只能用 history）
        if screenshot_path is None and status in (
            CaseStatus.FAILED, CaseStatus.ERROR, CaseStatus.INCOMPLETE
        ):
            try:
                screenshot_path = await capture_failure_screenshot(
                    session=None,
                    history=history,
                    output_dir=cfg.screenshots_dir or (
                        cfg.results_dir / "screenshots"),
                    case_name=case.name,
                )
            except Exception:  # noqa: BLE001
                logger.debug("截图失败", exc_info=True)

    tokens = parsed.token_usage
    final_text = parsed.final_result_text

    return CaseResult(
        case=case,
        status=status,
        elapsed=elapsed,
        tokens=tokens,
        final_result=final_text,
        error_message=error_message,
        error_trace=error_trace,
        screenshot_path=screenshot_path,
        started_at=started,
        stopped_at=stopped,
    )
