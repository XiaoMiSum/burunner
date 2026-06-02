"""通知器模块单元测试。"""

from burunner.notifier.base import BaseNotifier, NotifyPayload


class TestNotifyPayload:
    """NotifyPayload 数据类测试。"""

    def test_create_payload_default(self):
        payload = NotifyPayload(suite_name="测试套件", is_success=True)
        assert payload.suite_name == "测试套件"
        assert payload.is_success is True
        assert payload.total == 0
        assert payload.passed == 0
        assert payload.failed == 0
        assert payload.error == 0
        assert payload.incomplete == 0
        assert payload.total_elapsed == 0.0
        assert payload.env_name is None
        assert payload.failed_cases == []

    def test_create_payload_full(self):
        payload = NotifyPayload(
            suite_name="完整测试",
            is_success=False,
            total=10,
            passed=7,
            failed=2,
            error=1,
            incomplete=0,
            total_elapsed=125.5,
            env_name="production",
            failed_cases=["用例A", "用例B", "用例C"],
        )
        assert payload.suite_name == "完整测试"
        assert payload.total == 10
        assert payload.failed == 2
        assert payload.env_name == "production"
        assert len(payload.failed_cases) == 3

    def test_pass_rate_zero_total(self):
        payload = NotifyPayload(suite_name="测试", is_success=True)
        assert payload.pass_rate == "0.0%"

    def test_pass_rate_calculation(self):
        payload = NotifyPayload(
            suite_name="测试",
            is_success=False,
            total=10,
            passed=8,
            failed=2,
        )
        assert payload.pass_rate == "80.0%"

    def test_pass_rate_all_passed(self):
        payload = NotifyPayload(
            suite_name="测试",
            is_success=True,
            total=5,
            passed=5,
        )
        assert payload.pass_rate == "100.0%"

    def test_status_text_success(self):
        payload = NotifyPayload(suite_name="测试", is_success=True)
        assert payload.status_text == "✅ 全部通过"

    def test_status_text_failure(self):
        payload = NotifyPayload(suite_name="测试", is_success=False)
        assert payload.status_text == "❌ 存在失败"

    def test_elapsed_text_seconds(self):
        payload = NotifyPayload(
            suite_name="测试", is_success=True, total_elapsed=45.0
        )
        assert payload.elapsed_text == "45s"

    def test_elapsed_text_minutes(self):
        payload = NotifyPayload(
            suite_name="测试", is_success=True, total_elapsed=125.0
        )
        assert payload.elapsed_text == "2m5s"

    def test_elapsed_text_exact_minute(self):
        payload = NotifyPayload(
            suite_name="测试", is_success=True, total_elapsed=120.0
        )
        assert payload.elapsed_text == "2m0s"


class TestBaseNotifier:
    """BaseNotifier 抽象基类测试。"""

    def test_notifier_is_abstract(self):
        """BaseNotifier 不能被直接实例化。"""
        import abc

        assert issubclass(BaseNotifier, abc.ABC)

    def test_notifier_concrete_implementation(self):
        """可以创建具体的通知器实现。"""

        class TestNotifier(BaseNotifier):
            def send(self, payload: NotifyPayload) -> bool:
                return True

        notifier = TestNotifier(webhook_url="https://example.com/webhook")
        assert notifier.webhook_url == "https://example.com/webhook"

    def test_build_summary_lines_basic(self):
        class TestNotifier(BaseNotifier):
            def send(self, payload: NotifyPayload) -> bool:
                return True

        notifier = TestNotifier(webhook_url="https://example.com")
        payload = NotifyPayload(
            suite_name="测试套件",
            is_success=True,
            total=10,
            passed=10,
            total_elapsed=60.0,
            env_name="production",
        )

        lines = notifier._build_summary_lines(payload)
        assert len(lines) > 0
        assert "**测试执行报告**" in lines[0]
        assert "**套件**: 测试套件" in lines
        assert "**状态**: ✅ 全部通过" in lines
        assert "**环境**: production" in lines
        assert "**耗时**: 1m0s" in lines
        assert "**通过率**: 100.0%" in lines

    def test_build_summary_lines_with_failures(self):
        class TestNotifier(BaseNotifier):
            def send(self, payload: NotifyPayload) -> bool:
                return True

        notifier = TestNotifier(webhook_url="https://example.com")
        payload = NotifyPayload(
            suite_name="测试套件",
            is_success=False,
            total=5,
            passed=3,
            failed=2,
            total_elapsed=100.0,
            failed_cases=["失败用例1", "失败用例2"],
        )

        lines = notifier._build_summary_lines(payload)
        assert "**状态**: ❌ 存在失败" in lines
        assert "**失败用例**:" in lines
        assert "- 失败用例1" in lines
        assert "- 失败用例2" in lines

    def test_build_summary_lines_many_failures(self):
        class TestNotifier(BaseNotifier):
            def send(self, payload: NotifyPayload) -> bool:
                return True

        notifier = TestNotifier(webhook_url="https://example.com")
        failed_cases = [f"用例{i}" for i in range(15)]
        payload = NotifyPayload(
            suite_name="测试套件",
            is_success=False,
            total=15,
            failed=15,
            failed_cases=failed_cases,
        )

        lines = notifier._build_summary_lines(payload)
        # 只显示前 10 个
        assert "- 用例0" in lines
        assert "- 用例9" in lines
        # 应该有汇总行
        assert any("等共 15 个" in line for line in lines)

    def test_send_not_implemented(self):
        """未实现 send 方法的子类应该报错。"""
        import pytest

        class IncompleteNotifier(BaseNotifier):
            pass

        with pytest.raises(TypeError):
            IncompleteNotifier(webhook_url="https://example.com")
