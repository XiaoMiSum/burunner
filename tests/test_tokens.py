"""Token 用量统计模块单元测试。"""

from burunner.utils.tokens import TokenUsage, usage_from_history, _extract_int


class TestTokenUsage:
    """TokenUsage 数据类测试。"""

    def test_create_default(self):
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total == 0

    def test_create_with_values(self):
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total == 150

    def test_add(self):
        usage1 = TokenUsage(input_tokens=100, output_tokens=50)
        usage2 = TokenUsage(input_tokens=200, output_tokens=100)
        result = usage1 + usage2
        assert result.input_tokens == 300
        assert result.output_tokens == 150
        assert result.total == 450

    def test_add_does_not_mutate(self):
        usage1 = TokenUsage(input_tokens=100, output_tokens=50)
        usage2 = TokenUsage(input_tokens=200, output_tokens=100)
        _ = usage1 + usage2
        assert usage1.input_tokens == 100
        assert usage2.input_tokens == 200


class TestExtractInt:
    """_extract_int 辅助函数测试。"""

    def test_extract_from_object(self):
        class Obj:
            def __init__(self):
                self.value = 42

        obj = Obj()
        assert _extract_int(obj, "value") == 42

    def test_extract_from_object_missing(self):
        class Obj:
            pass

        obj = Obj()
        assert _extract_int(obj, "nonexistent") is None

    def test_extract_from_dict(self):
        d = {"key": 123}
        assert _extract_int(d, "key") == 123

    def test_extract_from_dict_missing(self):
        d = {"key": 123}
        assert _extract_int(d, "nonexistent") is None

    def test_extract_multiple_names(self):
        class Obj:
            def __init__(self):
                self.first = None
                self.second = 99

        obj = Obj()
        assert _extract_int(obj, "first", "second") == 99

    def test_extract_float_conversion(self):
        class Obj:
            def __init__(self):
                self.value = 42.5

        obj = Obj()
        assert _extract_int(obj, "value") == 42


class TestUsageFromHistory:
    """usage_from_history 函数测试。"""

    def test_none_history(self):
        usage = usage_from_history(None)
        assert usage == TokenUsage()

    def test_history_usage_attribute(self):
        """测试形态 1: history.usage"""

        class Usage:
            def __init__(self):
                self.total_prompt_tokens = 100
                self.total_completion_tokens = 50

        class History:
            def __init__(self):
                self.usage = Usage()

        usage = usage_from_history(History())
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    def test_history_flat_attributes(self):
        """测试形态 2: 平铺属性"""

        class History:
            def __init__(self):
                self.total_input_tokens = 200
                self.total_output_tokens = 100
                self.usage = None  # 形态 1 不存在

        usage = usage_from_history(History())
        assert usage.input_tokens == 200
        assert usage.output_tokens == 100

    def test_history_list(self):
        """测试形态 3: 遍历 history.history"""

        class Metadata:
            def __init__(self, input_tokens, output_tokens):
                self.input_tokens = input_tokens
                self.output_tokens = output_tokens

        class HistoryItem:
            def __init__(self, input_tokens, output_tokens):
                self.metadata = Metadata(input_tokens, output_tokens)

        class History:
            def __init__(self):
                self.usage = None
                self.history = [
                    HistoryItem(50, 25),
                    HistoryItem(100, 50),
                ]

        usage = usage_from_history(History())
        assert usage.input_tokens == 150
        assert usage.output_tokens == 75

    def test_history_empty_list(self):
        class History:
            def __init__(self):
                self.usage = None
                self.history = []

        usage = usage_from_history(History())
        assert usage == TokenUsage()

    def test_history_no_attributes(self):
        """没有任何 token 相关属性"""

        class History:
            pass

        usage = usage_from_history(History())
        assert usage == TokenUsage()
