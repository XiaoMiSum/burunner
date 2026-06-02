"""通知器基类与通知消息载荷定义。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger("burunner.notifier")


@dataclass
class NotifyPayload:
    """发送通知所需的聚合信息。"""

    suite_name: str
    is_success: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    error: int = 0
    incomplete: int = 0
    total_elapsed: float = 0.0
    env_name: str | None = None
    failed_cases: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> str:
        if self.total == 0:
            return "0.0%"
        return f"{self.passed / self.total * 100:.1f}%"

    @property
    def status_text(self) -> str:
        return "✅ 全部通过" if self.is_success else "❌ 存在失败"

    @property
    def elapsed_text(self) -> str:
        seconds = int(self.total_elapsed)
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m{secs}s"


class BaseNotifier(ABC):
    """通知器抽象基类。

    外部插件开发者需要继承此类并实现 send() 方法。

    注册方式：在外部包的 pyproject.toml 中添加：

        [project.entry-points."burunner.notifiers"]
        my_channel = "my_package.module:MyNotifier"

    实现示例：

        from burunner.notifier import BaseNotifier, NotifyPayload

        class MyNotifier(BaseNotifier):
            def send(self, payload: NotifyPayload) -> bool:
                # 发送通知逻辑
                content = "\\n".join(self._build_summary_lines(payload))
                # ... 发送到你的渠道
                return True  # 成功返回 True
    """

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    @abstractmethod
    def send(self, payload: NotifyPayload) -> bool:
        """发送通知。成功返回 True，失败返回 False（不抛异常）。"""
        ...

    def _build_summary_lines(self, payload: NotifyPayload) -> list[str]:
        """构建通知正文的各行文本（Markdown 格式）。"""
        lines = [
            f"**测试执行报告**",
            f"",
            f"**套件**: {payload.suite_name}",
            f"**状态**: {payload.status_text}",
            f"**环境**: {payload.env_name or 'default'}",
            f"**耗时**: {payload.elapsed_text}",
            f"**统计**: 总计 {payload.total} | "
            f"通过 {payload.passed} | 失败 {payload.failed} | "
            f"错误 {payload.error} | 未完成 {payload.incomplete}",
            f"**通过率**: {payload.pass_rate}",
        ]
        if payload.failed_cases:
            lines.append("")
            lines.append("**失败用例**:")
            for name in payload.failed_cases[:10]:
                lines.append(f"- {name}")
            if len(payload.failed_cases) > 10:
                lines.append(f"- ... 等共 {len(payload.failed_cases)} 个")
        return lines
