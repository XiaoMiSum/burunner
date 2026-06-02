"""异常体系单元测试。"""

import pytest

from burunner.exceptions import (
    BurunnerError,
    ConfigurationError,
    ExecutionError,
    TransientError,
    PermanentError,
    BrowserError,
    LLMError,
)


class TestExceptionHierarchy:
    """异常继承关系测试。"""

    def test_burunner_error_is_exception(self):
        assert issubclass(BurunnerError, Exception)

    def test_configuration_error_inherits_burunner_error(self):
        assert issubclass(ConfigurationError, BurunnerError)

    def test_execution_error_inherits_burunner_error(self):
        assert issubclass(ExecutionError, BurunnerError)

    def test_transient_error_inherits_execution_error(self):
        assert issubclass(TransientError, ExecutionError)

    def test_permanent_error_inherits_execution_error(self):
        assert issubclass(PermanentError, ExecutionError)

    def test_browser_error_inherits_transient_error(self):
        assert issubclass(BrowserError, TransientError)

    def test_llm_error_inherits_transient_error(self):
        assert issubclass(LLMError, TransientError)


class TestExceptionCatching:
    """异常捕获测试。"""

    def test_catch_configuration_error_as_burunner_error(self):
        with pytest.raises(BurunnerError):
            raise ConfigurationError("配置错误")

    def test_catch_transient_error_as_execution_error(self):
        with pytest.raises(ExecutionError):
            raise TransientError("临时错误")

    def test_catch_browser_error_as_transient_error(self):
        with pytest.raises(TransientError):
            raise BrowserError("浏览器错误")

    def test_catch_llm_error_as_transient_error(self):
        with pytest.raises(TransientError):
            raise LLMError("LLM 错误")

    def test_catch_permanent_error_as_execution_error(self):
        with pytest.raises(ExecutionError):
            raise PermanentError("永久错误")


class TestExceptionMessages:
    """异常消息测试。"""

    def test_configuration_error_message(self):
        msg = "YAML 解析失败: 缺少 name 字段"
        with pytest.raises(ConfigurationError, match=msg):
            raise ConfigurationError(msg)

    def test_transient_error_message(self):
        msg = "网络超时"
        with pytest.raises(TransientError, match=msg):
            raise TransientError(msg)

    def test_permanent_error_message(self):
        msg = "断言失败: 期望 200 实际 404"
        with pytest.raises(PermanentError, match=msg):
            raise PermanentError(msg)

    def test_browser_error_message(self):
        msg = "浏览器崩溃"
        with pytest.raises(BrowserError, match=msg):
            raise BrowserError(msg)

    def test_llm_error_message(self):
        msg = "API 调用失败: rate limit exceeded"
        with pytest.raises(LLMError, match=msg):
            raise LLMError(msg)


class TestExceptionWithCause:
    """异常链测试。"""

    def test_configuration_error_with_cause(self):
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as e:
                raise ConfigurationError("配置解析失败") from e
        except ConfigurationError as ex:
            assert ex.__cause__ is not None
            assert isinstance(ex.__cause__, ValueError)

    def test_transient_error_with_cause(self):
        try:
            try:
                raise TimeoutError("连接超时")
            except TimeoutError as e:
                raise TransientError("请求失败") from e
        except TransientError as ex:
            assert ex.__cause__ is not None
            assert isinstance(ex.__cause__, TimeoutError)
