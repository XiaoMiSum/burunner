"""参数化变量和函数替换引擎（基于 Mako 模板）。

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
from datetime import datetime as _datetime_cls, timezone
from typing import Any, Callable

from mako.template import Template
from mako.exceptions import (
    CompileException,
    SyntaxException,
    TemplateLookupException,
)

from burunner.exceptions import ConfigurationError


class VariableError(ConfigurationError):
    """变量或函数解析错误。"""


# ---------------------------------------------------------------------------
# 内置函数注册表
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

    def register_function(self, name: str, func: Callable[..., str]) -> None:
        """直接注册函数到此注册表。"""
        self._functions[name] = func

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
    return _datetime_cls.now().strftime("%Y-%m-%d")


@_register("datetime")
def _fn_datetime() -> str:
    """返回当前日期时间，格式 YYYY-MM-DD HH:MM:SS。"""
    return _datetime_cls.now().strftime("%Y-%m-%d %H:%M:%S")


@_register("utc_datetime")
def _fn_utc_datetime() -> str:
    """返回当前 UTC 日期时间。"""
    return _datetime_cls.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---- 随机值 ----


@_register("random_int")
def _fn_random_int(*args) -> str:
    """返回随机整数。无参数默认 0-9999，1 个参数为上限，2 个参数为 [min, max]。"""
    if len(args) == 0:
        return str(random.randint(0, 9999))
    elif len(args) == 1:
        return str(random.randint(0, int(args[0])))
    elif len(args) == 2:
        lo = int(args[0])
        hi = int(args[1])
        return str(random.randint(lo, hi))
    raise VariableError("random_int() 最多接受 2 个参数: random_int([min], [max])")


@_register("random_string")
def _fn_random_string(*args) -> str:
    """返回指定长度的随机字母数字字符串，默认长度 8。"""
    length = int(args[0]) if args else 8
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
def _fn_env(*args) -> str:
    """获取环境变量值。用法：env(VAR_NAME) 或 env(VAR_NAME, default_value)。"""
    if not args:
        raise VariableError("env() 至少需要 1 个参数: env(VAR_NAME[, default])")
    var_name = str(args[0]).strip()
    default = str(args[1]).strip() if len(args) > 1 else None
    value = os.environ.get(var_name, default)
    if value is None:
        raise VariableError(
            f"环境变量 '{var_name}' 未定义且未提供默认值"
        )
    return value


# ---- 数学计算 ----


@_register("calc")
def _fn_calc(*args) -> str:
    """安全的数学表达式计算。支持基础运算 +, -, *, /, %, **。"""
    if not args:
        raise VariableError("calc() 需要 1 个参数: calc(expression)")
    expr = ",".join(str(a) for a in args).strip()

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
# Mako 模板安全沙箱
# ---------------------------------------------------------------------------

# 禁止在模板上下文中出现的危险名称
_FORBIDDEN_NAMES = frozenset({
    '__import__', '__builtins__', '__loader__', '__spec__',
    'eval', 'exec', 'compile', 'globals', 'locals',
    'getattr', 'setattr', 'delattr', 'hasattr',
    'open', 'input', 'breakpoint',
    '__subclasses__', '__bases__', '__class__',
})

# 匹配 ${...} 表达式内部的危险模式
_DANGEROUS_PATTERNS = re.compile(
    r'__\w+__'           # dunder 方法/属性
    r'|\b__import__\b'   # 显式 import
    r'|\bimport\b'       # import 语句
    r'|\beval\s*\('      # eval 调用
    r'|\bexec\s*\('      # exec 调用
    r'|\bopen\s*\('      # 文件操作
    r'|\bcompile\s*\('   # compile 调用
    r'|\bgetattr\s*\('   # getattr 调用
    r'|\bsetattr\s*\('   # setattr 调用
    r'|\bdelattr\s*\('   # delattr 调用
    r'|\bglobals\s*\('   # globals 调用
    r'|\blocals\s*\('    # locals 调用
    r'|\bbreakpoint\s*\('  # breakpoint 调用
)


def _validate_template_safety(text: str) -> None:
    """预检模板文本，拒绝明显的危险模式。

    只检查 ${...} 表达式内部的内容，对普通文本不做限制。

    Raises:
        VariableError: 检测到危险表达式时抛出。
    """
    for match in re.finditer(r'\$\{([^}]+)\}', text):
        expr = match.group(1)
        if _DANGEROUS_PATTERNS.search(expr):
            raise VariableError(
                f"不安全的模板表达式被拒绝: ${{{expr}}}。"
                f"模板表达式中不允许使用 import、eval、exec、open 等危险操作。"
            )


# ---------------------------------------------------------------------------
# Mako 模板渲染引擎
# ---------------------------------------------------------------------------

# 匹配 ${...} 模式，用于快速检测
_HAS_EXPR = re.compile(r"\$\{")

# 匹配 Mako 控制语法（不在 ${...} 内部）
_MAKO_BLOCK_TAG = re.compile(r"<%")


def _preprocess_for_mako(text: str) -> str:
    """预处理文本，转义 Mako 控制字符，保留 ${...} 表达式不受影响。

    处理的特殊字符：
    - <% (Mako 块/标签起始)
    - 行首 % (Mako 行级指令)
    """
    # 使用分段处理：将 ${...} 表达式与普通文本分开
    # 对普通文本部分进行 Mako 控制字符转义
    segments = []
    last_end = 0

    for match in re.finditer(r"\$\{[^}]*\}", text):
        # 转义 ${...} 之前的普通文本
        before = text[last_end:match.start()]
        if "<%" in before:
            before = before.replace("<%", "${'<%'}")
        segments.append(before)
        # 保留 ${...} 表达式原样
        segments.append(match.group(0))
        last_end = match.end()

    # 处理最后一段普通文本
    remaining = text[last_end:]
    if "<%" in remaining:
        remaining = remaining.replace("<%", "${'<%'}")
    segments.append(remaining)

    result = "".join(segments)

    # 处理行首 % (Mako 行级指令)
    lines = result.split("\n")
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("%") and not stripped.startswith("${"):
            # 在 % 前插入空表达式来阻止 Mako 将其解析为指令
            indent = len(line) - len(stripped)
            lines[i] = line[:indent] + "${''}" + stripped
    return "\n".join(lines)


def _build_mako_context(
    variables: dict[str, Any],
    custom_functions: dict[str, Callable] | None = None,
) -> dict[str, Any]:
    """构建安全的 Mako 模板渲染上下文，阻止危险操作。

    合并变量 + 内置函数 + 自定义函数，并清除危险的内置名称。
    """
    context: dict[str, Any] = {}

    # 1. 注入内置函数
    context.update(_BUILTIN_FUNCTIONS)

    # 2. 注入自定义函数（可覆盖同名内置函数）
    if custom_functions:
        context.update(custom_functions)

    # 3. 注入变量（变量优先级最高，可覆盖同名函数）
    context.update(variables)

    # 4. 安全沙箱：清空 __builtins__，阻止所有未显式注入的内置函数
    context['__builtins__'] = {}

    # 5. 确保禁止的危险名称不可访问（不覆盖已注册的合法函数/变量）
    for name in _FORBIDDEN_NAMES:
        if name not in context or name == '__builtins__':
            context[name] = None

    return context


def resolve_text(
    text: str,
    variables: dict[str, Any] | None = None,
    custom_functions: dict[str, Callable] | None = None,
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
    # 性能优化：纯文本直接返回
    if "${" not in text:
        return text

    # 安全预检：拒绝明显的危险模式
    _validate_template_safety(text)

    vars_dict = variables or {}
    context = _build_mako_context(vars_dict, custom_functions)

    # 预处理 Mako 控制字符
    processed_text = _preprocess_for_mako(text)

    try:
        template = Template(processed_text, strict_undefined=True)
        return template.render(**context)
    except NameError as e:
        # 未定义变量
        raise VariableError(
            f"变量解析失败: {e}。已定义的变量: "
            f"{', '.join(sorted(vars_dict.keys())) if vars_dict else '(无)'}"
        ) from e
    except (CompileException, SyntaxException) as e:
        raise VariableError(f"模板编译失败: {e}") from e
    except TemplateLookupException as e:
        raise VariableError(f"模板查找失败: {e}") from e
    except VariableError:
        # 内置函数抛出的 VariableError 直接透传
        raise
    except Exception as e:
        # 捕获 Mako 渲染中的其他异常（包括函数执行错误）
        # Mako 将异常包装，尝试提取原始异常信息
        original = getattr(e, "__cause__", None) or e
        if isinstance(original, VariableError):
            raise original
        raise VariableError(f"变量/函数解析失败: {original}") from e


def resolve_variables_in_steps(
    steps_text: list[str],
    variables: dict[str, Any] | None = None,
    custom_functions: dict[str, Callable] | None = None,
) -> list[str]:
    """批量替换步骤列表中的变量和函数。"""
    return [resolve_text(s, variables, custom_functions) for s in steps_text]


def get_builtin_function_names() -> list[str]:
    """返回所有已注册的内置函数名列表。"""
    return _default_registry.available
