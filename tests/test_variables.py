"""变量解析引擎单元测试。"""

import os
import re
from unittest.mock import patch

import pytest

from burunner.parser.variables import (
    VariableError,
    VariableRegistry,
    resolve_text,
    resolve_variables_in_steps,
    get_builtin_function_names,
)


class TestVariableRegistry:
    """VariableRegistry 类测试。"""

    def test_create_registry(self):
        registry = VariableRegistry()
        assert registry.available == []

    def test_register_function_decorator(self):
        registry = VariableRegistry()

        @registry.register("test_func")
        def my_func():
            return "test"

        assert "test_func" in registry
        assert registry.get("test_func") == my_func

    def test_register_function_direct(self):
        registry = VariableRegistry()

        def my_func():
            return "direct"

        registry.register_function("my_func", my_func)
        assert "my_func" in registry
        assert registry.get("my_func") == my_func

    def test_get_nonexistent(self):
        registry = VariableRegistry()
        assert registry.get("nonexistent") is None

    def test_contains(self):
        registry = VariableRegistry()

        @registry.register("test")
        def test_fn():
            return "test"

        assert "test" in registry
        assert "nonexistent" not in registry

    def test_available_sorted(self):
        registry = VariableRegistry()

        @registry.register("zebra")
        def zebra():
            return "z"

        @registry.register("alpha")
        def alpha():
            return "a"

        @registry.register("middle")
        def middle():
            return "m"

        assert registry.available == ["alpha", "middle", "zebra"]


class TestBuiltinFunctions:
    """内置函数测试。"""

    def test_timestamp(self):
        result = resolve_text("${timestamp()}")
        assert result.isdigit()
        assert len(result) == 10  # Unix timestamp 秒数

    def test_date(self):
        result = resolve_text("${date()}")
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", result)

    def test_datetime(self):
        result = resolve_text("${datetime()}")
        assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", result)

    def test_utc_datetime(self):
        result = resolve_text("${utc_datetime()}")
        assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", result)

    def test_random_int_default(self):
        result = resolve_text("${random_int()}")
        value = int(result)
        assert 0 <= value <= 9999

    def test_random_int_with_max(self):
        result = resolve_text("${random_int(100)}")
        value = int(result)
        assert 0 <= value <= 100

    def test_random_int_with_range(self):
        result = resolve_text("${random_int(10, 20)}")
        value = int(result)
        assert 10 <= value <= 20

    def test_random_string_default(self):
        result = resolve_text("${random_string()}")
        assert len(result) == 8
        assert result.isalnum()

    def test_random_string_custom_length(self):
        result = resolve_text("${random_string(16)}")
        assert len(result) == 16
        assert result.isalnum()

    def test_random_string_invalid_length(self):
        with pytest.raises(VariableError):
            resolve_text("${random_string(0)}")

        with pytest.raises(VariableError):
            resolve_text("${random_string(1001)}")

    def test_uuid(self):
        result = resolve_text("${uuid()}")
        assert re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            result,
        )

    def test_env_with_default(self):
        with patch.dict(os.environ, {"MY_VAR": "test_value"}, clear=True):
            # env 函数的参数需要用引号括起来
            result = resolve_text("${env('MY_VAR')}")
            assert result == "test_value"

    def test_env_with_default_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            if "NONEXISTENT_VAR" in os.environ:
                del os.environ["NONEXISTENT_VAR"]
            result = resolve_text("${env('NONEXISTENT_VAR', 'fallback')}")
            assert result == "fallback"

    def test_env_missing_no_default(self):
        with patch.dict(os.environ, {}, clear=True):
            if "MISSING_VAR" in os.environ:
                del os.environ["MISSING_VAR"]
            with pytest.raises(VariableError):
                resolve_text("${env('MISSING_VAR')}")

    def test_calc_simple(self):
        result = resolve_text("${calc(2 + 3)}")
        assert result == "5"

    def test_calc_multiplication(self):
        result = resolve_text("${calc(3 * 4)}")
        assert result == "12"

    def test_calc_division(self):
        result = resolve_text("${calc(10 / 2)}")
        assert result == "5"

    def test_calc_complex(self):
        result = resolve_text("${calc(2 ** 3 + 1)}")
        assert result == "9"

    def test_calc_invalid(self):
        with pytest.raises(VariableError):
            resolve_text("${calc(import os)}")


class TestVariableResolution:
    """变量解析测试。"""

    def test_no_variables(self):
        result = resolve_text("纯文本")
        assert result == "纯文本"

    def test_simple_variable(self):
        result = resolve_text("你好 ${name}", variables={"name": "世界"})
        assert result == "你好 世界"

    def test_multiple_variables(self):
        result = resolve_text(
            "${greeting} ${name}", variables={"greeting": "你好", "name": "张三"}
        )
        assert result == "你好 张三"

    def test_variable_not_found(self):
        with pytest.raises(VariableError):
            resolve_text("${missing}", variables={})

    def test_function_in_text(self):
        result = resolve_text("ID: ${uuid()}")
        assert result.startswith("ID: ")
        assert len(result) > 10

    def test_variable_and_function(self):
        result = resolve_text(
            "${name}-${timestamp()}", variables={"name": "user"}
        )
        parts = result.split("-")
        assert parts[0] == "user"
        assert parts[1].isdigit()

    def test_mako_escape_percent(self):
        result = resolve_text("% 这是一行文本")
        assert result == "% 这是一行文本"

    def test_mako_escape_block_tag(self):
        result = resolve_text("包含 <% 的文本")
        assert "<%" in result

    def test_custom_function(self):
        def my_func():
            return "custom"

        result = resolve_text(
            "${my_func()}", custom_functions={"my_func": my_func}
        )
        assert result == "custom"

    def test_custom_function_override_builtin(self):
        def custom_timestamp():
            return "CUSTOM"

        result = resolve_text(
            "${timestamp()}", custom_functions={"timestamp": custom_timestamp}
        )
        assert result == "CUSTOM"

    def test_variable_override_builtin_function(self):
        # 变量可以覆盖内置函数,但如果尝试调用字符串变量会失败
        # 正确的使用是直接引用变量而不是调用
        result = resolve_text(
            "${date}", variables={"date": "2024-01-01"}
        )
        # date 变量直接输出
        assert result == "2024-01-01"


class TestBatchResolution:
    """批量变量解析测试。"""

    def test_resolve_steps(self):
        steps = ["步骤1: ${name}", "步骤2: ${action}"]
        variables = {"name": "测试", "action": "点击"}
        result = resolve_variables_in_steps(steps, variables)
        assert result == ["步骤1: 测试", "步骤2: 点击"]

    def test_resolve_steps_empty(self):
        result = resolve_variables_in_steps([], {"name": "test"})
        assert result == []

    def test_resolve_steps_no_variables(self):
        steps = ["纯文本步骤"]
        result = resolve_variables_in_steps(steps, {})
        assert result == ["纯文本步骤"]


class TestGetBuiltinFunctionNames:
    """获取内置函数名测试。"""

    def test_returns_list(self):
        names = get_builtin_function_names()
        assert isinstance(names, list)

    def test_contains_expected_functions(self):
        names = get_builtin_function_names()
        expected = [
            "timestamp",
            "date",
            "datetime",
            "random_int",
            "random_string",
            "uuid",
            "calc",
        ]
        for func in expected:
            assert func in names
