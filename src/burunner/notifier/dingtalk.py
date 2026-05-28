"""钉钉 Webhook 通知器。"""

from __future__ import annotations

import json
import urllib.request
import urllib.error

from burunner.notifier.base import BaseNotifier, NotifyPayload, logger


class DingtalkNotifier(BaseNotifier):
    """通过钉钉自定义机器人 Webhook 发送 Markdown 通知。

    Webhook 文档: https://open.dingtalk.com/document/orgapp/custom-robots-send-group-messages
    """

    def send(self, payload: NotifyPayload) -> bool:
        content = "\n".join(self._build_summary_lines(payload))
        title = f"{'✅' if payload.is_success else '❌'} 测试执行报告 - {payload.suite_name}"
        body = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content,
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
                if result.get("errcode", -1) != 0:
                    logger.warning(
                        "钉钉通知返回错误: %s", result.get("errmsg", "unknown"))
                    return False
                return True
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            logger.warning("钉钉通知发送失败: %s", e)
            return False
