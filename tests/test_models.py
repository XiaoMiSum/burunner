"""测试用例数据模型单元测试。"""

from pathlib import Path

import pytest

from burunner.parser.models import (
    TestCase,
    TestStep,
    TestSuite,
    TestTemplate,
    CookieItem,
    DataDrivenConfig,
    EnvConfig,
)


class TestTestStep:
    """TestStep 模型测试。"""

    def test_create_step(self):
        step = TestStep(text="打开网页")
        assert step.text == "打开网页"

    def test_str_representation(self):
        step = TestStep(text="点击按钮")
        assert str(step) == "点击按钮"


class TestCookieItem:
    """CookieItem 模型测试。"""

    def test_create_cookie_default(self):
        cookie = CookieItem(name="session", value="abc123",
                            domain="example.com")
        assert cookie.name == "session"
        assert cookie.value == "abc123"
        assert cookie.domain == "example.com"
        assert cookie.path == "/"
        assert cookie.secure is False
        assert cookie.http_only is False

    def test_create_cookie_custom(self):
        cookie = CookieItem(
            name="token",
            value="xyz",
            domain="api.example.com",
            path="/api",
            secure=True,
            http_only=True,
        )
        assert cookie.name == "token"
        assert cookie.secure is True
        assert cookie.http_only is True

    def test_to_playwright_cookie(self):
        cookie = CookieItem(
            name="session",
            value="abc",
            domain="example.com",
            path="/app",
            secure=True,
            http_only=True,
        )
        pw_cookie = cookie.to_playwright_cookie()
        assert pw_cookie == {
            "name": "session",
            "value": "abc",
            "domain": "example.com",
            "path": "/app",
            "secure": True,
            "httpOnly": True,
        }


class TestEnvConfig:
    """EnvConfig 模型测试。"""

    def test_create_env_config_default(self):
        env = EnvConfig(name="production")
        assert env.name == "production"
        assert env.variables == {}
        assert env.config == {}
        assert env.cookies == []

    def test_create_env_config_with_values(self):
        env = EnvConfig(
            name="staging",
            variables={"base_url": "https://staging.example.com"},
            config={"llm_model": "gpt-4"},
            cookies=[CookieItem(name="env", value="staging",
                                domain="example.com")],
        )
        assert env.name == "staging"
        assert len(env.variables) == 1
        assert len(env.config) == 1
        assert len(env.cookies) == 1


class TestTestTemplate:
    """TestTemplate 模型测试。"""

    def test_create_template_default(self):
        tpl = TestTemplate(name="login")
        assert tpl.name == "login"
        assert tpl.description is None
        assert tpl.steps == []
        assert tpl.tags == []
        assert tpl.config == {}
        assert tpl.cookies == []
        assert tpl.variables == {}

    def test_create_template_with_steps(self):
        tpl = TestTemplate(
            name="login",
            description="登录流程",
            steps=[TestStep(text="打开登录页"), TestStep(text="输入用户名")],
            tags=["auth", "smoke"],
        )
        assert tpl.name == "login"
        assert tpl.description == "登录流程"
        assert len(tpl.steps) == 2
        assert len(tpl.tags) == 2


class TestDataDrivenConfig:
    """DataDrivenConfig 模型测试。"""

    def test_create_config_default(self):
        config = DataDrivenConfig()
        assert config.source is None
        assert config.filter_expr is None
        assert config.skip_if_expr is None
        assert config.name_field is None

    def test_create_config_with_values(self):
        config = DataDrivenConfig(
            source="test_data.csv",
            filter_expr="status == 'active'",
            skip_if_expr="data.skip == true",
            name_field="username",
        )
        assert config.source == "test_data.csv"
        assert config.filter_expr == "status == 'active'"
        assert config.skip_if_expr == "data.skip == true"
        assert config.name_field == "username"


