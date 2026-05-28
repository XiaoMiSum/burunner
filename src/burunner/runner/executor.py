"""单个测试用例的执行器：调用 browser-use Agent 跑自然语言任务。"""

from __future__ import annotations

import json
import logging
import re
import time
import traceback
from typing import Any

from burunner.browser.session import close_session, create_session, inject_cookies
from burunner.config import RunnerConfig
from burunner.exceptions import (
    BrowserError,
    BurunnerError,
    ConfigurationError,
    LLMError,
    TransientError,
)
from burunner.parser.models import TestCase
from burunner.runner.result import CaseResult, CaseStatus
from burunner.utils.screenshot import capture_failure_screenshot
from burunner.utils.tokens import usage_from_history

logger = logging.getLogger("burunner.executor")


def _import_agent_class() -> Any:
    try:
        from browser_use import Agent  # type: ignore
        return Agent
    except ImportError as e:
        raise RuntimeError(
            "无法导入 browser_use.Agent，请检查 browser-use 是否安装且版本 >= 0.12.0"
        ) from e


_JSON_VERDICT_RE = re.compile(
    r"\{[^{}]*?\"success\"\s*:\s*(true|false)[^{}]*?\}", re.IGNORECASE
)


def _parse_verdict(text: str | None) -> tuple[bool | None, str | None]:
    """从 Agent 最终输出中解析 {"success":..., "reason":...}。

    返回 (success, reason)；解析失败时 success=None 表示需要回退到 history.is_successful()。
    """
    if not text:
        return None, None
    # 中文关键词兜底
    lower = text.strip()
    m = _JSON_VERDICT_RE.search(lower)
    if m:
        try:
            payload = json.loads(m.group(0))
            success = bool(payload.get("success"))
            reason = payload.get("reason")
            return success, str(reason) if reason is not None else None
        except (json.JSONDecodeError, AttributeError):
            pass
    if "测试失败" in text or "失败" in text and "成功" not in text:
        return False, text.strip()[:300]
    if "测试成功" in text:
        return True, None
    return None, None


def _final_result_text(history: Any) -> str | None:
    if history is None:
        return None
    fn = getattr(history, "final_result", None)
    if callable(fn):
        try:
            v = fn()
            if isinstance(v, str):
                return v
            if v is not None:
                return str(v)
        except Exception:  # noqa: BLE001
            pass
    # fallback: 取 history 最后一项的输出
    inner = getattr(history, "history", None)
    if isinstance(inner, list) and inner:
        last = inner[-1]
        for attr in ("output", "result", "model_output"):
            v = getattr(last, attr, None)
            if isinstance(v, str):
                return v
            if v is not None:
                return str(v)
    return None


def _is_successful(history: Any) -> bool | None:
    if history is None:
        return None
    fn = getattr(history, "is_successful", None)
    if callable(fn):
        try:
            v = fn()
            if isinstance(v, bool):
                return v
        except Exception:  # noqa: BLE001
            pass
    return None


async def run_case(case: TestCase, cfg: RunnerConfig, llm: Any) -> CaseResult:
    """执行单个 TestCase，返回 CaseResult（绝不抛异常出来）。"""
    Agent = _import_agent_class()

    cfg.ensure_dirs()
    started = time.time() * 1000
    t0 = time.perf_counter()

    session = None
    history = None
    final_text: str | None = None
    error_message: str | None = None
    error_trace: str | None = None

    try:
        session = await create_session(
            headless=cfg.headless,
            user_data_dir=cfg.user_data_dir,
            keep_alive=cfg.keep_browser_open,
            channel=cfg.browser_channel,
        )

        # 注入预设 cookies（用例级 + 全局级合并）
        all_cookies = list(case.cookies)
        if cfg.cookies:
            # 全局 cookies 在用例 cookies 之后，同名cookie用例优先
            seen_keys = {(c.name, c.domain) for c in all_cookies}
            for gc in cfg.cookies:
                if (gc.name, gc.domain) not in seen_keys:
                    all_cookies.append(gc)
        if all_cookies:
            pw_cookies = [c.to_playwright_cookie() for c in all_cookies]
            await inject_cookies(session, pw_cookies)

        task_prompt = case.build_task_prompt()

        agent_kwargs: dict[str, Any] = {
            "task": task_prompt,
            "llm": llm,
            "browser_session": session,
            "use_vision": cfg.use_vision,
            "generate_gif": False,
        }
        try:
            agent = Agent(**agent_kwargs)
        except TypeError:
            # 旧版本可能用 browser= 而非 browser_session=
            agent_kwargs.pop("browser_session", None)
            agent_kwargs["browser"] = session
            agent = Agent(**agent_kwargs)

        run_kwargs: dict[str, Any] = {}
        if cfg.max_steps:
            run_kwargs["max_steps"] = cfg.max_steps
        try:
            history = await agent.run(**run_kwargs)
        except TypeError:
            # 旧 API 不接受 max_steps kwarg
            history = await agent.run()

        final_text = _final_result_text(history)

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

    # 结果判定
    status = CaseStatus.ERROR if error_message else CaseStatus.PASSED
    if status != CaseStatus.ERROR:
        verdict_success, verdict_reason = _parse_verdict(final_text)
        is_succ = _is_successful(history)
        if verdict_success is False:
            status = CaseStatus.FAILED
            error_message = verdict_reason or "Agent 报告测试失败"
        elif is_succ is False:
            status = CaseStatus.FAILED
            error_message = verdict_reason or "Agent history.is_successful() 返回 False"
        elif verdict_success is True or is_succ is True:
            status = CaseStatus.PASSED
        else:
            # 双重未知 -> 视为失败，避免误报通过
            status = CaseStatus.FAILED
            error_message = "无法从 Agent 输出中判定测试结论"

    tokens = usage_from_history(history)

    # 失败/异常时尝试截图
    screenshot_path = None
    if status in (CaseStatus.FAILED, CaseStatus.ERROR):
        try:
            screenshot_path = await capture_failure_screenshot(
                session=session,
                history=history,
                output_dir=cfg.screenshots_dir or (
                    cfg.results_dir / "screenshots"),
                case_name=case.name,
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("截图失败: %s", e)

    # 关闭 session
    if not cfg.keep_browser_open:
        try:
            await close_session(session)
        except Exception as e:  # noqa: BLE001
            logger.debug("关闭 BrowserSession 失败: %s", e)

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
