"""通知器实现类单元测试。"""

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from burunner.notifier.base import NotifyPayload
from burunner.notifier.wecom import WecomNotifier
from burunner.notifier.feishu import FeishuNotifier
from burunner.notifier.dingtalk import DingtalkNotifier
from burunner.notifier.factory import create_notifier


class TestWecomNotifier:
    """企业微信通知器测试。"""

    def test_create_notifier(self):
        notifier = WecomNotifier(webhook_url="https://example.com/webhook")
        assert notifier.webhook_url == "https://example.com/webhook"

    def test_send_success(self):
        """发送成功。"""
        notifier = WecomNotifier(webhook_url="https://example.com/webhook")
        payload = NotifyPayload(
            suite_name="测试套件",
            is_success=True,
            total=10,
            passed=10,
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"errcode": 0}).encode()
            mock_urlopen.return_value.__enter__ = MagicMock(
                return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            result = notifier.send(payload)
            assert result is True

    def test_send_error_response(self):
        """返回错误码。"""
        notifier = WecomNotifier(webhook_url="https://example.com/webhook")
        payload = NotifyPayload(suite_name="测试", is_success=True)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"errcode": 1, "errmsg": "错误"}
            ).encode()
            mock_urlopen.return_value.__enter__ = MagicMock(
                return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            result = notifier.send(payload)
            assert result is False

    def test_send_network_error(self):
        """网络错误。"""
        notifier = WecomNotifier(webhook_url="https://example.com/webhook")
        payload = NotifyPayload(suite_name="测试", is_success=True)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("网络错误")

            result = notifier.send(payload)
            assert result is False

    def test_build_markdown_content(self):
        """构建 Markdown 内容。"""
        notifier = WecomNotifier(webhook_url="https://example.com")
        payload = NotifyPayload(
            suite_name="测试套件",
            is_success=False,
            total=5,
            passed=3,
            failed=2,
            total_elapsed=100.0,
            env_name="production",
            failed_cases=["用例1", "用例2"],
        )

        lines = notifier._build_summary_lines(payload)
        content = "\n".join(lines)

        assert "**测试执行报告**" in content
        assert "**套件**: 测试套件" in content
        assert "**状态**: ❌ 存在失败" in content
        assert "**通过率**: 60.0%" in content


class TestFeishuNotifier:
    """飞书通知器测试。"""

    def test_create_notifier(self):
        notifier = FeishuNotifier(webhook_url="https://example.com/webhook")
        assert notifier.webhook_url == "https://example.com/webhook"

    def test_send_success(self):
        """发送成功。"""
        notifier = FeishuNotifier(webhook_url="https://example.com/webhook")
        payload = NotifyPayload(
            suite_name="测试", is_success=True, total=5, passed=5)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"StatusCode": 0}).encode()
            mock_urlopen.return_value.__enter__ = MagicMock(
                return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            result = notifier.send(payload)
            assert result is True

    def test_send_error(self):
        """发送失败。"""
        notifier = FeishuNotifier(webhook_url="https://example.com/webhook")
        payload = NotifyPayload(suite_name="测试", is_success=True)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = OSError("连接失败")

            result = notifier.send(payload)
            assert result is False


class TestDingtalkNotifier:
    """钉钉通知器测试。"""

    def test_create_notifier(self):
        notifier = DingtalkNotifier(webhook_url="https://example.com/webhook")
        assert notifier.webhook_url == "https://example.com/webhook"

    def test_send_success(self):
        """发送成功。"""
        notifier = DingtalkNotifier(webhook_url="https://example.com/webhook")
        payload = NotifyPayload(
            suite_name="测试", is_success=True, total=3, passed=3)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"errcode": 0}).encode()
            mock_urlopen.return_value.__enter__ = MagicMock(
                return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            result = notifier.send(payload)
            assert result is True

    def test_send_error(self):
        """发送失败。"""
        notifier = DingtalkNotifier(webhook_url="https://example.com/webhook")
        payload = NotifyPayload(suite_name="测试", is_success=True)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("超时")

            result = notifier.send(payload)
            assert result is False


class TestCreateNotifier:
    """create_notifier 工厂函数测试。"""

    def test_create_wecom(self):
        notifier = create_notifier("wecom", "https://example.com")
        assert isinstance(notifier, WecomNotifier)

    def test_create_feishu(self):
        notifier = create_notifier("feishu", "https://example.com")
        assert isinstance(notifier, FeishuNotifier)

    def test_create_dingtalk(self):
        notifier = create_notifier("dingtalk", "https://example.com")
        assert isinstance(notifier, DingtalkNotifier)

    def test_create_unknown_channel(self):
        """未知渠道返回 None。"""
        notifier = create_notifier("unknown", "https://example.com")
        assert notifier is None

    def test_create_none_channel(self):
        """None 渠道返回 None。"""
        notifier = create_notifier(None, "https://example.com")
        assert notifier is None

    def test_create_empty_webhook(self):
        """空 webhook URL 返回 None。"""
        notifier = create_notifier("wecom", "")
        assert notifier is None

    def test_create_none_webhook(self):
        """None webhook URL 返回 None。"""
        notifier = create_notifier("wecom", None)
        assert notifier is None
