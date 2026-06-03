"""历史解析器模块单元测试。"""

from burunner.runner.result import StepOutcome
from burunner.parser.models import TestCase, TestStep
import pytest

from burunner.runner.history_parser import HistoryParser
from burunner.utils.metrics import TokenUsage


class TestHistoryParserFinalResult:
    """final_result_text 属性测试。"""

    def test_none_history(self):
        parser = HistoryParser(None)
        assert parser.final_result_text is None

    def test_final_result_method(self):
        """通过 final_result() 方法获取。"""

        class HistoryObj:
            def final_result(self_):
                return "测试完成"

        parser = HistoryParser(HistoryObj())
        assert parser.final_result_text == "测试完成"

    def test_final_result_method_non_string(self):
        """final_result() 返回非字符串。"""

        class HistoryObj:
            def final_result(self_):
                return 123

        parser = HistoryParser(HistoryObj())
        assert parser.final_result_text == "123"

    def test_final_result_method_exception(self):
        """final_result() 抛出异常。"""

        class HistoryObj:
            def final_result(self_):
                raise RuntimeError("失败")

        parser = HistoryParser(HistoryObj())
        # 应该回退到其他方法
        assert parser.final_result_text is None

    def test_from_history_list_last_item(self):
        """从 history 列表最后一项获取结果。"""

        class LastItem:
            result = "最终结果"

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.final_result_text == "最终结果"

    def test_from_history_list_output_attr(self):
        """从 output 属性获取。"""

        class LastItem:
            output = "输出内容"

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.final_result_text == "输出内容"

    def test_from_history_list_model_output_attr(self):
        """从 model_output 属性获取。"""

        class LastItem:
            model_output = "模型输出"

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.final_result_text == "模型输出"

    def test_empty_history_list(self):
        """history 列表为空。"""

        class HistoryObj:
            def __init__(self_):
                self_.history = []

        parser = HistoryParser(HistoryObj())
        assert parser.final_result_text is None

    def test_no_result_attributes(self):
        """最后一步没有结果属性。"""

        class LastItem:
            pass

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.final_result_text is None


class TestHistoryParserIsDone:
    """is_done 属性测试。"""

    def test_none_history(self):
        parser = HistoryParser(None)
        assert parser.is_done is False

    def test_is_done_method_true(self):
        """通过 is_done() 方法获取 True。"""

        class HistoryObj:
            def is_done(self_):
                return True

        parser = HistoryParser(HistoryObj())
        assert parser.is_done is True

    def test_is_done_method_false(self):
        """通过 is_done() 方法获取 False。"""

        class HistoryObj:
            def is_done(self_):
                return False

        parser = HistoryParser(HistoryObj())
        assert parser.is_done is False

    def test_is_successful_method(self):
        """通过 is_successful() 方法。"""

        class HistoryObj:
            def is_successful(self_):
                return True  # 非 None 值

        parser = HistoryParser(HistoryObj())
        assert parser.is_done is True

    def test_is_successful_method_none(self):
        """is_successful() 返回 None。"""

        class HistoryObj:
            def is_successful(self_):
                return None

        parser = HistoryParser(HistoryObj())
        # 应该回退到其他方法
        assert parser.is_done is False

    def test_done_action_attribute(self):
        """通过 action.name == 'done' 判断。"""

        class Action:
            name = "done"

        class LastItem:
            action = Action()

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.is_done is True

    def test_done_action_dict(self):
        """action 是字典。"""

        class LastItem:
            action = {"name": "done"}

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.is_done is True

    def test_done_in_actions_list(self):
        """在 actions 列表中找到 done。"""

        class Action:
            def __init__(self_, name):
                self_.name = name

        class LastItem:
            actions = [Action("click"), Action("done")]

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.is_done is True

    def test_done_in_actions_list_dict(self):
        """actions 列表中是字典。"""

        class LastItem:
            actions = [{"name": "type"}, {"name": "done"}]

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.is_done is True

    def test_not_done(self):
        """没有 done 标记。"""

        class LastItem:
            action = {"name": "click"}

        class HistoryObj:
            def __init__(self_):
                self_.history = [LastItem()]

        parser = HistoryParser(HistoryObj())
        assert parser.is_done is False


