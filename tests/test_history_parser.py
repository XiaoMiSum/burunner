"""历史解析器模块单元测试。"""

import pytest

from burunner.runner.history_parser import HistoryParser
from burunner.utils.tokens import TokenUsage


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
