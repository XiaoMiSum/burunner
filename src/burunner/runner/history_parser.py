"""统一封装 browser-use Agent history 对象的解析逻辑。

将 history 对象的各种兼容性处理集中在此，屏蔽不同 browser-use 版本的差异。
"""

from __future__ import annotations

import logging
from typing import Any

from burunner.utils.metrics import TokenUsage, usage_from_history

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

    # ---------- Step Outcomes ----------

    def extract_step_outcomes(self, case: Any) -> list:
        """将 Agent 迭代映射回用户定义的 TestStep，提取每步的执行结果。

        映射策略：
        - 主路径：使用 AgentOutput.current_plan_item 分组
        - 回退：current_plan_item 不可用时，按比例均匀分配
        """
        from burunner.runner.result import StepOutcome

        steps = getattr(case, "steps", None) or []
        if not steps:
            return []

        history_items = self._get_history_list()
        if not history_items:
            # 无执行历史，所有步骤标记 UNKNOWN
            return [
                StepOutcome(step_index=i, step_text=s.text, status="UNKNOWN")
                for i, s in enumerate(steps)
            ]

        # 分组：将 Agent 迭代按 step_index 归组
        groups = self._group_iterations_by_step(history_items, len(steps))

        # 聚合：为每组生成 StepOutcome
        outcomes = []
        for idx, s in enumerate(steps):
            group = groups.get(idx, [])
            outcome = self._aggregate_group(idx, s.text, group)
            outcomes.append(outcome)

        return outcomes

    def _get_history_list(self) -> list:
        """安全获取 history.history 列表（兼容不同版本）。"""
        if self._history is None:
            return []
        inner = getattr(self._history, "history", None)
        if callable(inner):
            try:
                inner = inner()
            except Exception:  # noqa: BLE001
                return []
        if isinstance(inner, list):
            return inner
        return []

    def _group_iterations_by_step(
        self, history_items: list, num_steps: int
    ) -> dict[int, list]:
        """将 Agent 迭代按 step_index 归组。

        优先使用 model_output.current_plan_item，
        不可用时按比例均匀分配。
        """
        groups: dict[int, list] = {}
        plan_items: list[int | None] = []

        for item in history_items:
            plan_idx = self._extract_plan_item(item)
            plan_items.append(plan_idx)

        # 判断是否大部分 iteration 有 current_plan_item
        valid_count = sum(1 for p in plan_items if p is not None)
        use_plan = valid_count > len(plan_items) * 0.5

        if use_plan and num_steps > 0:
            # 检测 0-based vs 1-based
            max_val = max((p for p in plan_items if p is not None), default=0)
            is_one_based = max_val == num_steps  # 如果最大值 == num_steps，则为 1-based

            for i, item in enumerate(history_items):
                idx = plan_items[i]
                if idx is None:
                    # 未标记的归入最后一步
                    step_idx = num_steps - 1
                else:
                    step_idx = (idx - 1) if is_one_based else idx
                # 超出范围的归入最后一步
                if step_idx < 0 or step_idx >= num_steps:
                    step_idx = num_steps - 1
                groups.setdefault(step_idx, []).append(item)
        else:
            # 按比例均匀分配
            if num_steps > 0:
                per_step = max(len(history_items) / num_steps, 1)
                for i, item in enumerate(history_items):
                    step_idx = min(int(i / per_step), num_steps - 1)
                    groups.setdefault(step_idx, []).append(item)

        return groups

    def _extract_plan_item(self, item: Any) -> int | None:
        """从单个 history item 中提取 current_plan_item。"""
        try:
            model_output = getattr(item, "model_output", None)
            if model_output is None:
                return None
            plan_item = getattr(model_output, "current_plan_item", None)
            if plan_item is None:
                # 某些版本可能叫 current_state.next_step_index
                current_state = getattr(model_output, "current_state", None)
                if current_state is not None:
                    plan_item = getattr(current_state, "next_step_index", None)
            if isinstance(plan_item, int):
                return plan_item
        except Exception:  # noqa: BLE001
            pass
        return None

    def _aggregate_group(
        self, step_index: int, step_text: str, iterations: list
    ) -> Any:
        """从 iterations 中提取时间、错误、动作等信息，生成 StepOutcome。"""
        from burunner.runner.result import StepOutcome

        if not iterations:
            return StepOutcome(
                step_index=step_index, step_text=step_text, status="UNKNOWN"
            )

        errors: list[str] = []
        actions: list[str] = []
        started_at = 0.0
        stopped_at = 0.0
        url: str | None = None
        has_done_fail = False

        for item in iterations:
            # 提取时间信息
            try:
                metadata = getattr(item, "metadata", None)
                if metadata is not None:
                    t_start = getattr(metadata, "start_time", None) or getattr(
                        metadata, "started_at", None
                    )
                    t_end = getattr(metadata, "end_time", None) or getattr(
                        metadata, "stopped_at", None
                    )
                    if t_start and (started_at == 0.0 or t_start < started_at):
                        started_at = float(t_start)
                    if t_end and t_end > stopped_at:
                        stopped_at = float(t_end)
            except Exception:  # noqa: BLE001
                pass

            # 提取错误信息
            try:
                errs = getattr(item, "errors", None)
                if isinstance(errs, list):
                    for e in errs:
                        if e:
                            errors.append(str(e))
                elif isinstance(errs, str) and errs:
                    errors.append(errs)
                # 部分版本使用 error 字段（单数）
                err_single = getattr(item, "error", None)
                if isinstance(err_single, str) and err_single:
                    errors.append(err_single)
            except Exception:  # noqa: BLE001
                pass

            # 提取动作名称
            try:
                model_output = getattr(item, "model_output", None)
                if model_output is not None:
                    item_actions = getattr(model_output, "actions", None)
                    if isinstance(item_actions, list):
                        for a in item_actions:
                            a_name = None
                            if isinstance(a, dict):
                                a_name = a.get("name") or a.get("type")
                            else:
                                a_name = getattr(a, "name", None) or getattr(
                                    a, "type", None
                                )
                            if a_name:
                                actions.append(str(a_name))
            except Exception:  # noqa: BLE001
                pass

            # 提取 URL
            try:
                state = getattr(item, "state", None)
                if state is not None:
                    item_url = getattr(state, "url", None)
                    if isinstance(item_url, str) and item_url:
                        url = item_url
            except Exception:  # noqa: BLE001
                pass

            # 检查 done(success=false)
            try:
                result_list = getattr(item, "result", None)
                if isinstance(result_list, list):
                    for r in result_list:
                        is_done = getattr(r, "is_done", None)
                        if is_done:
                            success = getattr(r, "success", None)
                            if success is False:
                                has_done_fail = True
                elif result_list is not None:
                    is_done = getattr(result_list, "is_done", None)
                    if is_done:
                        success = getattr(result_list, "success", None)
                        if success is False:
                            has_done_fail = True
            except Exception:  # noqa: BLE001
                pass

        # 判定状态
        if has_done_fail:
            status = "FAILED"
        elif errors:
            # 有错误且无后续成功动作 → FAILED
            status = "FAILED"
        else:
            status = "PASSED"

        duration = (stopped_at - started_at) if (
            stopped_at > 0 and started_at > 0
        ) else 0.0

        return StepOutcome(
            step_index=step_index,
            step_text=step_text,
            status=status,
            duration=duration,
            started_at=started_at,
            stopped_at=stopped_at,
            iterations=len(iterations),
            errors=errors,
            actions=actions,
            url=url,
        )
