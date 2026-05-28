"""轻量日志封装。"""

from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%H:%M:%S"
_INITIALIZED = False


def setup_logging(verbose: bool = False) -> None:
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

    # 降低 browser-use 自身的 INFO 噪音（除非 verbose）
    if not verbose:
        for noisy in ("browser_use", "playwright", "httpx", "openai"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"burunner.{name}")
