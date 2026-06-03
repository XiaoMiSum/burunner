"""报告器注册表 —— 支持通过名称创建报告器实例。

.. deprecated::
    此模块已废弃，请使用 burunner.reporter.factory 中的
    create_reporter() 和 _discover_reporters()。
    保留仅用于向后兼容。
"""

from __future__ import annotations

from burunner.reporter.base import BaseReporter

REPORTER_REGISTRY: dict[str, type[BaseReporter]] = {}


def register_reporter(name: str, cls: type[BaseReporter]) -> None:
    """注册报告器类型。"""
    REPORTER_REGISTRY[name] = cls


def create_reporter(name: str, **kwargs) -> BaseReporter:
    """根据名称创建报告器实例。"""
    cls = REPORTER_REGISTRY.get(name)
    if cls is None:
        available = list(REPORTER_REGISTRY.keys())
        raise ValueError(f"未知的报告格式: {name}，可用: {available}")
    return cls(**kwargs)
