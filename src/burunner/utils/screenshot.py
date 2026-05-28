"""失败截图 —— 与 browser-use use_vision 模式配合。

策略:
1. 优先从 BrowserSession 当前页面抓一帧 png 字节。
2. 若失败，则回退到 AgentHistoryList 中最后一帧 vision 截图 (base64)。
3. 仍失败时返回 None。
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("burunner.screenshot")


def _decode_b64(data: str) -> bytes | None:
    if not data:
        return None
    try:
        # 容忍带 data:image/png;base64, 前缀的形式
        if data.startswith("data:") and "," in data:
            data = data.split(",", 1)[1]
        return base64.b64decode(data, validate=False)
    except (binascii.Error, ValueError):
        return None


async def _from_session(session: Any) -> bytes | None:
    if session is None:
        return None
    method = getattr(session, "take_screenshot", None) or getattr(session, "screenshot", None)
    if method is None:
        return None
    try:
        result = method()
        if asyncio.iscoroutine(result):
            result = await result
    except Exception as e:  # noqa: BLE001
        logger.debug("session.take_screenshot 失败: %s", e)
        return None

    if isinstance(result, bytes):
        return result
    if isinstance(result, str):
        return _decode_b64(result)
    return None


def _from_history(history: Any) -> bytes | None:
    if history is None:
        return None
    # browser-use 历史中可能存放 base64 截图
    candidates: list[Any] = []
    fn = getattr(history, "screenshots", None)
    if callable(fn):
        try:
            candidates = fn() or []
        except Exception:  # noqa: BLE001
            candidates = []
    if not candidates:
        inner = getattr(history, "history", None)
        if isinstance(inner, list):
            for item in inner:
                state = getattr(item, "state", None) or item
                shot = getattr(state, "screenshot", None)
                if shot:
                    candidates.append(shot)
    for shot in reversed(candidates):
        if isinstance(shot, bytes):
            return shot
        if isinstance(shot, str):
            data = _decode_b64(shot)
            if data:
                return data
    return None


async def capture_failure_screenshot(
    *,
    session: Any,
    history: Any,
    output_dir: Path,
    case_name: str,
) -> Path | None:
    """抓一张失败现场截图，落盘并返回路径。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    png = await _from_session(session)
    if png is None:
        png = _from_history(history)
    if png is None:
        return None

    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in case_name)[:80]
    path = output_dir / f"{safe}-{int(time.time() * 1000)}.png"
    path.write_bytes(png)
    return path
