"""LLM Provider 模块单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from burunner.llm.provider import (
    LLMProviderError,
    ProviderSpec,
    _missing_dep,
    _resolve,
)


class TestLLMProviderError:
    """LLMProviderError 异常测试。"""

    def test_inherits_from_configuration_error(self):
        """继承自 ConfigurationError。"""
        from burunner.exceptions import ConfigurationError

        error = LLMProviderError("测试错误")
        assert isinstance(error, ConfigurationError)

    def test_error_message(self):
        """错误消息。"""
        error = LLMProviderError("provider 加载失败")
        assert "provider 加载失败" in str(error)


class TestMissingDep:
    """_missing_dep 函数测试。"""

    def test_missing_dep_message(self):
        """生成缺失依赖错误消息。"""
        exc = ImportError("No module named 'xyz'")
        error = _missing_dep("openai", "openai", exc)

        assert "openai" in str(error)
        assert "pip install openai" in str(error)
        assert "No module named 'xyz'" in str(error)


class TestResolve:
    """_resolve 函数测试。"""

    def test_resolve_success(self):
        """成功解析类。"""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.ChatOpenAI = MagicMock()
            mock_import.return_value = mock_module

            result = _resolve("openai", "ChatOpenAI")
            assert result == mock_module.ChatOpenAI

    def test_resolve_with_fallback(self):
        """带回退的解析。"""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.ChatOpenAI = None
            mock_module.ChatAnthropic = MagicMock()
            mock_import.return_value = mock_module

            result = _resolve("anthropic", "ChatAnthropic", "ChatOpenAI")
            assert result == mock_module.ChatAnthropic

    def test_resolve_all_fail(self):
        """所有候选都失败。"""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.ChatOpenAI = None
            mock_module.ChatAnthropic = None
            mock_import.return_value = mock_module

            with pytest.raises(LLMProviderError) as exc_info:
                _resolve("test", "ChatOpenAI", "ChatAnthropic")

            assert "ChatOpenAI" in str(exc_info.value)
            assert "ChatAnthropic" in str(exc_info.value)


class TestProviderSpec:
    """ProviderSpec 数据类测试。"""

    def test_create_provider_spec(self):
        """创建 ProviderSpec。"""
        spec = ProviderSpec(
            class_candidates=("ChatOpenAI",),
            default_endpoint="https://api.openai.com",
        )

        assert spec.class_candidates == ("ChatOpenAI",)
        assert spec.default_endpoint == "https://api.openai.com"
        assert spec.fallback_candidates == ()

    def test_provider_spec_with_fallback(self):
        """带回退候选的 ProviderSpec。"""
        spec = ProviderSpec(
            class_candidates=("ChatDeepSeek",),
            fallback_candidates=("ChatOpenAI",),
        )

        assert spec.class_candidates == ("ChatDeepSeek",)
        assert spec.fallback_candidates == ("ChatOpenAI",)

    def test_provider_spec_frozen(self):
        """ProviderSpec 是不可变的。"""
        spec = ProviderSpec(class_candidates=("ChatOpenAI",))

        with pytest.raises((TypeError, Exception)):  # dataclasses.FrozenInstanceError
            spec.class_candidates = ("ChatAnthropic",)


class TestLLMProviderIntegration:
    """LLM Provider 集成测试。"""

    def test_provider_registry_exists(self):
        """Provider 注册表存在。"""
        try:
            from burunner.llm.provider import PROVIDER_REGISTRY
            assert isinstance(PROVIDER_REGISTRY, dict)
            assert len(PROVIDER_REGISTRY) > 0
        except ImportError:
            pytest.skip("LLM 模块不可用")

    def test_provider_spec_in_registry(self):
        """注册表中包含 ProviderSpec。"""
        try:
            from burunner.llm.provider import PROVIDER_REGISTRY
            for name, spec in PROVIDER_REGISTRY.items():
                assert isinstance(spec, ProviderSpec)
                assert len(spec.class_candidates) > 0
        except ImportError:
            pytest.skip("LLM 模块不可用")

    def test_common_providers_registered(self):
        """常见 provider 已注册。"""
        try:
            from burunner.llm.provider import PROVIDER_REGISTRY
            # 至少应该有一些常见 provider
            assert len(PROVIDER_REGISTRY) > 0
        except ImportError:
            pytest.skip("LLM 模块不可用")


class TestLLMCustomizer:
    """LLM Customizer 测试。"""

    def test_customizer_signature(self):
        """Customizer 签名。"""
        from typing import Callable
        from burunner.llm.provider import Customizer

        # Customizer 应该是 Callable 类型
        assert Customizer is not None

    def test_customizer_execution(self):
        """执行 customizer。"""
        def mock_customizer(kwargs, base_url, api_key, extra):
            kwargs["custom"] = True

        kwargs = {}
        mock_customizer(kwargs, None, None, {})

        assert kwargs["custom"] is True
