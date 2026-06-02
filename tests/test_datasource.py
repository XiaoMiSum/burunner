"""数据源模块单元测试。"""

import csv
import json
from pathlib import Path

import pytest
import yaml

from burunner.parser.datasource import (
    DataSourceError,
    DataCache,
    load_csv,
    load_json,
    load_yaml_data,
    load_inline_data,
    resolve_data_source,
    filter_data_rows,
    row_to_variables,
    clear_cache,
)


class TestDataCache:
    """DataCache 类测试。"""

    def test_create_cache(self):
        cache = DataCache()
        assert cache.get("nonexistent") is None

    def test_set_and_get(self):
        cache = DataCache()
        data = [{"name": "test"}]
        cache.set("key1", data)
        assert cache.get("key1") == data

    def test_get_nonexistent(self):
        cache = DataCache()
        assert cache.get("missing") is None

    def test_clear(self):
        cache = DataCache()
        cache.set("key1", [{"a": 1}])
        cache.set("key2", [{"b": 2}])
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_contains(self):
        cache = DataCache()
        cache.set("key1", [])
        assert "key1" in cache
        assert "key2" not in cache


class TestLoadCSV:
    """CSV 加载测试。"""

    def test_load_csv_valid(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")

        result = load_csv(str(csv_file))
        assert len(result) == 2
        assert result[0] == {"name": "Alice", "age": "30"}
        assert result[1] == {"name": "Bob", "age": "25"}

    def test_load_csv_not_exists(self):
        with pytest.raises(DataSourceError, match="不存在"):
            load_csv("/nonexistent/file.csv")

    def test_load_csv_empty(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("name,age\n", encoding="utf-8")

        with pytest.raises(DataSourceError, match="为空"):
            load_csv(str(csv_file))


class TestLoadJSON:
    """JSON 加载测试。"""

    def test_load_json_valid(self, tmp_path):
        json_file = tmp_path / "test.json"
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = load_json(str(json_file))
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_load_json_not_exists(self):
        with pytest.raises(DataSourceError, match="不存在"):
            load_json("/nonexistent/file.json")

    def test_load_json_not_array(self, tmp_path):
        json_file = tmp_path / "invalid.json"
        json_file.write_text('{"name": "Alice"}', encoding="utf-8")

        with pytest.raises(DataSourceError, match="必须是数组"):
            load_json(str(json_file))

    def test_load_json_empty(self, tmp_path):
        json_file = tmp_path / "empty.json"
        json_file.write_text("[]", encoding="utf-8")

        with pytest.raises(DataSourceError, match="为空"):
            load_json(str(json_file))

    def test_load_json_invalid_item(self, tmp_path):
        json_file = tmp_path / "invalid.json"
        json_file.write_text('["not", "a", "dict"]', encoding="utf-8")

        with pytest.raises(DataSourceError, match="必须是对象"):
            load_json(str(json_file))


class TestLoadYAMLData:
    """YAML 数据加载测试。"""

    def test_load_yaml_valid(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        data = [{"name": "Alice"}, {"name": "Bob"}]
        yaml_file.write_text(yaml.dump(data), encoding="utf-8")

        result = load_yaml_data(str(yaml_file))
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_load_yaml_not_exists(self):
        with pytest.raises(DataSourceError, match="不存在"):
            load_yaml_data("/nonexistent/file.yaml")

    def test_load_yaml_not_list(self, tmp_path):
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("name: Alice", encoding="utf-8")

        with pytest.raises(DataSourceError, match="必须是列表"):
            load_yaml_data(str(yaml_file))

    def test_load_yaml_empty(self, tmp_path):
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("[]", encoding="utf-8")

        with pytest.raises(DataSourceError, match="为空"):
            load_yaml_data(str(yaml_file))


class TestLoadInlineData:
    """内联数据加载测试。"""

    def test_load_inline_valid(self):
        data = [{"name": "Alice"}, {"name": "Bob"}]
        result = load_inline_data(data, "test")
        assert result == data

    def test_load_inline_not_list(self):
        with pytest.raises(DataSourceError, match="必须是列表"):
            load_inline_data("not a list", "test")

    def test_load_inline_empty(self):
        with pytest.raises(DataSourceError, match="不能为空"):
            load_inline_data([], "test")

    def test_load_inline_invalid_item(self):
        with pytest.raises(DataSourceError, match="必须是映射"):
            load_inline_data(["not a dict"], "test")


class TestResolveDataSource:
    """数据源解析入口测试。"""

    def test_resolve_csv_file(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name\nAlice\n", encoding="utf-8")

        result = resolve_data_source(
            str(csv_file), base_dir=tmp_path, ctx="test")
        assert len(result) == 1

    def test_resolve_json_file(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text('[{"name": "Alice"}]', encoding="utf-8")

        result = resolve_data_source(
            str(json_file), base_dir=tmp_path, ctx="test")
        assert len(result) == 1

    def test_resolve_yaml_file(self, tmp_path):
        yaml_file = tmp_path / "data.yaml"
        yaml_file.write_text("- name: Alice", encoding="utf-8")

        result = resolve_data_source(
            str(yaml_file), base_dir=tmp_path, ctx="test")
        assert len(result) == 1

    def test_resolve_inline(self):
        data = [{"name": "Alice"}]
        result = resolve_data_source(data, ctx="test")
        assert len(result) == 1

    def test_resolve_dict_csv(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name\nAlice\n", encoding="utf-8")

        result = resolve_data_source(
            {"type": "csv", "file": str(csv_file)}, base_dir=tmp_path, ctx="test"
        )
        assert len(result) == 1

    def test_resolve_dict_inline(self):
        result = resolve_data_source(
            {"type": "inline", "data": [{"name": "Alice"}]}, ctx="test"
        )
        assert len(result) == 1

    def test_resolve_unsupported_type(self):
        with pytest.raises(DataSourceError, match="无法识别"):
            resolve_data_source("file.txt", ctx="test")

    def test_resolve_invalid_type(self):
        with pytest.raises(DataSourceError, match="必须是字符串、列表或字典"):
            resolve_data_source(123, ctx="test")


class TestFilterDataRows:
    """数据过滤测试。"""

    def test_no_filter(self):
        rows = [{"name": "Alice"}, {"name": "Bob"}]
        result = filter_data_rows(rows)
        assert result == rows

    def test_filter_keep(self):
        rows = [
            {"name": "Alice", "status": "active"},
            {"name": "Bob", "status": "inactive"},
        ]
        result = filter_data_rows(rows, filter_expr="status == 'active'")
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_skip_if(self):
        rows = [
            {"name": "Alice", "skip": False},
            {"name": "Bob", "skip": True},
        ]
        result = filter_data_rows(rows, skip_if_expr="skip == true")
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_filter_and_skip(self):
        rows = [
            {"name": "Alice", "status": "active", "skip": False},
            {"name": "Bob", "status": "active", "skip": True},
            {"name": "Charlie", "status": "inactive", "skip": False},
        ]
        result = filter_data_rows(
            rows, filter_expr="status == 'active'", skip_if_expr="skip == true"
        )
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_filter_invalid_expression(self):
        rows = [{"name": "Alice"}]
        with pytest.raises(DataSourceError, match="求值失败"):
            filter_data_rows(rows, filter_expr="invalid syntax !!!")


class TestRowToVariables:
    """数据行转变量测试。"""

    def test_simple_conversion(self):
        row = {"username": "alice", "age": 30}
        result = row_to_variables(row)
        assert result == {"data.username": "alice", "data.age": "30"}

    def test_none_value(self):
        row = {"name": None}
        result = row_to_variables(row)
        assert result == {"data.name": ""}

    def test_custom_prefix(self):
        row = {"key": "value"}
        result = row_to_variables(row, prefix="custom")
        assert result == {"custom.key": "value"}

    def test_empty_row(self):
        row = {}
        result = row_to_variables(row)
        assert result == {}


class TestCacheIntegration:
    """缓存集成测试。"""

    def test_cache_is_used(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name\nAlice\n", encoding="utf-8")

        # 第一次加载
        result1 = load_csv(str(csv_file))
        assert len(result1) == 1

        # 修改文件
        csv_file.write_text("name\nBob\n", encoding="utf-8")

        # 应该返回缓存的数据
        result2 = load_csv(str(csv_file))
        assert result2 == result1  # 仍然是 Alice
        assert result2[0]["name"] == "Alice"

    def test_clear_cache(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name\nAlice\n", encoding="utf-8")

        load_csv(str(csv_file))

        # 清空缓存
        clear_cache()

        # 修改文件
        csv_file.write_text("name\nBob\n", encoding="utf-8")

        # 应该重新加载
        result = load_csv(str(csv_file))
        assert result[0]["name"] == "Bob"
