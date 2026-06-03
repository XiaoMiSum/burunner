"""配置校验逻辑单元测试 - 测试 RunnerConfig.validate() 方法。"""

import pytest

from burunner.config import RunnerConfig
from burunner.exceptions import ConfigurationError


class TestConfigValidation:
    """RunnerConfig.validate() 方法测试。"""

    def test_valid_default_config(self):
        """测试默认配置校验通过。"""
        cfg = RunnerConfig()
        cfg.validate()  # 不应抛出异常

    def test_valid_temperature_boundary(self):
        """测试 temperature 边界值。"""
        # 0.0 应该有效
        cfg = RunnerConfig(llm_temperature=0.0)
        cfg.validate()

        # 2.0 应该有效
        cfg = RunnerConfig(llm_temperature=2.0)
        cfg.validate()

    def test_invalid_temperature_below_zero(self):
        """测试 temperature 小于 0 抛出异常。"""
        cfg = RunnerConfig(llm_temperature=-0.1)
        with pytest.raises(ConfigurationError) as exc_info:
            cfg.validate()
        assert "temperature" in str(exc_info.value)
        assert "0.0~2.0" in str(exc_info.value)

    def test_invalid_temperature_above_two(self):
        """测试 temperature 大于 2 抛出异常。"""
        cfg = RunnerConfig(llm_temperature=2.1)
        with pytest.raises(ConfigurationError) as exc_info:
            cfg.validate()
        assert "temperature" in str(exc_info.value)

    def test_invalid_parallel_zero(self):
        """测试 parallel 为 0 抛出异常。"""
        cfg = RunnerConfig(parallel=0)
        with pytest.raises(ConfigurationError) as exc_info:
            cfg.validate()
        assert "parallel" in str(exc_info.value)
        assert ">= 1" in str(exc_info.value)

    def test_invalid_parallel_negative(self):
        """测试 parallel 为负数抛出异常。"""
        cfg = RunnerConfig(parallel=-1)
        with pytest.raises(ConfigurationError) as exc_info:
            cfg.validate()
        assert "parallel" in str(exc_info.value)

    def test_valid_parallel_one(self):
        """测试 parallel 为 1 有效。"""
        cfg = RunnerConfig(parallel=1)
        cfg.validate()

    def test_invalid_max_steps_negative(self):
        """测试 max_steps 为负数抛出异常。"""
        cfg = RunnerConfig(max_steps=-1)
        with pytest.raises(ConfigurationError) as exc_info:
            cfg.validate()
        assert "max-steps" in str(exc_info.value)
        assert "不能为负数" in str(exc_info.value)

    def test_valid_max_steps_zero(self):
        """测试 max_steps 为 0 有效（动态计算）。"""
        cfg = RunnerConfig(max_steps=0)
        cfg.validate()

    def test_valid_max_steps_positive(self):
        """测试 max_steps 为正数有效。"""
        cfg = RunnerConfig(max_steps=100)
        cfg.validate()

    def test_invalid_case_timeout_negative(self):
        """测试 case_timeout 为负数抛出异常。"""
        cfg = RunnerConfig(case_timeout=-1)
        with pytest.raises(ConfigurationError) as exc_info:
            cfg.validate()
        assert "case-timeout" in str(exc_info.value)
        assert "不能为负数" in str(exc_info.value)

    def test_valid_case_timeout_zero(self):
        """测试 case_timeout 为 0 有效（不限制）。"""
        cfg = RunnerConfig(case_timeout=0)
        cfg.validate()

    def test_invalid_retry_count_negative(self):
        """测试 retry_count 为负数抛出异常。"""
        cfg = RunnerConfig(retry_count=-1)
        with pytest.raises(ConfigurationError) as exc_info:
            cfg.validate()
        assert "retry" in str(exc_info.value)
        assert "不能为负数" in str(exc_info.value)

    def test_valid_retry_count_zero(self):
        """测试 retry_count 为 0 有效（不重试）。"""
        cfg = RunnerConfig(retry_count=0)
        cfg.validate()

    def test_multiple_validation_errors(self):
        """测试多个错误时只抛出第一个。"""
        cfg = RunnerConfig(parallel=0, retry_count=-1)
        with pytest.raises(ConfigurationError):
            cfg.validate()


class TestConfigDescribe:
    """RunnerConfig.describe() 方法测试。"""

    def test_describe_returns_string(self):
        """测试 describe 返回字符串。"""
        cfg = RunnerConfig()
        description = cfg.describe()
        assert isinstance(description, str)

    def test_describe_contains_key_info(self):
        """测试 describe 包含关键信息。"""
        cfg = RunnerConfig(
            llm_provider="openai",
            llm_model="gpt-4o",
            parallel=4,
            max_steps=50,
        )
        description = cfg.describe()
        assert "openai" in description
        assert "gpt-4o" in description
        assert "parallel=4" in description
        assert "max_steps=50" in description

    def test_describe_with_notify(self):
        """测试 describe 包含通知配置。"""
        cfg = RunnerConfig(notify_channel="wecom")
        description = cfg.describe()
        assert "wecom" in description

    def test_describe_without_notify(self):
        """测试无通知配置时不显示。"""
        cfg = RunnerConfig()
        description = cfg.describe()
        assert "Notify" not in description


class TestConfigEnsureDirs:
    """RunnerConfig.ensure_dirs() 方法测试。"""

    def test_ensure_dirs_creates_directories(self, tmp_path):
        """测试 ensure_dirs 创建目录。"""
        results_dir = tmp_path / "allure-results"
        cfg = RunnerConfig(results_dir=results_dir)
        cfg.ensure_dirs()

        assert results_dir.exists()
        assert (results_dir / "screenshots").exists()

    def test_ensure_dirs_idempotent(self, tmp_path):
        """测试 ensure_dirs 可重复调用。"""
        results_dir = tmp_path / "allure-results"
        cfg = RunnerConfig(results_dir=results_dir)

        cfg.ensure_dirs()
        cfg.ensure_dirs()  # 不应抛出异常

        assert results_dir.exists()

    def test_ensure_dirs_custom_screenshots_dir(self, tmp_path):
        """测试自定义 screenshots_dir。"""
        results_dir = tmp_path / "allure-results"
        screenshots_dir = tmp_path / "custom-screenshots"
        cfg = RunnerConfig(
            results_dir=results_dir,
            screenshots_dir=screenshots_dir,
        )
        cfg.ensure_dirs()

        assert results_dir.exists()
        assert screenshots_dir.exists()
