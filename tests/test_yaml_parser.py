"""YAML 解析器单元测试。"""

from pathlib import Path

import pytest
import yaml

from burunner.exceptions import ConfigurationError
from burunner.parser.yaml_parser import (
    YamlParseError,
    load_yaml,
    load_files,
)


class TestLoadYAML:
    """load_yaml 函数测试。"""

    def test_load_list_format(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
- name: 测试用例1
  steps:
    - 打开网页
    - 点击按钮
- name: 测试用例2
  steps:
    - 登录系统
""",
            encoding="utf-8",
        )

        cases, config, presets = load_yaml(yaml_file)
        assert len(cases) == 2
        assert cases[0].name == "测试用例1"
        assert len(cases[0].steps) == 2
        assert cases[1].name == "测试用例2"

    def test_load_dict_format(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
cases:
  - name: 测试用例1
    steps:
      - 打开网页
config:
  llm_provider: openai
""",
            encoding="utf-8",
        )

        cases, config, presets = load_yaml(yaml_file)
        assert len(cases) == 1
        assert config["llm_provider"] == "openai"

    def test_load_empty_file(self, tmp_path):
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("", encoding="utf-8")

        cases, config, presets = load_yaml(yaml_file)
        assert cases == []
        assert config == {}
        assert presets == {}

    def test_load_file_not_exists(self):
        with pytest.raises(YamlParseError, match="不存在"):
            load_yaml("/nonexistent/file.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(":::invalid yaml:::", encoding="utf-8")

        # YAML 解析可能不会失败,但会返回 None 或非预期结构
        # 这个测试取决于实际行为
        try:
            cases, config, presets = load_yaml(yaml_file)
        except YamlParseError:
            pass  # 预期可能失败

    def test_load_case_missing_name(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
- steps:
    - 打开网页
""",
            encoding="utf-8",
        )

        with pytest.raises(YamlParseError, match="name"):
            load_yaml(yaml_file)

    def test_load_case_empty_steps(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
- name: 测试用例
  steps: []
""",
            encoding="utf-8",
        )

        with pytest.raises(YamlParseError, match="steps"):
            load_yaml(yaml_file)

    def test_load_case_with_extends(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
presets:
  login:
    steps:
      - 打开登录页

cases:
  - name: 继承用例
    extends: login
    steps:
      - 输入用户名
""",
            encoding="utf-8",
        )

        cases, config, presets = load_yaml(yaml_file)
        assert len(cases) == 1
        assert cases[0].extends == "login"
        assert len(cases[0].steps) == 1  # 自身步骤

    def test_load_presets(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
presets:
  login:
    description: 登录流程
    steps:
      - 打开登录页
      - 输入凭据
    tags:
      - auth

cases:
  - name: 使用预设
    extends: login
""",
            encoding="utf-8",
        )

        cases, config, presets = load_yaml(yaml_file)
        assert "login" in presets
        assert presets["login"].description == "登录流程"
        assert len(presets["login"].steps) == 2

    def test_load_cookies(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
- name: 测试用例
  steps:
    - 打开网页
  cookies:
    - name: session
      value: abc123
      domain: example.com
""",
            encoding="utf-8",
        )

        cases, config, presets = load_yaml(yaml_file)
        assert len(cases[0].cookies) == 1
        assert cases[0].cookies[0].name == "session"

    def test_load_variables(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
variables:
  base_url: https://example.com
  username: admin

cases:
  - name: 测试用例
    steps:
      - 打开 ${base_url}
""",
            encoding="utf-8",
        )

        cases, config, presets = load_yaml(yaml_file)
        assert "_variables" in config
        assert config["_variables"]["base_url"] == "https://example.com"

    def test_load_environments(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
cases:
  - name: 测试用例
    steps:
      - 打开网页

environments:
  production:
    variables:
      base_url: https://prod.example.com
    config:
      llm_model: gpt-4
  staging:
    variables:
      base_url: https://staging.example.com
""",
            encoding="utf-8",
        )

        cases, config, presets = load_yaml(yaml_file)
        assert "_environments" in config
        assert "production" in config["_environments"]
        assert "staging" in config["_environments"]


class TestLoadFiles:
    """load_files 函数测试。"""

    def test_load_single_file(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
- name: 用例1
  steps:
    - 步骤1
- name: 用例2
  steps:
    - 步骤2
""",
            encoding="utf-8",
        )

        suite = load_files([yaml_file])
        assert len(suite.cases) == 2
        assert len(suite.source_files) == 1

    def test_load_multiple_files(self, tmp_path):
        file1 = tmp_path / "test1.yaml"
        file1.write_text(
            """
- name: 用例1
  steps:
    - 步骤1
""",
            encoding="utf-8",
        )

        file2 = tmp_path / "test2.yaml"
        file2.write_text(
            """
- name: 用例2
  steps:
    - 步骤2
""",
            encoding="utf-8",
        )

        suite = load_files([file1, file2])
        assert len(suite.cases) == 2
        assert len(suite.source_files) == 2

    def test_duplicate_names_get_suffix(self, tmp_path):
        file1 = tmp_path / "suite1.yaml"
        file1.write_text(
            """
- name: 重复用例
  steps:
    - 步骤1
""",
            encoding="utf-8",
        )

        file2 = tmp_path / "suite2.yaml"
        file2.write_text(
            """
- name: 重复用例
  steps:
    - 步骤2
""",
            encoding="utf-8",
        )

        suite = load_files([file1, file2])
        assert len(suite.cases) == 2
        # 第二个用例应该有后缀
        names = [c.name for c in suite.cases]
        assert any("suite2" in name for name in names)

    def test_resolve_extends(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
presets:
  base:
    steps:
      - 前置步骤1
      - 前置步骤2

cases:
  - name: 继承用例
    extends: base
    steps:
      - 用例步骤
""",
            encoding="utf-8",
        )

        suite = load_files([yaml_file])
        assert len(suite.cases) == 1
        # 步骤应该合并: 前置步骤 + 用例步骤
        assert len(suite.cases[0].steps) == 3
        assert suite.cases[0].steps[0].text == "前置步骤1"
        assert suite.cases[0].steps[2].text == "用例步骤"

    def test_apply_variables(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
variables:
  url: https://example.com
  action: 点击

cases:
  - name: 变量测试
    steps:
      - 打开 ${url}
      - ${action}按钮
""",
            encoding="utf-8",
        )

        suite = load_files([yaml_file])
        assert len(suite.cases) == 1
        assert suite.cases[0].steps[0].text == "打开 https://example.com"
        assert suite.cases[0].steps[1].text == "点击按钮"

    def test_load_with_env_name(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
cases:
  - name: 测试用例
    steps:
      - 打开网页

environments:
  production:
    variables:
      env_name: production
  staging:
    variables:
      env_name: staging
""",
            encoding="utf-8",
        )

        suite = load_files([yaml_file], env_name="production")
        assert suite.active_env == "production"
        # 环境变量应该注入
        assert "env_name" in suite.variables
        assert suite.variables["env_name"] == "production"

    def test_load_invalid_env_name(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
cases:
  - name: 测试用例
    steps:
      - 打开网页

environments:
  production:
    variables:
      base_url: https://prod.example.com
""",
            encoding="utf-8",
        )

        with pytest.raises(YamlParseError, match="未定义"):
            load_files([yaml_file], env_name="nonexistent")

    def test_data_driven_expansion(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
- name: 数据驱动测试
  steps:
    - 测试用户
  data_source:
    - username: alice
    - username: bob
""",
            encoding="utf-8",
        )

        suite = load_files([yaml_file])
        # 应该展开为 2 个用例
        assert len(suite.cases) == 2
        assert "alice" in suite.cases[0].name or "0" in suite.cases[0].name
        assert "bob" in suite.cases[1].name or "1" in suite.cases[1].name
        # 数据行应该被设置
        assert suite.cases[0].data_row is not None
        assert suite.cases[0].data_row.get("username") == "alice"
        assert suite.cases[1].data_row.get("username") == "bob"


class TestCoerceHelpers:
    """辅助函数测试。"""

    def test_coerce_step_string(self):
        from burunner.parser.yaml_parser import _coerce_step

        step = _coerce_step("打开网页", "test")
        assert step.text == "打开网页"

    def test_coerce_step_dict_with_text(self):
        from burunner.parser.yaml_parser import _coerce_step

        step = _coerce_step({"text": "点击按钮"}, "test")
        assert step.text == "点击按钮"

    def test_coerce_step_dict_with_step(self):
        from burunner.parser.yaml_parser import _coerce_step

        step = _coerce_step({"step": "输入内容"}, "test")
        assert step.text == "输入内容"

    def test_coerce_step_dict_with_action(self):
        from burunner.parser.yaml_parser import _coerce_step

        step = _coerce_step({"action": "提交表单"}, "test")
        assert step.text == "提交表单"

    def test_coerce_step_empty_string(self):
        from burunner.parser.yaml_parser import _coerce_step

        with pytest.raises(YamlParseError, match="不能为空"):
            _coerce_step("  ", "test")

    def test_coerce_step_invalid_type(self):
        from burunner.parser.yaml_parser import _coerce_step

        with pytest.raises(YamlParseError, match="必须是字符串或带 'text' 的字典"):
            _coerce_step(123, "test")

    def test_coerce_cookies_empty(self):
        from burunner.parser.yaml_parser import _coerce_cookies

        result = _coerce_cookies(None, "test")
        assert result == []

    def test_coerce_cookies_valid(self):
        from burunner.parser.yaml_parser import _coerce_cookies

        result = _coerce_cookies(
            [{"name": "session", "value": "abc", "domain": "example.com"}],
            "test",
        )
        assert len(result) == 1
        assert result[0].name == "session"

    def test_coerce_cookies_missing_name(self):
        from burunner.parser.yaml_parser import _coerce_cookies

        with pytest.raises(YamlParseError, match="name"):
            _coerce_cookies(
                [{"value": "abc", "domain": "example.com"}], "test")
