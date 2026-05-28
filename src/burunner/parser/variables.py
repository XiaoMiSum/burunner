"""参数化变量和函数替换引擎。

支持语法：
  - 变量引用：${var_name}
  - 函数调用：${func_name()} 或 ${func_name(arg1, arg2)}
  - 拼接使用：prefix_${var}_${func()}_suffix
"""

from __future__ import annotations

import math
import os
import random
import re
import string
import time
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any, Callable

from burunner.exceptions import ConfigurationError


class VariableError(ConfigurationError):
    """变量或函数解析错误。"""


# 匹配 ${...} 模式的正则
_EXPR_PATTERN = re.compile(r"\$\{([^}]+)\}")

# 匹配函数调用的正则：func_name(args...)
_FUNC_CALL_PATTERN = re.compile(r"^(\w+)\((.*)\)$", re.DOTALL)


# ---------------------------------------------------------------------------
# 内置函数注册表（封装为实例，支持独立实例化便于测试）
# ---------------------------------------------------------------------------


class VariableRegistry:
    """变量函数注册表，支持独立实例化便于测试。

    测试时可创建独立实例，避免注册表污染或测试间干扰。
    """

    def __init__(self) -> None:
        self._functions: dict[str, Callable[..., str]] = {}

    def register(self, name: str):
        """装饰器：注册函数到此注册表。"""

        def decorator(fn: Callable[..., str]):
            self._functions[name] = fn
            return fn

        return decorator

    def get(self, name: str) -> Callable[..., str] | None:
        """获取已注册的函数，未找到返回 None。"""
        return self._functions.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._functions

    @property
    def available(self) -> list[str]:
        """返回所有已注册函数名的排序列表。"""
        return sorted(self._functions.keys())


# 默认全局注册表实例（保持向后兼容）
_default_registry = VariableRegistry()

_BUILTIN_FUNCTIONS = _default_registry._functions


def _register(name: str):
    """装饰器：注册内置函数到默认注册表。"""
    return _default_registry.register(name)


# ---- 时间相关 ----


@_register("timestamp")
def _fn_timestamp() -> str:
    """返回当前 Unix 时间戳（秒）。"""
    return str(int(time.time()))


@_register("date")
def _fn_date() -> str:
    """返回当前日期，格式 YYYY-MM-DD。"""
    return datetime.now().strftime("%Y-%m-%d")


@_register("datetime")
def _fn_datetime() -> str:
    """返回当前日期时间，格式 YYYY-MM-DD HH:MM:SS。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@_register("utc_datetime")
def _fn_utc_datetime() -> str:
    """返回当前 UTC 日期时间。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---- 随机值 ----


@_register("random_int")
def _fn_random_int(*args: str) -> str:
    """返回随机整数。无参数默认 0-9999，1 个参数为上限，2 个参数为 [min, max]。"""
    if len(args) == 0:
        return str(random.randint(0, 9999))
    elif len(args) == 1:
        return str(random.randint(0, int(args[0].strip())))
    elif len(args) == 2:
        lo = int(args[0].strip())
        hi = int(args[1].strip())
        return str(random.randint(lo, hi))
    raise VariableError("random_int() 最多接受 2 个参数: random_int([min], [max])")


@_register("random_string")
def _fn_random_string(*args: str) -> str:
    """返回指定长度的随机字母数字字符串，默认长度 8。"""
    length = int(args[0].strip()) if args else 8
    if length <= 0 or length > 1000:
        raise VariableError(f"random_string() 长度必须在 1-1000 之间，得到 {length}")
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


@_register("uuid")
def _fn_uuid() -> str:
    """返回 UUID4 字符串。"""
    return str(_uuid_mod.uuid4())


# ---- 环境变量 ----


@_register("env")
def _fn_env(*args: str) -> str:
    """获取环境变量值。用法：env(VAR_NAME) 或 env(VAR_NAME, default_value)。"""
    if not args:
        raise VariableError("env() 至少需要 1 个参数: env(VAR_NAME[, default])")
    var_name = args[0].strip()
    default = args[1].strip() if len(args) > 1 else None
    value = os.environ.get(var_name, default)
    if value is None:
        raise VariableError(
            f"环境变量 '{var_name}' 未定义且未提供默认值"
        )
    return value


# ---- 数学计算 ----


