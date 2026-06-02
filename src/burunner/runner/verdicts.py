"""结果判定模块 - 从 Agent 执行结果中确定用例状态。"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from burunner.runner.history_parser import HistoryParser

from burunner.runner.result import CaseStatus

logger = logging.getLogger("burunner.verdicts")

_JSON_VERDICT_RE = re.compile(
    r"\{[^{}]*?\"success\"\s*:\s*(true|false)[^{}]*?\}", re.IGNORECASE
)


class VerdictJudge:
    """负责从 Agent 执行结果判定用例最终状态。"""

    def judge(
        self,
        parsed: HistoryParser,
        max_steps: int,
        error_occurred: bool = False,
        error_message: str | None = None,
    ) -> tuple[CaseStatus, str | None]:
        """判定用例执行结果。

        返回: (status, error_message)

        判定优先级：
        1. 若 error_occurred → ERROR
        2. 若 parsed.total_steps >= max_steps → INCOMPLETE
        3. 若 Agent 输出包含 {"success": true} → PASSED
        4. 若 Agent 输出包含 {"success": false} → FAILED
        5. 若 parsed.is_done == True 且无明确结果 → FAILED（保守策略）
        6. 若 parsed.is_done == False → INCOMPLETE
        """
        if error_occurred:
            return CaseStatus.ERROR, error_message

        if parsed.total_steps >= max_steps:
            return CaseStatus.INCOMPLETE, f"执行未完成：已达最大步骤数 {max_steps}"

        final_text = parsed.final_result_text
        verdict_success, verdict_reason = self._parse_verdict(final_text)

        if verdict_success is True:
            return CaseStatus.PASSED, None
        elif verdict_success is False:
            return CaseStatus.FAILED, verdict_reason or "Agent 报告测试失败"
        elif parsed.is_done:
            return CaseStatus.FAILED, "无法从 Agent 输出中判定测试结论"
        else:
            return CaseStatus.INCOMPLETE, "Agent 未正常结束执行"

    def _parse_verdict(self, text: str | None) -> tuple[bool | None, str | None]:
        """从 Agent 最终输出中解析 {"success":..., "reason":...}。

        返回 (success, reason)；解析失败时 success=None 表示需要回退到其他判定方式。
        """
        if not text:
            return None, None
        # JSON 匹配
        lower = text.strip()
        m = _JSON_VERDICT_RE.search(lower)
        if m:
            try:
                payload = json.loads(m.group(0))
                success = bool(payload.get("success"))
                reason = payload.get("reason")
                return success, str(reason) if reason is not None else None
            except (json.JSONDecodeError, AttributeError):
                pass
        # 中文关键词兜底
        if "测试失败" in text or "失败" in text and "成功" not in text:
            return False, text.strip()[:300]
        if "测试成功" in text:
            return True, None
        return None, None