class TestHistoryParserIsSuccessful:
    """is_successful 属性测试。"""

    def test_none_history(self):
        parser = HistoryParser(None)
        assert parser.is_successful is None

    def test_is_successful_true(self):
        class HistoryObj:
            def is_successful(self_):
                return True

        parser = HistoryParser(HistoryObj())
        assert parser.is_successful is True

    def test_is_successful_false(self):
        class HistoryObj:
            def is_successful(self_):
                return False

        parser = HistoryParser(HistoryObj())
        assert parser.is_successful is False

    def test_is_successful_none(self):
        class HistoryObj:
            def is_successful(self_):
                return None

        parser = HistoryParser(HistoryObj())
        assert parser.is_successful is None

    def test_is_successful_exception(self):
        class HistoryObj:
            def is_successful(self_):
                raise RuntimeError("错误")

        parser = HistoryParser(HistoryObj())
        assert parser.is_successful is None


class TestHistoryParserTotalSteps:
    """total_steps 属性测试。"""

    def test_none_history(self):
        parser = HistoryParser(None)
        assert parser.total_steps == 0

    def test_from_history_list_length(self):
        """从 history 列表长度获取。"""

        class HistoryObj:
            def __init__(self_):
                self_.history = [1, 2, 3, 4, 5]

        parser = HistoryParser(HistoryObj())
        assert parser.total_steps == 5

    def test_from_n_steps_attribute(self):
        """从 n_steps 属性获取。"""

        class HistoryObj:
            def __init__(self_):
                self_.n_steps = 10

        parser = HistoryParser(HistoryObj())
        assert parser.total_steps == 10

    def test_empty_history_list(self):
        """history 列表为空。"""

        class HistoryObj:
            def __init__(self_):
                self_.history = []

        parser = HistoryParser(HistoryObj())
        assert parser.total_steps == 0

    def test_no_steps_info(self):
        """没有任何步骤信息。"""

        class HistoryObj:
            pass

        parser = HistoryParser(HistoryObj())
        assert parser.total_steps == 0


class TestHistoryParserTokenUsage:
    """token_usage 属性测试。"""

    def test_none_history(self):
        parser = HistoryParser(None)
        usage = parser.token_usage
        assert usage == TokenUsage()

    def test_with_token_data(self):
        """包含 token 数据。"""

        class Usage:
            def __init__(self_):
                self_.total_prompt_tokens = 100
                self_.total_completion_tokens = 50

        class HistoryObj:
            def __init__(self_):
                self_.usage = Usage()

        parser = HistoryParser(HistoryObj())
        usage = parser.token_usage
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50


class TestHistoryParserRaw:
    """raw 属性测试。"""

    def test_returns_original_history(self):
        class HistoryObj:
            pass

        history = HistoryObj()
        parser = HistoryParser(history)
        assert parser.raw is history


# ============ Step Outcomes 测试 ============


def _make_history_item(
    current_plan_item=None,
    actions=None,
    errors=None,
    error=None,
    start_time=None,
    end_time=None,
    url=None,
    result=None,
    metadata_none=False,
    model_output_none=False,
):
    """构造模拟的 history item。"""

    class _Metadata:
        pass

    class _ModelOutput:
        pass

    class _State:
        pass

    class _Action:
        def __init__(self, name):
            self.name = name

    class _Item:
        pass

    item = _Item()

    # model_output
    if model_output_none:
        item.model_output = None
    else:
        mo = _ModelOutput()
        mo.current_plan_item = current_plan_item
        mo.actions = [_Action(a) for a in (actions or [])]
        item.model_output = mo

    # errors
    item.errors = errors if errors is not None else []
    item.error = error

    # metadata
    if metadata_none:
        item.metadata = None
    else:
        md = _Metadata()
        md.start_time = start_time
        md.end_time = end_time
        md.started_at = None
        md.stopped_at = None
        item.metadata = md

    # state
    state = _State()
    state.url = url
    item.state = state

    # result
    item.result = result if result is not None else []

    return item


