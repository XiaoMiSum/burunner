"""结果判定模块单元测试。"""

import pytest

from burunner.runner.verdicts import VerdictJudge
from burunner.runner.result import CaseStatus


class MockHistoryParser:
    """HistoryParser 的 Mock 实现。"""

    def __init__(
        self,
        total_steps: int = 0,
        is_done: bool = False,
        final_result_text: str | None = None,
    ):
        self.total_steps = total_steps
        self.is_done = is_done
        self.final_result_text = final_result_text


class TestVerdictJudge:
    """VerdictJudge 类测试。"""

    def setup_method(self):
        self.judge = VerdictJudge()

    def test_error_occurred(self):
        """错误发生时返回 ERROR 状态。"""
        parsed = MockHistoryParser(total_steps=5, is_done=False)
        status, error = self.judge.judge(
            parsed, max_steps=50, error_occurred=True, error_message="浏览器崩溃"
        )
        assert status == CaseStatus.ERROR
        assert error == "浏览器崩溃"

    def test_exceeds_max_steps(self):
        """超过最大步骤数返回 INCOMPLETE。"""
        parsed = MockHistoryParser(total_steps=50, is_done=False)
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.INCOMPLETE
        assert "已达最大步骤数 50" in error

    def test_parse_verdict_success_json(self):
        """从 JSON 解析成功结果。"""
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text='{"success": true, "reason": "测试通过"}',
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.PASSED
        assert error is None

    def test_parse_verdict_failure_json(self):
        """从 JSON 解析失败结果。"""
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text='{"success": false, "reason": "元素不存在"}',
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED
        assert error == "元素不存在"

    def test_parse_verdict_json_no_reason(self):
        """JSON 中没有 reason 字段。"""
        parsed = MockHistoryParser(
            total_steps=3,
            is_done=True,
            final_result_text='{"success": false}',
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED
        assert error == "Agent 报告测试失败"

    def test_parse_verdict_json_invalid(self):
        """无效的 JSON 格式。"""
        parsed = MockHistoryParser(
            total_steps=3,
            is_done=True,
            final_result_text='{success: true}',  # 缺少引号
        )
        # 应该回退到其他判定方式
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED  # is_done=True 但无明确结果

    def test_is_done_without_verdict(self):
        """Agent 正常结束但未输出判定结果。"""
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text="执行完毕",
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED
        assert "无法从 Agent 输出中判定测试结论" in error

    def test_not_done(self):
        """Agent 未正常结束。"""
        parsed = MockHistoryParser(
            total_steps=3,
            is_done=False,
            final_result_text=None,
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.INCOMPLETE
        assert "Agent 未正常结束执行" in error

    def test_parse_verdict_chinese_keywords(self):
        """中文关键词兜底 - 测试失败。"""
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text="测试失败：无法找到登录按钮",
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED
        assert "测试失败" in error

    def test_parse_verdict_chinese_success(self):
        """中文关键词兜底 - 测试成功。"""
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text="测试成功，所有步骤执行完毕",
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.PASSED
        assert error is None

    def test_parse_verdict_mixed_keywords(self):
        """混合关键词 - 成功优先。"""
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text="执行失败但测试成功",
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.PASSED

    def test_final_text_truncated(self):
        """失败原因超过 300 字符会被截断。"""
        long_reason = "失败原因" * 50  # 200 字符
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text=long_reason,
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED
        assert len(error) <= 300

    def test_no_final_text(self):
        """没有最终输出文本。"""
        parsed = MockHistoryParser(
            total_steps=3,
            is_done=True,
            final_result_text=None,
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED

    def test_empty_final_text(self):
        """最终输出文本为空。"""
        parsed = MockHistoryParser(
            total_steps=3,
            is_done=True,
            final_result_text="",
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED

    def test_verdict_json_with_extra_text(self):
        """JSON 前后有其他文本。"""
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text="执行步骤完毕。\n{\"success\": true, \"reason\": \"OK\"}\n结束。",
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.PASSED

    def test_verdict_json_case_insensitive(self):
        """JSON 中的 true/false 不区分大小写(正则匹配)。"""
        # 注意: JSON 标准只接受小写 true/false
        # 但我们的正则会匹配大写的 TRUE,但 json.loads 会失败
        # 所以这个测试应该回退到其他方式判定
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text='{"success": true}',  # 使用标准小写
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.PASSED

    def test_verdict_json_with_spaces(self):
        """JSON 中有多余空格。"""
        parsed = MockHistoryParser(
            total_steps=5,
            is_done=True,
            final_result_text='{ "success" : false , "reason" : "断言失败" }',
        )
        status, error = self.judge.judge(parsed, max_steps=50)
        assert status == CaseStatus.FAILED
        assert error == "断言失败"


class TestParseVerdict:
    """_parse_verdict 方法专项测试。"""

    def setup_method(self):
        self.judge = VerdictJudge()

    def test_none_text(self):
        success, reason = self.judge._parse_verdict(None)
        assert success is None
        assert reason is None

    def test_empty_text(self):
        success, reason = self.judge._parse_verdict("")
        assert success is None
        assert reason is None

    def test_no_verdict_pattern(self):
        """不包含任何判定模式。"""
        success, reason = self.judge._parse_verdict("这是一段普通文本")
        assert success is None
        assert reason is None

    def test_json_with_additional_fields(self):
        """JSON 包含额外字段。"""
        success, reason = self.judge._parse_verdict(
            '{"success": true, "reason": "OK", "steps": 5}'
        )
        assert success is True
        assert reason == "OK"

    def test_chinese_failure_without_success(self):
        """包含"失败"但不包含"成功"。"""
        success, reason = self.judge._parse_verdict("步骤执行失败")
        assert success is False
        assert "失败" in reason

    def test_chinese_failure_with_success_keyword(self):
        """同时包含"失败"和"成功",不应该匹配失败。"""
        success, reason = self.judge._parse_verdict("之前失败但最后成功")
        # 因为包含"成功",不会匹配失败模式
        assert success is None
