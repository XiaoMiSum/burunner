"""报告器工厂 —— 支持内置 + 外部插件发现。"""
from __future__ import annotations

import importlib.metadata
import logging

from burunner.reporter.base import BaseReporter

logger = logging.getLogger(__name__)

_BUILTIN_REPORTERS: dict[str, str] = {
    "allure": "burunner.reporter.allure_reporter:AllureReporter",
    "console": "burunner.reporter.console:ConsoleReporter",
}


def _discover_reporters() -> dict[str, type[BaseReporter]]:
    """发现所有可用的报告器（内置 + 外部插件）。"""
    registry: dict[str, type[BaseReporter]] = {}

    # 内置报告器（延迟导入避免循环）
    from burunner.reporter.allure_reporter import AllureReporter
    from burunner.reporter.console import ConsoleReporter

    registry["allure"] = AllureReporter
    registry["console"] = ConsoleReporter

    # 外部插件（通过 entry_points）
    try:
        eps = importlib.metadata.entry_points(group="burunner.reporters")
        for ep in eps:
            try:
                cls = ep.load()
                if isinstance(cls, type) and issubclass(cls, BaseReporter):
                    registry[ep.name] = cls
                else:
                    logger.warning(
                        "Reporter plugin %r is not a BaseReporter subclass", ep.name)
            except Exception as exc:
                logger.warning(
                    "Failed to load reporter plugin %r: %s", ep.name, exc)
    except Exception:
        pass

    return registry


def create_reporter(name: str, *args, **kwargs) -> BaseReporter | None:
    """根据名称创建报告器实例。"""
    reporters = _discover_reporters()
    cls = reporters.get(name)
    if cls is None:
        logger.warning("Unknown reporter: %r. Available: %s",
                       name, list(reporters.keys()))
        return None
    return cls(*args, **kwargs)