@_register("calc")
def _fn_calc(*args: str) -> str:
    """安全的数学表达式计算。支持基础运算 +, -, *, /, %, **。"""
    if not args:
        raise VariableError("calc() 需要 1 个参数: calc(expression)")
    expr = ",".join(args).strip()  # 支持参数中含逗号的表达式

    # 安全检查：只允许数字、运算符、括号和空格
    allowed = re.compile(r"^[\d\s+\-*/%().eE]+$")
    if not allowed.match(expr):
        raise VariableError(
            f"calc() 表达式包含不允许的字符: '{expr}'"
        )

    # 提供安全的数学环境
    safe_globals: dict[str, Any] = {"__builtins__": {}}
    safe_locals = {
        "abs": abs,
        "round": round,
        "int": int,
        "float": float,
        "min": min,
        "max": max,
        "pow": pow,
        "math": math,
    }
    try:
        result = eval(expr, safe_globals, safe_locals)  # noqa: S307
    except Exception as e:
        raise VariableError(f"calc() 计算失败: '{expr}' -> {e}") from e
    # 如果是整数结果，返回不带小数点
    if isinstance(result, float) and result == int(result):
        return str(int(result))
    return str(result)


# ---------------------------------------------------------------------------
# 核心解析引擎
# ---------------------------------------------------------------------------


def _parse_args(args_str: str) -> list[str]:
    """解析函数参数字符串，支持简单的逗号分隔。"""
    if not args_str.strip():
        return []
    # 简单按逗号分隔（不处理嵌套括号内的逗号）
    return [a.strip() for a in args_str.split(",")]


def _resolve_expr(
    expr: str,
    variables: dict[str, str],
    custom_functions: dict[str, Callable[..., str]] | None = None,
) -> str:
    """解析单个 ${...} 内的表达式。"""
    expr = expr.strip()

    # 尝试匹配函数调用: func_name(args...)
    func_match = _FUNC_CALL_PATTERN.match(expr)
    if func_match:
        func_name = func_match.group(1)
        args_str = func_match.group(2)
        args = _parse_args(args_str)

        # 先在自定义函数中查找
        if custom_functions and func_name in custom_functions:
            try:
                return str(custom_functions[func_name](*args))
            except VariableError:
                raise
            except Exception as e:
                raise VariableError(
                    f"自定义函数 '{func_name}' 执行失败: {e}"
                ) from e

        # 再在内置函数中查找
        if func_name in _BUILTIN_FUNCTIONS:
            try:
                return str(_BUILTIN_FUNCTIONS[func_name](*args))
            except VariableError:
                raise
            except Exception as e:
                raise VariableError(
                    f"内置函数 '{func_name}' 执行失败: {e}"
                ) from e

        raise VariableError(
            f"未知函数 '{func_name}'，"
            f"可用内置函数: {', '.join(sorted(_BUILTIN_FUNCTIONS.keys()))}"
        )

    # 非函数调用 -> 变量引用（支持 data.field 格式）
    if expr in variables:
        return str(variables[expr])

    # 支持点号访问：检查 data.xxx / env.xxx 格式的变量
    if "." in expr:
        # 先尝试精确匹配（已在上面处理），再尝试前缀匹配
        parts = expr.split(".", 1)
        prefix = parts[0]
        # 检查是否有以该前缀开头的变量
        matching = [k for k in variables if k.startswith(f"{prefix}.")]
        if matching:
            # 给出更具体的错误信息
            raise VariableError(
                f"变量 '{expr}' 未定义。"
                f"可用的 '{prefix}.*' 变量: "
                f"{', '.join(sorted(matching))}"
            )
        # 特殊提示：env.xxx 格式但未激活环境
        if prefix == "env":
            raise VariableError(
                f"变量 '{expr}' 未定义。"
                f"可能未通过 --env 参数指定运行环境，"
                f"或该环境未定义对应变量。"
            )

    # 变量未定义
    raise VariableError(
        f"变量 '{expr}' 未定义。已定义的变量: "
        f"{', '.join(sorted(variables.keys())) if variables else '(无)'}"
    )


def resolve_text(
    text: str,
    variables: dict[str, str] | None = None,
    custom_functions: dict[str, Callable[..., str]] | None = None,
) -> str:
    """对文本中的所有 ${...} 表达式进行替换。

    Args:
        text: 包含 ${...} 表达式的原始文本。
        variables: 变量名到值的映射。
        custom_functions: 自定义函数名到可调用对象的映射。

    Returns:
        替换后的文本。

    Raises:
        VariableError: 变量未定义或函数执行失败。
    """
    if "${" not in text:
        return text

    vars_dict = variables or {}

    def _replacer(match: re.Match) -> str:
        expr = match.group(1)
        return _resolve_expr(expr, vars_dict, custom_functions)

    return _EXPR_PATTERN.sub(_replacer, text)


def resolve_variables_in_steps(
    steps_text: list[str],
    variables: dict[str, str] | None = None,
    custom_functions: dict[str, Callable[..., str]] | None = None,
) -> list[str]:
    """批量替换步骤列表中的变量和函数。"""
    return [resolve_text(s, variables, custom_functions) for s in steps_text]


def get_builtin_function_names() -> list[str]:
    """返回所有已注册的内置函数名列表。"""
    return _default_registry.available
