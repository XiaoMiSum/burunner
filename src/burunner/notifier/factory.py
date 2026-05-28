"""通知器工厂 —— 根据配置创建对应平台的通知器实例。"""

from __future__ import annotations

from burunner.notifier.base import BaseNotifier
from burunner.notifier.dingtalk import DingtalkNotifier
from burunner.notifier.feishu import FeishuNotifier
from burunner.notifier.wecom import WecomNotifier
from burunner.utils.logger import get_logger

logger = get_logger("notifier")

# ---------------------------------------------------------------------------
# 注册表 —— 渠道名(小写) -> 通知器类
# ---------------------------------------------------------------------------
NOTIFIER_REGISTRY: dict[str, type[BaseNotifier]] = {
    "wecom": WecomNotifier,
    "feishu": FeishuNotifier,
    "dingtalk": DingtalkNotifier,
}

# 支持的通知渠道名称（大小写不敏感）
SUPPORTED_CHANNELS = list(NOTIFIER_REGISTRY.keys())


def create_notifier(
    channel: str | None,
    webhook_url: str | None,
) -> BaseNotifier | None:
    """根据渠道名和 webhook URL 创建通知器。

    返回 None 表示未配置或配置无效（不阻断主流程）。
    """
    if not channel or not webhook_url:
        return None

    channel_lower = channel.strip().lower()
    notifier_cls = NOTIFIER_REGISTRY.get(channel_lower)

    if notifier_cls is None:
        logger.warning(
            "不支持的通知渠道 '%s'，可用渠道: %s",
            channel, SUPPORTED_CHANNELS,
        )
        return None

    return notifier_cls(webhook_url)
