"""会话管理器模块单元测试。"""

import pytest

from burunner.runner.session_manager import _merge_cookies
from burunner.config import RunnerConfig
from burunner.parser.models import TestCase, TestStep, CookieItem


class TestMergeCookies:
    """_merge_cookies 函数测试。"""

    def test_case_cookies_only(self):
        """只有用例级 cookies。"""
        case = TestCase(
            name="测试",
            steps=[TestStep(text="步骤")],
            cookies=[
                CookieItem(name="case_cookie", value="v1",
                           domain="example.com")
            ],
        )
        cfg = RunnerConfig()

        result = _merge_cookies(case, cfg)
        assert len(result) == 1
        assert result[0].name == "case_cookie"

    def test_global_cookies_only(self):
        """只有全局 cookies。"""
        case = TestCase(name="测试", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig(
            cookies=[
                CookieItem(name="global_cookie",
                           value="v2", domain="example.com")
            ]
        )

        result = _merge_cookies(case, cfg)
        assert len(result) == 1
        assert result[0].name == "global_cookie"

    def test_merge_both_no_conflict(self):
        """合并全局和用例 cookies,无冲突。"""
        case = TestCase(
            name="测试",
            steps=[TestStep(text="步骤")],
            cookies=[
                CookieItem(name="case_cookie", value="v1",
                           domain="example.com")
            ],
        )
        cfg = RunnerConfig(
            cookies=[
                CookieItem(name="global_cookie",
                           value="v2", domain="example.com")
            ]
        )

        result = _merge_cookies(case, cfg)
        assert len(result) == 2
        # 用例 cookies 优先
        assert result[0].name == "case_cookie"
        assert result[1].name == "global_cookie"

    def test_case_cookie_overrides_global(self):
        """用例同名 cookie 覆盖全局。"""
        case = TestCase(
            name="测试",
            steps=[TestStep(text="步骤")],
            cookies=[
                CookieItem(name="session", value="case_value",
                           domain="example.com")
            ],
        )
        cfg = RunnerConfig(
            cookies=[
                CookieItem(name="session", value="global_value",
                           domain="example.com"),
                CookieItem(name="other", value="v2", domain="example.com"),
            ]
        )

        result = _merge_cookies(case, cfg)
        # 用例的 session 应该保留,全局的 session 不应该添加
        session_cookies = [c for c in result if c.name == "session"]
        assert len(session_cookies) == 1
        assert session_cookies[0].value == "case_value"
        # other cookie 应该被添加
        other_cookies = [c for c in result if c.name == "other"]
        assert len(other_cookies) == 1

    def test_different_domains_same_name(self):
        """相同名称但不同 domain 的 cookies 都应该保留。"""
        case = TestCase(
            name="测试",
            steps=[TestStep(text="步骤")],
            cookies=[
                CookieItem(name="token", value="v1", domain="api.example.com")
            ],
        )
        cfg = RunnerConfig(
            cookies=[
                CookieItem(name="token", value="v2", domain="web.example.com")
            ]
        )

        result = _merge_cookies(case, cfg)
        assert len(result) == 2
        domains = [c.domain for c in result]
        assert "api.example.com" in domains
        assert "web.example.com" in domains

    def test_empty_cookies(self):
        """全局和用例都没有 cookies。"""
        case = TestCase(name="测试", steps=[TestStep(text="步骤")])
        cfg = RunnerConfig()

        result = _merge_cookies(case, cfg)
        assert result == []

    def test_multiple_case_cookies(self):
        """用例有多个 cookies。"""
        case = TestCase(
            name="测试",
            steps=[TestStep(text="步骤")],
            cookies=[
                CookieItem(name="c1", value="v1", domain="example.com"),
                CookieItem(name="c2", value="v2", domain="example.com"),
                CookieItem(name="c3", value="v3", domain="example.com"),
            ],
        )
        cfg = RunnerConfig()

        result = _merge_cookies(case, cfg)
        assert len(result) == 3
        names = [c.name for c in result]
        assert names == ["c1", "c2", "c3"]
