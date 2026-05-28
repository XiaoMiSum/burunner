"""burunner 统一异常体系。

所有 burunner 自定义异常都应继承 BurunnerError，
按可恢复性分为 ConfigurationError（不可恢复）和 ExecutionError（运行时）两大分支。
"""


class BurunnerError(Exception):
    """burunner 基础异常，所有自定义异常的根类。"""


# ---------------------------------------------------------------------------
# 配置类错误（不可恢复）
# ---------------------------------------------------------------------------


class ConfigurationError(BurunnerError):
    """配置错误（不可恢复）。如 YAML 解析失败、无效配置值。"""


# ---------------------------------------------------------------------------
# 执行类错误
# ---------------------------------------------------------------------------


class ExecutionError(BurunnerError):
    """执行错误基类。"""


class TransientError(ExecutionError):
    """临时错误（可重试）。如网络超时、浏览器临时无响应。"""


class PermanentError(ExecutionError):
    """永久错误（不应重试）。如断言失败、业务逻辑错误。"""


class BrowserError(TransientError):
    """浏览器相关错误（通常可重试）。"""


class LLMError(TransientError):
    """LLM 调用错误（通常可重试）。"""
