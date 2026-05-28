"""Token 用量统计 —— 兼容 browser-use 不同版本暴露形式。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


def _extract_int(obj: Any, *names: str) -> int | None:
    for n in names:
        v = getattr(obj, n, None)
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(obj, dict) and n in obj and isinstance(obj[n], (int, float)):
            return int(obj[n])
    return None


def usage_from_history(history: Any) -> TokenUsage:
    """从 browser-use 的 AgentHistoryList 聚合 token 用量。

    兼容三种形态:
    1. history.usage (TokenSummary, 0.12+)
    2. history.total_input_tokens / total_output_tokens
    3. 遍历 history.history[*].metadata.{input_tokens,output_tokens}
    """
    if history is None:
        return TokenUsage()

    # 形态 1: history.usage
    usage = getattr(history, "usage", None)
    if usage is not None:
        in_tok = _extract_int(usage, "total_prompt_tokens", "prompt_tokens", "input_tokens")
        out_tok = _extract_int(usage, "total_completion_tokens", "completion_tokens", "output_tokens")
        if in_tok is not None or out_tok is not None:
            return TokenUsage(input_tokens=in_tok or 0, output_tokens=out_tok or 0)

    # 形态 2: 平铺属性
    in_tok = _extract_int(history, "total_input_tokens", "input_tokens", "prompt_tokens")
    out_tok = _extract_int(history, "total_output_tokens", "output_tokens", "completion_tokens")
    if in_tok is not None or out_tok is not None:
        return TokenUsage(input_tokens=in_tok or 0, output_tokens=out_tok or 0)

    # 形态 3: 遍历 history.history
    inner = getattr(history, "history", None)
    if isinstance(inner, list):
        total_in = 0
        total_out = 0
        for item in inner:
            md = getattr(item, "metadata", None) or item
            i = _extract_int(md, "input_tokens", "prompt_tokens") or 0
            o = _extract_int(md, "output_tokens", "completion_tokens") or 0
            total_in += i
            total_out += o
        if total_in or total_out:
            return TokenUsage(input_tokens=total_in, output_tokens=total_out)

    return TokenUsage()