class TestTestCase:
    """TestCase 模型测试。"""

    def test_create_case_default(self):
        case = TestCase(name="测试登录")
        assert case.name == "测试登录"
        assert case.description is None
        assert case.steps == []
        assert case.tags == []
        assert case.config == {}
        assert case.cookies == []
        assert case.source_file is None
        assert case.extends is None
        assert case.variables == {}
        assert case.data_driven is None
        assert case.data_row is None
        assert case.data_index is None

    def test_create_case_full(self):
        case = TestCase(
            name="测试登录",
            description="验证用户登录功能",
            steps=[TestStep(text="打开登录页"), TestStep(text="提交表单")],
            tags=["auth", "critical"],
            config={"max_steps": 10},
            cookies=[CookieItem(name="session", value="abc",
                                domain="example.com")],
            source_file=Path("test.yaml"),
            variables={"username": "admin"},
        )
        assert case.name == "测试登录"
        assert case.description == "验证用户登录功能"
        assert len(case.steps) == 2
        assert len(case.tags) == 2
        assert len(case.cookies) == 1

    def test_build_task_prompt_without_description(self):
        case = TestCase(
            name="简单测试",
            steps=[TestStep(text="步骤1"), TestStep(text="步骤2")],
        )
        prompt = case.build_task_prompt()
        assert "测试用例: 简单测试" in prompt
        assert "请严格按以下步骤逐项执行:" in prompt
        assert "1. 步骤1" in prompt
        assert "2. 步骤2" in prompt
        assert '{"success": true|false, "reason": "..."}' in prompt

    def test_build_task_prompt_with_description(self):
        case = TestCase(
            name="完整测试",
            description="这是一个测试目标",
            steps=[TestStep(text="执行操作")],
        )
        prompt = case.build_task_prompt()
        assert "测试目标: 这是一个测试目标" in prompt
        assert "测试用例: 完整测试" in prompt


class TestTestSuite:
    """TestSuite 模型测试。"""

    def test_create_suite_default(self):
        suite = TestSuite()
        assert suite.cases == []
        assert suite.templates == {}
        assert suite.source_files == []
        assert suite.yaml_config == {}
        assert suite.variables == {}
        assert suite.environments == {}
        assert suite.active_env is None

    def test_len_empty(self):
        suite = TestSuite()
        assert len(suite) == 0

    def test_len_with_cases(self):
        suite = TestSuite(
            cases=[
                TestCase(name="用例1"),
                TestCase(name="用例2"),
                TestCase(name="用例3"),
            ]
        )
        assert len(suite) == 3

    def test_filter_by_name_none(self):
        suite = TestSuite(
            cases=[
                TestCase(name="测试A"),
                TestCase(name="测试B"),
            ]
        )
        filtered = suite.filter_by_name(None)
        assert len(filtered.cases) == 2

    def test_filter_by_name_match(self):
        suite = TestSuite(
            cases=[
                TestCase(name="登录测试"),
                TestCase(name="注册测试"),
                TestCase(name="登录验证"),
            ]
        )
        filtered = suite.filter_by_name("登录")
        assert len(filtered.cases) == 2
        assert all("登录" in c.name for c in filtered.cases)

    def test_filter_by_name_regex(self):
        suite = TestSuite(
            cases=[
                TestCase(name="test_login"),
                TestCase(name="test_register"),
                TestCase(name="test_login_v2"),
            ]
        )
        filtered = suite.filter_by_name(r"login.*")
        assert len(filtered.cases) == 2

    def test_filter_by_tags_none(self):
        suite = TestSuite(
            cases=[
                TestCase(name="用例1", tags=["smoke"]),
                TestCase(name="用例2", tags=["regression"]),
            ]
        )
        filtered = suite.filter_by_tags(None)
        assert len(filtered.cases) == 2

    def test_filter_by_tags_single(self):
        suite = TestSuite(
            cases=[
                TestCase(name="用例1", tags=["smoke", "auth"]),
                TestCase(name="用例2", tags=["regression"]),
                TestCase(name="用例3", tags=["smoke", "api"]),
            ]
        )
        filtered = suite.filter_by_tags(["smoke"])
        assert len(filtered.cases) == 2
        assert filtered.cases[0].name == "用例1"
        assert filtered.cases[1].name == "用例3"

    def test_filter_by_tags_multiple(self):
        suite = TestSuite(
            cases=[
                TestCase(name="用例1", tags=["auth"]),
                TestCase(name="用例2", tags=["api"]),
                TestCase(name="用例3", tags=["ui"]),
            ]
        )
        filtered = suite.filter_by_tags(["auth", "api"])
        assert len(filtered.cases) == 2

    def test_filter_by_tags_case_insensitive(self):
        suite = TestSuite(
            cases=[
                TestCase(name="用例1", tags=["Smoke"]),
                TestCase(name="用例2", tags=["smoke"]),
            ]
        )
        filtered = suite.filter_by_tags(["SMOKE"])
        assert len(filtered.cases) == 2
