"""飞书 Webhook 通知器。"""

from __future__ import annotations

import json
import urllib.request
import urllib.error

from burunner.notifier.base import BaseNotifier, NotifyPayload, logger


class FeishuNotifier(BaseNotifier):
    """通过飞书自定义机器人 Webhook 发送富文本通知。

    Webhook 文档: https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
    """

    def send(self, payload: NotifyPayload) -> bool:
        content = "\n".join(self._build_summary_lines(payload))
        # 飞书支持 interactive (card) 和 text/post 类型
        # 使用 interactive 卡片获得更好的展示效果
        body = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{'✅' if payload.is_success else '❌'} 测试执行报告 - {payload.suite_name}",
                    },
                    "template": "green" if payload.is_success else "red",
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content,
                    }
                ],
            },
        }
        return self._post(body)

    def _post(self, body: dict) -> bool:
        try:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                code = result.get("code", result.get("StatusCode", -1))
                if code != 0:
                    logger.warning(
                        "飞书通知返回错误: %s", result.get("msg", result.get("StatusMessage", "unknown")))
                    return False
                return True
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            logger.warning("飞书通知发送失败: %s", e)
            return False
