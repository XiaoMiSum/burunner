"""轻量日志封装。"""

from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%H:%M:%S"
_INITIALIZED = False


def setup_logging(verbose: bool = False, browser_use_log: bool = False) -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))

    root = logging.getLogger("burunner")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False

    # 控制 browser-use 相关日志
    if not browser_use_log:
        # 彻底静默 browser-use 日志（默认行为）
        logging.getLogger("browser_use").setLevel(logging.CRITICAL)
        logging.getLogger("playwright").setLevel(logging.CRITICAL)
        logging.getLogger("httpx").setLevel(logging.CRITICAL)
    elif not verbose:
        # browser_use_log=True 但非 verbose：降为 WARNING
        logging.getLogger("browser_use").setLevel(logging.WARNING)
        logging.getLogger("playwright").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
    # verbose=True 且 browser_use_log=True 时：使用 DEBUG 级别（由顶层设置）

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"burunner.{name}")
