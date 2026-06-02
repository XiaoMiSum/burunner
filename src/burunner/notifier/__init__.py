"""测试完成通知模块 —— 支持企业微信、飞书、钉钉及外部插件扩展。"""

from .base import BaseNotifier, NotifyPayload
from .factory import create_notifier

__all__ = ["BaseNotifier", "NotifyPayload", "create_notifier"]
