"""测试完成通知模块 —— 支持企业微信、飞书、钉钉。"""

from burunner.notifier.base import BaseNotifier, NotifyPayload
from burunner.notifier.factory import (
    NOTIFIER_REGISTRY,
    SUPPORTED_CHANNELS,
    create_notifier,
)

__all__ = [
    "BaseNotifier",
    "NOTIFIER_REGISTRY",
    "NotifyPayload",
    "SUPPORTED_CHANNELS",
    "create_notifier",
]
