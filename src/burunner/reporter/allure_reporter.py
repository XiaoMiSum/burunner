"""Allure 报告写入 —— 直接使用 allure-python-commons lifecycle，不依赖 pytest。"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from burunner.reporter.base import BaseReporter
from burunner.runner.result import CaseResult, CaseStatus

logger = logging.getLogger("burunner.allure")


def _safe_import() -> tuple[Any, Any, Any]:
    """动态导入 allure_commons 并返回 (lifecycle, model2, file_logger_cls)。"""
    from allure_commons.lifecycle import AllureLifecycle  # type: ignore
    from allure_commons import model2  # type: ignore
    try:
        from allure_commons.logger import AllureFileLogger  # type: ignore
    except ImportError:
        # 部分版本下放在 allure_commons.reporter
        from allure_commons.reporter import AllureFileLogger  # type: ignore
    return AllureLifecycle, model2, AllureFileLogger


_STATUS_MAP_NAME = {
    CaseStatus.PASSED: "passed",
    CaseStatus.FAILED: "failed",
    CaseStatus.ERROR: "broken",
    CaseStatus.SKIPPED: "skipped",
    CaseStatus.INCOMPLETE: "broken",
}


class AllureReporter(BaseReporter):
    """将 CaseResult 序列化为 allure-results 目录下的 JSON。

    每条用例生成一个 *-result.json，并在失败/异常时附加截图与 Agent 输出。
    HTML 由用户运行 `allure generate` 或 `allure serve` 产出。
    """

    def __init__(self, results_dir: Path):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        AllureLifecycle, model2, AllureFileLogger = _safe_import()
        self._model2 = model2
        self._lifecycle = AllureLifecycle()
        self._file_logger = AllureFileLogger(str(self.results_dir))
        # plugin_manager hook 注册（兼容多个 allure_commons 版本）
        try:
            from allure_commons import plugin_manager  # type: ignore
            plugin_manager.register(self._file_logger)
        except Exception as e:  # noqa: BLE001
            logger.debug("plugin_manager 注册失败，回退手动写入: %s", e)
            self._file_logger = None

        self._status_cls = getattr(model2, "Status")
        self._status_details_cls = getattr(model2, "StatusDetails")
        self._label_cls = getattr(model2, "Label")
        self._param_cls = getattr(model2, "Parameter")
        self._attach_cls = getattr(model2, "Attachment")

    # ---------- lifecycle ----------
    def start_suite(self, suite_name: str) -> None:  # noqa: D102
        pass

    def finish(self) -> None:  # noqa: D102
        pass

    # ---------- helpers ----------
    def _status(self, name: str) -> Any:
        return getattr(self._status_cls, name, name)

    def _label(self, name: str, value: str) -> Any:
        return self._label_cls(name=name, value=value)

    def _param(self, name: str, value: Any) -> Any:
        return self._param_cls(name=name, value=str(value))

    def _attach_text(self, name: str, content: str) -> Any:
        att_uuid = uuid.uuid4().hex
        filename = f"{att_uuid}-attachment.txt"
        target = self.results_dir / filename
        target.write_text(content, encoding="utf-8")
        return self._attach_cls(name=name, source=filename, type="text/plain")

    def _attach_file(self, name: str, src: Path, mime: str) -> Any:
        att_uuid = uuid.uuid4().hex
        ext = src.suffix or ""
        filename = f"{att_uuid}-attachment{ext}"
        target = self.results_dir / filename
        target.write_bytes(src.read_bytes())
        return self._attach_cls(name=name, source=filename, type=mime)

    # ---------- public ----------
    def write_case(self, result: CaseResult, *, provider: str, model: str) -> None:
        case = result.case
        status_name = _STATUS_MAP_NAME[result.status]
        status = self._status(status_name)

        labels = [
            self._label("framework", "burunner"),
            self._label("language", "python"),
        ]
        suite_name = case.source_file.stem if case.source_file else "burunner"
        labels.append(self._label("suite", suite_name))
        labels.append(self._label("parentSuite", "burunner"))
        for tag in case.tags:
            labels.append(self._label("tag", tag))

        parameters = [
            self._param("provider", provider),
            self._param("model", model),
            self._param("elapsed_seconds", f"{result.elapsed:.2f}"),
            self._param("input_tokens", result.tokens.input_tokens),
            self._param("output_tokens", result.tokens.output_tokens),
            self._param("total_tokens", result.tokens.total),
        ]
        if case.source_file:
            parameters.append(self._param(
                "source_file", str(case.source_file)))

        # 构造 step 列表（自然语言每步一条）
        steps = []
        StepResult = getattr(self._model2, "TestStepResult", None) or getattr(
            self._model2, "StepResult"
        )
        if result.step_outcomes:
            # 使用真实步骤级数据
            for outcome in result.step_outcomes:
                if outcome.status == "PASSED":
                    step_status = self._status("passed")
                elif outcome.status == "FAILED":
                    step_status = self._status("failed")
                else:
                    step_status = self._status("broken")
                step = StepResult(
                    name=f"{outcome.step_index + 1}. {outcome.step_text}",
                    status=step_status,
                    start=int(
                        outcome.started_at * 1000) if outcome.started_at else int(result.started_at),
                    stop=int(
                        outcome.stopped_at * 1000) if outcome.stopped_at else int(result.stopped_at),
                )
                steps.append(step)
        else:
            # 回退逻辑：所有步骤共享 case 的最终状态
            for idx, s in enumerate(case.steps):
                step_status = self._status("passed")
                if status_name in ("failed", "broken") and idx == len(case.steps) - 1:
                    step_status = status
                step = StepResult(
                    name=f"{idx + 1}. {s.text}",
                    status=step_status,
                    start=int(result.started_at),
                    stop=int(result.stopped_at),
                )
                steps.append(step)

        attachments = []
        if result.final_result:
            attachments.append(
                self._attach_text("Agent final result", result.final_result)
            )
        if result.error_trace:
            attachments.append(
                self._attach_text("Traceback", result.error_trace)
            )
        if result.screenshot_path and result.screenshot_path.is_file():
            attachments.append(
                self._attach_file(
                    "Failure screenshot",
                    result.screenshot_path,
                    "image/png",
                )
            )

        status_details = None
        if result.error_message:
            status_details = self._status_details_cls(
                message=result.error_message,
                trace=result.error_trace or "",
            )

        Stage = getattr(self._model2, "Stage", None)
        stage_value = getattr(
            Stage, "FINISHED", "finished") if Stage else "finished"

        TestResult = getattr(self._model2, "TestResult")
        tr = TestResult(
            uuid=uuid.uuid4().hex,
            name=case.name,
            fullName=f"{suite_name}::{case.name}",
            historyId=f"{suite_name}::{case.name}",
            testCaseId=f"{suite_name}::{case.name}",
            description=case.description or "",
            status=status,
            statusDetails=status_details,
            stage=stage_value,
            start=int(result.started_at),
            stop=int(result.stopped_at),
            labels=labels,
            parameters=parameters,
            steps=steps,
            attachments=attachments,
        )

        # 通过 file_logger 写出（标准方式）
        if self._file_logger is not None:
            try:
                self._file_logger.report_result(tr)
                return
            except Exception as e:  # noqa: BLE001
                logger.debug(
                    "AllureFileLogger.report_result 失败 (%s)，回退手写 JSON", e)

        # 回退：直接以 dict 形式手写 JSON
        self._fallback_write(tr)

    def _fallback_write(self, tr: Any) -> None:
        try:
            payload = tr.to_dict()  # type: ignore[attr-defined]
        except AttributeError:
            payload = self._serialize(tr)
        target = self.results_dir / f"{tr.uuid}-result.json"
        target.write_text(json.dumps(payload, ensure_ascii=False,
                          default=self._serialize), encoding="utf-8")

    @staticmethod
    def _serialize(obj: Any) -> Any:
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_") and v is not None}
        return str(obj)

    def write_environment(self, env: dict[str, str]) -> None:
        """写入 environment.properties，便于 Allure 报告展示。"""
        if not env:
            return
        path = self.results_dir / "environment.properties"
        with path.open("w", encoding="utf-8") as fh:
            for k, v in env.items():
                fh.write(f"{k}={v}{os.linesep}")
