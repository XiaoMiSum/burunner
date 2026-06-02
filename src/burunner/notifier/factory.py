"""通知器工厂 —— 插件化发现机制，支持内置通知器与外部 entry_points 插件。"""

from __future__ import annotations

import importlib.metadata
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseNotifier

from .base import BaseNotifier
from .wecom import WecomNotifier
from .feishu import FeishuNotifier
from .dingtalk import DingtalkNotifier

logger = logging.getLogger("burunner.notifier")


def _discover_notifiers() -> dict[str, type[BaseNotifier]]:
    """发现所有可用的通知器（内置 + 外部插件）"""
    registry: dict[str, type[BaseNotifier]] = {}

    # 1. 内置通知器
    registry["wecom"] = WecomNotifier
    registry["feishu"] = FeishuNotifier
    registry["dingtalk"] = DingtalkNotifier

    # 2. 外部插件（通过 entry_points group: burunner.notifiers）
    try:
        eps = importlib.metadata.entry_points(group="burunner.notifiers")
        for ep in eps:
            try:
                notifier_cls = ep.load()
                if isinstance(notifier_cls, type) and issubclass(notifier_cls, BaseNotifier):
                    registry[ep.name] = notifier_cls
                    logger.debug(f"Loaded external notifier plugin: {ep.name}")
                else:
                    logger.warning(
                        f"Notifier plugin '{ep.name}' is not a subclass of BaseNotifier, skipped"
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to load notifier plugin '{ep.name}': {e}")
    except Exception as e:
        logger.debug(f"No external notifier plugins found: {e}")

    return registry


def create_notifier(channel: str | None, webhook_url: str | None) -> "BaseNotifier | None":
    """创建通知器实例

    Args:
        channel: 通知渠道名称（wecom/feishu/dingtalk/或外部插件名）
        webhook_url: Webhook URL

    Returns:
        通知器实例，配置不完整时返回 None
    """
    if not channel or not webhook_url:
        return None

    registry = _discover_notifiers()
    channel_lower = channel.strip().lower()

    notifier_cls = registry.get(channel_lower)
    if notifier_cls is None:
        available = ", ".join(sorted(registry.keys()))
        logger.warning(
            f"Unknown notifier channel '{channel}'. Available: {available}"
        )
        return None

    return notifier_cls(webhook_url)