def _make_result(is_done=False, success=None, error=None):
    """构造模拟的 ActionResult。"""

    class _Result:
        pass

    r = _Result()
    r.is_done = is_done
    r.success = success
    r.error = error
    return r


class TestExtractStepOutcomes:
    """步骤级信息提取测试。"""

    def test_empty_steps_returns_empty(self):
        """无步骤时返回空列表。"""
        case = TestCase(name="空用例", steps=[])

        class HistoryObj:
            history = [_make_history_item()]

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)
        assert outcomes == []

    def test_no_history_returns_unknown(self):
        """无执行历史时所有步骤标记 UNKNOWN。"""
        case = TestCase(
            name="测试",
            steps=[TestStep(text="步骤1"), TestStep(text="步骤2")],
        )
        parser = HistoryParser(None)
        outcomes = parser.extract_step_outcomes(case)
        assert len(outcomes) == 2
        assert all(o.status == "UNKNOWN" for o in outcomes)
        assert outcomes[0].step_text == "步骤1"
        assert outcomes[1].step_text == "步骤2"

    def test_current_plan_item_mapping(self):
        """使用 current_plan_item 正确分组迭代到步骤。"""
        # 3 个步骤, 10 次迭代
        # plan_items: 0,0,0, 1,1,1,1, 2,2,2 (0-based)
        steps = [TestStep(text=f"步骤{i}") for i in range(3)]
        case = TestCase(name="测试", steps=steps)

        items = []
        plan_sequence = [0, 0, 0, 1, 1, 1, 1, 2, 2, 2]
        for p in plan_sequence:
            items.append(_make_history_item(current_plan_item=p))

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert len(outcomes) == 3
        assert outcomes[0].iterations == 3
        assert outcomes[1].iterations == 4
        assert outcomes[2].iterations == 3

    def test_current_plan_item_1_based(self):
        """检测 1-based current_plan_item 并正确转换。"""
        # 3 个步骤, plan_items 为 1,2,3 (1-based, max==num_steps)
        steps = [TestStep(text=f"步骤{i}") for i in range(3)]
        case = TestCase(name="测试", steps=steps)

        items = [
            _make_history_item(current_plan_item=1),
            _make_history_item(current_plan_item=1),
            _make_history_item(current_plan_item=2),
            _make_history_item(current_plan_item=2),
            _make_history_item(current_plan_item=3),
            _make_history_item(current_plan_item=3),
        ]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert len(outcomes) == 3
        assert outcomes[0].iterations == 2  # plan_item 1 → step 0
        assert outcomes[1].iterations == 2  # plan_item 2 → step 1
        assert outcomes[2].iterations == 2  # plan_item 3 → step 2

    def test_fallback_uniform_distribution(self):
        """current_plan_item 不可用时均匀分配。"""
        # 6 次迭代、3 个步骤 → 每步 2 次
        steps = [TestStep(text=f"步骤{i}") for i in range(3)]
        case = TestCase(name="测试", steps=steps)

        # 所有 plan_item 为 None → 回退到均匀分配
        items = [_make_history_item(current_plan_item=None) for _ in range(6)]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert len(outcomes) == 3
        assert outcomes[0].iterations == 2
        assert outcomes[1].iterations == 2
        assert outcomes[2].iterations == 2

    def test_iterations_exceed_steps(self):
        """迭代数 >> 步骤数时，多余迭代归入最后步骤。"""
        steps = [TestStep(text="步骤0"), TestStep(text="步骤1")]
        case = TestCase(name="测试", steps=steps)

        # 10 次迭代, 无 plan_item → 均匀分配 per_step=5
        items = [_make_history_item(current_plan_item=None) for _ in range(10)]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert len(outcomes) == 2
        # per_step = 10/2 = 5.0, idx: 0-4 → step0, 5-9 → step1
        assert outcomes[0].iterations == 5
        assert outcomes[1].iterations == 5

    def test_steps_exceed_iterations(self):
        """步骤数 > 迭代数时，未覆盖步骤标记 UNKNOWN。"""
        steps = [TestStep(text=f"步骤{i}") for i in range(5)]
        case = TestCase(name="测试", steps=steps)

        # 只有 2 次迭代
        items = [_make_history_item(current_plan_item=None) for _ in range(2)]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert len(outcomes) == 5
        # per_step = max(2/5, 1) = 1.0
        # idx 0 → step 0, idx 1 → step 1
        # steps 2,3,4 没有迭代 → UNKNOWN
        assert outcomes[0].status == "PASSED"
        assert outcomes[1].status == "PASSED"
        assert outcomes[2].status == "UNKNOWN"
        assert outcomes[3].status == "UNKNOWN"
        assert outcomes[4].status == "UNKNOWN"

    def test_metadata_none_compatibility(self):
        """metadata 为 None 时不崩溃，时间为 0。"""
        steps = [TestStep(text="步骤1")]
        case = TestCase(name="测试", steps=steps)

        items = [_make_history_item(current_plan_item=0, metadata_none=True)]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert len(outcomes) == 1
        assert outcomes[0].duration == 0.0
        assert outcomes[0].started_at == 0.0
        assert outcomes[0].stopped_at == 0.0

    def test_model_output_none_compatibility(self):
        """model_output 为 None 时不崩溃。"""
        steps = [TestStep(text="步骤1")]
        case = TestCase(name="测试", steps=steps)

        items = [_make_history_item(model_output_none=True)]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert len(outcomes) == 1
        # model_output=None → plan_item=None, 但只有 1 步所以都归入 step 0
        assert outcomes[0].actions == []

    def test_error_in_iteration_marks_step_failed(self):
        """迭代中有错误时步骤标记 FAILED。"""
        steps = [TestStep(text="步骤1")]
        case = TestCase(name="测试", steps=steps)

        items = [
            _make_history_item(
                current_plan_item=0, errors=["元素不存在"]
            )
        ]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert outcomes[0].status == "FAILED"
        assert "元素不存在" in outcomes[0].errors

    def test_passed_step_no_errors(self):
        """无错误的步骤标记 PASSED。"""
        steps = [TestStep(text="步骤1")]
        case = TestCase(name="测试", steps=steps)

        items = [
            _make_history_item(
                current_plan_item=0,
                actions=["click"],
                start_time=100.0,
                end_time=102.0,
            )
        ]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert outcomes[0].status == "PASSED"
        assert outcomes[0].errors == []
        assert outcomes[0].duration == 2.0

    def test_actions_collected(self):
        """动作名称正确收集。"""
        steps = [TestStep(text="步骤1")]
        case = TestCase(name="测试", steps=steps)

        items = [
            _make_history_item(
                current_plan_item=0, actions=["click", "type", "scroll"]
            )
        ]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        assert outcomes[0].actions == ["click", "type", "scroll"]

    def test_url_from_last_iteration(self):
        """URL 取自组内最后一个迭代的 state。"""
        steps = [TestStep(text="步骤1")]
        case = TestCase(name="测试", steps=steps)

        items = [
            _make_history_item(current_plan_item=0, url="https://page1.com"),
            _make_history_item(current_plan_item=0, url="https://page2.com"),
        ]

        class HistoryObj:
            history = items

        parser = HistoryParser(HistoryObj())
        outcomes = parser.extract_step_outcomes(case)

        # url 是逐个迭代覆盖的，最终取最后一个非空值
        assert outcomes[0].url == "https://page2.com"
