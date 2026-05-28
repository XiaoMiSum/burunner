"""创建并清理 browser-use 的 BrowserSession。

不同 browser-use 版本对 BrowserSession 的入口签名略有差异，这里做了
兼容性 import 与 kwargs 适配，调用失败时给出明确报错。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger("burunner.browser")


# ---------------------------------------------------------------------------
# 浏览器驱动协议（I/O 抽象层，便于测试时 Mock）
# ---------------------------------------------------------------------------

# browser-use 支持的浏览器 channel（均为 Chromium 内核）
SUPPORTED_BROWSER_CHANNELS = (
    "chromium",
    "chrome", "chrome-beta", "chrome-dev", "chrome-canary",
    "msedge", "msedge-beta", "msedge-dev", "msedge-canary",
)


@runtime_checkable
class BrowserDriver(Protocol):
    """浏览器驱动协议，定义创建和关闭会话的能力。"""

    async def create_session(
        self,
        *,
        headless: bool = True,
        user_data_dir: str | None = None,
        keep_alive: bool = False,
        channel: str | None = None,
        **extra: Any,
    ) -> Any:
        """创建并启动一个浏览器会话实例。"""
        ...

    async def close_session(self, session: Any) -> None:
        """关闭浏览器会话。"""
        ...


class PlaywrightDriver:
    """基于 Playwright（browser-use）的默认浏览器驱动实现。"""

    async def create_session(
        self,
        *,
        headless: bool = True,
        user_data_dir: str | None = None,
        keep_alive: bool = False,
        channel: str | None = None,
        **extra: Any,
    ) -> Any:
        """使用 browser-use 的 BrowserSession 创建会话。"""
        SessionCls = _import_session_class()
        ProfileCls = _import_profile_class()

        init_kwargs: dict[str, Any] = {}
        if ProfileCls is not None:
            profile_kwargs: dict[str, Any] = {
                "headless": headless,
                "user_data_dir": user_data_dir,
                "keep_alive": keep_alive,
            }
            # 设置浏览器 channel（需要 browser-use >= 0.12.6）
            if channel:
                profile_kwargs["channel"] = channel
            try:
                profile = ProfileCls(**profile_kwargs)
                init_kwargs["browser_profile"] = profile
            except TypeError:
                # 旧版本签名兼容：不支持 channel/keep_alive
                try:
                    profile = ProfileCls(headless=headless)
                    init_kwargs["browser_profile"] = profile
                except TypeError:
                    init_kwargs.update(headless=headless)
        else:
            # 直接传给 Session
            init_kwargs.update(headless=headless)
            if user_data_dir:
                init_kwargs["user_data_dir"] = user_data_dir

        init_kwargs.update(extra)

        try:
            session = SessionCls(**init_kwargs)
        except TypeError as e:
            # 兜底: 仅以 headless 创建
            logger.debug("BrowserSession 完整签名失败 (%s)，回退最小参数", e)
            session = SessionCls(headless=headless)

        start = getattr(session, "start", None)
        if callable(start):
            result = start()
            if asyncio.iscoroutine(result):
                await result
        return session

    async def close_session(self, session: Any) -> None:
        """关闭浏览器会话，依次尝试 stop/close/kill。"""
        if session is None:
            return
        for name in ("stop", "close", "kill"):
            fn = getattr(session, name, None)
            if callable(fn):
                try:
                    result = fn()
                    if asyncio.iscoroutine(result):
                        await result
                    return
                except Exception as e:  # noqa: BLE001
                    logger.debug("BrowserSession.%s 失败: %s", name, e)
                    continue


def _import_session_class() -> Any:
    try:
        from browser_use import BrowserSession  # type: ignore
        return BrowserSession
    except ImportError:
        pass
    try:
        from browser_use.browser import BrowserSession  # type: ignore
        return BrowserSession
    except ImportError:
        pass
    try:
        from browser_use.browser.session import BrowserSession  # type: ignore
        return BrowserSession
    except ImportError as e:
        raise RuntimeError(
            "无法在 browser-use 中找到 BrowserSession 类，请检查 browser-use 版本"
        ) from e


def _import_profile_class() -> Any:
    """BrowserProfile 用于配置 headless/viewport 等，0.12+ 版本提供。"""
    try:
        from browser_use import BrowserProfile  # type: ignore
        return BrowserProfile
    except ImportError:
        pass
    try:
        from browser_use.browser import BrowserProfile  # type: ignore
        return BrowserProfile
    except ImportError:
        return None


# 默认全局驱动实例（保持向后兼容）
_default_driver = PlaywrightDriver()


async def create_session(
    *,
    headless: bool = True,
    user_data_dir: str | None = None,
    keep_alive: bool = False,
    channel: str | None = None,
    driver: BrowserDriver | None = None,
    **extra: Any,
) -> Any:
    """异步创建并启动一个 BrowserSession 实例。

    Args:
        headless: 是否无头模式运行。
        user_data_dir: 用户数据目录路径。
        keep_alive: 是否保持浏览器存活。
        channel: 浏览器 channel（chromium/chrome/msedge 等）。
        driver: 可选的浏览器驱动实现，默认使用 PlaywrightDriver。
        **extra: 额外的 BrowserSession 参数。
    """
    _driver = driver or _default_driver
    return await _driver.create_session(
        headless=headless,
        user_data_dir=user_data_dir,
        keep_alive=keep_alive,
        channel=channel,
        **extra,
    )


async def close_session(session: Any, *, driver: BrowserDriver | None = None) -> None:
    """关闭浏览器会话。

    Args:
        session: 要关闭的浏览器会话实例。
        driver: 可选的浏览器驱动实现，默认使用 PlaywrightDriver。
    """
    _driver = driver or _default_driver
    await _driver.close_session(session)


async def inject_cookies(session: Any, cookies: list[dict[str, Any]]) -> None:
    """向浏览器上下文注入预设 cookies。

    尝试通过 session 获取 Playwright BrowserContext 并调用 add_cookies。
    兼容 browser-use 不同版本的 session 内部结构。
    """
    if not cookies:
        return

    context = None

    # 尝试多种路径获取 browser context
    # 方式1: session.context (直接暴露)
    context = getattr(session, "context", None)

    # 方式2: session.browser_context
    if context is None:
        context = getattr(session, "browser_context", None)

    # 方式3: session.browser -> context
    if context is None:
        browser = getattr(session, "browser", None)
        if browser is not None:
            contexts = getattr(browser, "contexts", None)
            if contexts and len(contexts) > 0:
                context = contexts[0]

    if context is None:
        logger.warning("无法获取 BrowserContext，跳过 cookie 注入")
        return

    add_cookies_fn = getattr(context, "add_cookies", None)
    if not callable(add_cookies_fn):
        logger.warning("BrowserContext 不支持 add_cookies 方法，跳过 cookie 注入")
        return

    try:
        result = add_cookies_fn(cookies)
        if asyncio.iscoroutine(result):
            await result
        logger.info("成功注入 %d 个预设 cookies", len(cookies))
    except Exception as e:  # noqa: BLE001
        logger.warning("Cookie 注入失败: %s", e)
