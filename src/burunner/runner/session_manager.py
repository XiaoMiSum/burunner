"""浏览器会话生命周期管理。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from burunner.browser.session import close_session, create_session, inject_cookies
from burunner.config import RunnerConfig
from burunner.parser.models import CookieItem, TestCase

logger = logging.getLogger("burunner.session_manager")


def _merge_cookies(case: TestCase, cfg: RunnerConfig) -> list[CookieItem]:
    """合并全局和用例级 cookies，用例同名 cookie 覆盖全局。"""
    all_cookies: list[CookieItem] = list(case.cookies)
    if cfg.cookies:
        seen_keys = {(c.name, c.domain) for c in all_cookies}
        for gc in cfg.cookies:
            if (gc.name, gc.domain) not in seen_keys:
                all_cookies.append(gc)
    return all_cookies


@asynccontextmanager
async def managed_session(
    case: TestCase, cfg: RunnerConfig
) -> AsyncGenerator[Any, None]:
    """创建并管理浏览器会话的生命周期。

    使用方式：
        async with managed_session(case, cfg) as session:
            # 使用 session ...
    # session 自动清理，即使发生异常也不泄露
    """
    session = None
    try:
        session = await create_session(
            headless=cfg.headless,
            user_data_dir=cfg.user_data_dir,
            keep_alive=cfg.keep_browser_open,
            channel=cfg.browser_channel,
        )

        # Cookie 注入
        cookies = _merge_cookies(case, cfg)
        if cookies:
            pw_cookies = [c.to_playwright_cookie() for c in cookies]
            await inject_cookies(session, pw_cookies)

        yield session
    finally:
        if session and not cfg.keep_browser_open:
            try:
                await close_session(session)
            except Exception as e:  # noqa: BLE001
                logger.warning("Session cleanup failed: %s", e)
