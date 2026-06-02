"""统一封装 browser-use Agent history 对象的解析逻辑。

将 history 对象的各种兼容性处理集中在此，屏蔽不同 browser-use 版本的差异。
"""

from __future__ import annotations

import logging
from typing import Any

from burunner.utils.tokens import TokenUsage, usage_from_history

logger = logging.getLogger("burunner.history_parser")


class HistoryParser:
    """统一封装 browser-use Agent history 对象的解析逻辑。

    支持不同版本 browser-use 返回的 history 对象结构差异，
    提供统一的属性访问接口。
    """

    def __init__(self, history: Any):
        self._history = history

    @property
    def raw(self) -> Any:
        """原始 history 对象。"""
        return self._history

    @property
    def final_result_text(self) -> str | None:
        """获取 Agent 最终输出文本。

        尝试顺序：
        1. history.final_result() 方法
        2. history.history[-1].result / output / model_output 属性
        """
        if self._history is None:
            return None

        # 方式 1: final_result() 方法
        fn = getattr(self._history, "final_result", None)
        if callable(fn):
            try:
                v = fn()
                if isinstance(v, str):
                    return v
                if v is not None:
                    return str(v)
            except Exception:  # noqa: BLE001
                logger.debug("调用 history.final_result() 失败", exc_info=True)

        # 方式 2: 取 history 最后一项的输出属性
        inner = getattr(self._history, "history", None)
        if isinstance(inner, list) and inner:
            last = inner[-1]
            for attr in ("result", "output", "model_output"):
                v = getattr(last, attr, None)
                if isinstance(v, str):
                    return v
                if v is not None:
                    return str(v)

        logger.debug("无法从 history 对象中提取最终输出文本")
        return None

    @property
    def is_done(self) -> bool:
        """Agent 是否正常结束（调用了 done()）。

        尝试顺序：
        1. history.is_done() 方法（如果存在）
        2. history.is_successful() 方法返回值不为 None
        3. 检查最后一步是否有 done action
        """
        if self._history is None:
            return False

        # 方式 1: is_done() 方法
        fn = getattr(self._history, "is_done", None)
        if callable(fn):
            try:
                v = fn()
                if isinstance(v, bool):
                    return v
            except Exception:  # noqa: BLE001
                logger.debug("调用 history.is_done() 失败", exc_info=True)

        # 方式 2: is_successful() 返回非 None 值说明 Agent 正常结束
        fn = getattr(self._history, "is_successful", None)
        if callable(fn):
            try:
                v = fn()
                if v is not None:
                    return True
            except Exception:  # noqa: BLE001
                pass

        # 方式 3: 检查最后一步是否有 done action
        inner = getattr(self._history, "history", None)
        if isinstance(inner, list) and inner:
            last = inner[-1]
            # 检查 action 属性（部分版本使用 action.name == "done"）
            action = getattr(last, "action", None)
            if action is not None:
                action_name = getattr(action, "name", None) or getattr(
                    action, "type", None)
                if action_name == "done":
                    return True
                # 某些版本 action 是 dict
                if isinstance(action, dict) and action.get("name") == "done":
                    return True
            # 检查 actions 列表
            actions = getattr(last, "actions", None)
            if isinstance(actions, list):
                for a in actions:
                    a_name = getattr(a, "name", None) or getattr(
                        a, "type", None)
                    if a_name == "done":
                        return True
                    if isinstance(a, dict) and a.get("name") == "done":
                        return True

        return False

    @property
    def is_successful(self) -> bool | None:
        """Agent 自我评估是否成功。

        尝试：history.is_successful() 方法
        返回 None 表示无法判断。
        """
        if self._history is None:
            return None

        fn = getattr(self._history, "is_successful", None)
        if callable(fn):
            try:
                v = fn()
                if isinstance(v, bool):
                    return v
            except Exception:  # noqa: BLE001
                logger.debug("调用 history.is_successful() 失败", exc_info=True)

        return None

    @property
    def total_steps(self) -> int:
        """实际执行的步骤数。

        尝试：
        1. len(history.history) 如果存在
        2. history.n_steps 属性
        3. 默认返回 0
        """
        if self._history is None:
            return 0

        # 方式 1: len(history.history)
        inner = getattr(self._history, "history", None)
        if isinstance(inner, list):
            return len(inner)

        # 方式 2: n_steps 属性
        n = getattr(self._history, "n_steps", None)
        if isinstance(n, int):
            return n

        return 0

    @property
    def token_usage(self) -> TokenUsage:
        """聚合 token 用量。

        兼容三种形态：
        1. history.usage (TokenSummary, 0.12+)
        2. 平铺属性 history.input_tokens / output_tokens
        3. history.history[*].metadata 中的 token 信息累加
        """
        return usage_from_history(self._history)
