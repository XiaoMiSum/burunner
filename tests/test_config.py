"""配置模块单元测试。"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from burunner.config import RunnerConfig
from burunner.parser.models import CookieItem, EnvConfig


class TestEnvHelpers:
    """环境变量辅助函数测试。"""

    def test_env_bool_default(self):
        from burunner.config import _env_bool

        with patch.dict(os.environ, {}, clear=False):
            if "TEST_VAR" in os.environ:
                del os.environ["TEST_VAR"]
            assert _env_bool("TEST_VAR", True) is True
            assert _env_bool("TEST_VAR", False) is False

    def test_env_bool_true_values(self):
        from burunner.config import _env_bool

        for val in ["1", "true", "True", "TRUE", "yes", "YES", "on", "ON"]:
            with patch.dict(os.environ, {"TEST_VAR": val}, clear=True):
                assert _env_bool("TEST_VAR", False) is True

    def test_env_bool_false_values(self):
        from burunner.config import _env_bool

        for val in ["0", "false", "False", "no", "off", "", "other"]:
            with patch.dict(os.environ, {"TEST_VAR": val}, clear=True):
                assert _env_bool("TEST_VAR", True) is False

    def test_env_int_default(self):
        from burunner.config import _env_int

        with patch.dict(os.environ, {}, clear=False):
            if "TEST_INT" in os.environ:
                del os.environ["TEST_INT"]
            assert _env_int("TEST_INT", 42) == 42

    def test_env_int_valid(self):
        from burunner.config import _env_int

        with patch.dict(os.environ, {"TEST_INT": "100"}, clear=True):
            assert _env_int("TEST_INT", 0) == 100

    def test_env_int_invalid(self):
        from burunner.config import _env_int

        with patch.dict(os.environ, {"TEST_INT": "not_a_number"}, clear=True):
            assert _env_int("TEST_INT", 99) == 99

    def test_env_float_default(self):
        from burunner.config import _env_float

        with patch.dict(os.environ, {}, clear=False):
            if "TEST_FLOAT" in os.environ:
                del os.environ["TEST_FLOAT"]
            assert _env_float("TEST_FLOAT", 1.5) == 1.5

    def test_env_float_valid(self):
        from burunner.config import _env_float

        with patch.dict(os.environ, {"TEST_FLOAT": "3.14"}, clear=True):
            assert _env_float("TEST_FLOAT", 0.0) == 3.14

    def test_env_float_invalid(self):
        from burunner.config import _env_float

        with patch.dict(os.environ, {"TEST_FLOAT": "not_a_float"}, clear=True):
            assert _env_float("TEST_FLOAT", 2.0) == 2.0


class TestCollectFields:
    """字段收集函数测试。"""

    def test_collect_fields_basic(self):
        from burunner.config import _collect_fields

        source = {"a": 1, "b": 2, "c": 3}
        result = _collect_fields(source, ("a", "c"))
        assert result == {"a": 1, "c": 3}

    def test_collect_fields_missing(self):
        from burunner.config import _collect_fields

        source = {"a": 1}
        result = _collect_fields(source, ("a", "b"))
        assert result == {"a": 1}

    def test_collect_path_fields(self):
        from burunner.config import _collect_path_fields

        source = {"dir1": "/tmp/test", "dir2": "/tmp/other"}
        result = _collect_path_fields(source, ("dir1",))
        assert result == {"dir1": Path("/tmp/test")}


class TestRunnerConfig:
    """RunnerConfig 数据类测试。"""

    def test_default_values(self):
        cfg = RunnerConfig()
        assert cfg.llm_provider == "openai"
        assert cfg.llm_model == "gpt-4o"
        assert cfg.llm_temperature == 0.0
        assert cfg.headless is True
        assert cfg.keep_browser_open is False
        assert cfg.parallel == 1
        assert cfg.max_steps == 0
        assert cfg.case_timeout == 0
        assert cfg.retry_count == 0
        assert cfg.retry_delay == 2.0
        assert cfg.use_vision is True
        assert cfg.results_dir == Path("./allure-results")
        assert cfg.verbose is False
        assert cfg.browser_use_log is False
        assert cfg.cookies == []
        assert cfg.notify_channel is None
        assert cfg.notify_webhook is None
        assert cfg.env_name is None
        assert cfg.source_files == []

    @patch.dict(
        os.environ,
        {
            "BURUNNER_LLM_PROVIDER": "anthropic",
            "BURUNNER_LLM_MODEL": "claude-3",
            "BURUNNER_LLM_TEMPERATURE": "0.7",
            "BURUNNER_HEADLESS": "false",
            "BURUNNER_PARALLEL": "4",
            "BURUNNER_MAX_STEPS": "50",
            "BURUNNER_CASE_TIMEOUT": "300",
            "BURUNNER_RETRY_COUNT": "2",
            "BURUNNER_RETRY_DELAY": "5.0",
            "BURUNNER_NOTIFY_CHANNEL": "feishu",
            "BURUNNER_NOTIFY_WEBHOOK": "https://example.com/webhook",
            "BURUNNER_ENV": "production",
        },
        clear=True,
    )
    def test_from_env(self):
        cfg = RunnerConfig.from_env()
        assert cfg.llm_provider == "anthropic"
        assert cfg.llm_model == "claude-3"
        assert cfg.llm_temperature == 0.7
        assert cfg.headless is False
        assert cfg.parallel == 4
        assert cfg.max_steps == 50
        assert cfg.case_timeout == 300
        assert cfg.retry_count == 2
        assert cfg.retry_delay == 5.0
        assert cfg.notify_channel == "feishu"
        assert cfg.notify_webhook == "https://example.com/webhook"
        assert cfg.env_name == "production"

    def test_merge_yaml_config_none(self):
        cfg = RunnerConfig()
        merged = cfg.merge_yaml_config(None)
        assert merged is cfg

    def test_merge_yaml_config_empty(self):
        cfg = RunnerConfig()
        merged = cfg.merge_yaml_config({})
        assert merged is cfg

    def test_merge_yaml_config_simple_fields(self):
        cfg = RunnerConfig()
        yaml_cfg = {
            "llm_provider": "google",
            "llm_model": "gemini-pro",
            "llm_temperature": 0.5,
            "headless": False,
            "parallel": 2,
        }
        merged = cfg.merge_yaml_config(yaml_cfg)
        assert merged.llm_provider == "google"
        assert merged.llm_model == "gemini-pro"
        assert merged.llm_temperature == 0.5
        assert merged.headless is False
        assert merged.parallel == 2

    def test_merge_yaml_config_path_fields(self):
        cfg = RunnerConfig()
        yaml_cfg = {"results_dir": "/tmp/test-results"}
        merged = cfg.merge_yaml_config(yaml_cfg)
        assert merged.results_dir == Path("/tmp/test-results")

    def test_merge_yaml_config_cookies(self):
        cfg = RunnerConfig()
        yaml_cfg = {
            "cookies": [
                {
                    "name": "session",
                    "value": "abc123",
                    "domain": "example.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": False,
                }
            ]
        }
        merged = cfg.merge_yaml_config(yaml_cfg)
        assert len(merged.cookies) == 1
        assert merged.cookies[0].name == "session"
        assert merged.cookies[0].value == "abc123"
        assert merged.cookies[0].domain == "example.com"
        assert merged.cookies[0].secure is True

    def test_merge_yaml_config_invalid_cookies(self):
        cfg = RunnerConfig()
        yaml_cfg = {"cookies": [{"name": "test"}]}  # 缺少 domain
        merged = cfg.merge_yaml_config(yaml_cfg)
        assert len(merged.cookies) == 0  # 无效 cookie 被忽略

    def test_with_overrides_all(self):
        cfg = RunnerConfig()
        overridden = cfg.with_overrides(
            llm_provider="groq",
            llm_model="llama-3",
            headless=False,
            parallel=8,
        )
        assert overridden.llm_provider == "groq"
        assert overridden.llm_model == "llama-3"
        assert overridden.headless is False
        assert overridden.parallel == 8
        # 原始配置不变
        assert cfg.llm_provider == "openai"

    def test_with_overrides_none_values(self):
        cfg = RunnerConfig()
        overridden = cfg.with_overrides(
            llm_provider=None,
            llm_model="gpt-4",
            headless=None,
        )
        # None 值应该被忽略
        assert overridden.llm_provider == "openai"
        assert overridden.llm_model == "gpt-4"
        assert overridden.headless is True

    def test_merge_env_config_none(self):
        cfg = RunnerConfig()
        merged = cfg.merge_env_config(None)
        assert merged is cfg

    def test_merge_env_config_simple(self):
        cfg = RunnerConfig()
        env_config = EnvConfig(
            name="staging",
            config={
                "llm_provider": "openai",
                "llm_model": "gpt-4-turbo",
                "headless": True,
            },
        )
        merged = cfg.merge_env_config(env_config)
        assert merged.llm_model == "gpt-4-turbo"
        assert merged.headless is True

    def test_merge_env_config_cookies(self):
        cfg = RunnerConfig(
            cookies=[CookieItem(name="global", value="g",
                                domain="example.com")]
        )
        env_config = EnvConfig(
            name="staging",
            cookies=[CookieItem(name="env", value="e", domain="example.com")],
        )
        merged = cfg.merge_env_config(env_config)
        assert len(merged.cookies) == 2
        assert merged.cookies[0].name == "global"
        assert merged.cookies[1].name == "env"

    def test_merge_env_config_cookies_duplicate(self):
        cfg = RunnerConfig(
            cookies=[CookieItem(name="session", value="v1",
                                domain="example.com")]
        )
        env_config = EnvConfig(
            name="staging",
            cookies=[CookieItem(name="session", value="v2",
                                domain="example.com")],
        )
        merged = cfg.merge_env_config(env_config)
        # 环境 cookie 不应该覆盖全局 cookie
        assert len(merged.cookies) == 1
        assert merged.cookies[0].value == "v1"

    def test_ensure_dirs(self, tmp_path):
        cfg = RunnerConfig(results_dir=tmp_path / "test-results")
        cfg.ensure_dirs()
        assert cfg.results_dir.exists()
        assert cfg.screenshots_dir is not None
        assert cfg.screenshots_dir.exists()

    def test_ensure_dirs_custom_screenshots(self, tmp_path):
        cfg = RunnerConfig(
            results_dir=tmp_path / "test-results",
            screenshots_dir=tmp_path / "custom-screenshots",
        )
        cfg.ensure_dirs()
        assert cfg.results_dir.exists()
        assert cfg.screenshots_dir.exists()
        assert cfg.screenshots_dir == tmp_path / "custom-screenshots"
