"""端到端集成测试 - 使用 examples/ 中的真实文件验证完整流程。"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from burunner.config import RunnerConfig
from burunner.parser.datasource import load_csv, load_json, clear_cache
from burunner.parser.models import TestCase, TestStep, TestSuite
from burunner.parser.yaml_parser import load_files
from burunner.runner.result import CaseResult, CaseStatus, SuiteResult

# examples 目录路径
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE_YAML = EXAMPLES_DIR / "example.yaml"
TEST_DATA_CSV = EXAMPLES_DIR / "test_data.csv"
TEST_USERS_JSON = EXAMPLES_DIR / "test_users.json"


# ---------------------------------------------------------------------------
# 1. YAML 解析端到端测试
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestYamlParsingE2E:
    """YAML 解析全流程端到端测试，使用 examples/ 中的真实文件。"""

    def test_load_example_yaml(self):
        """加载 example.yaml 并验证 TestSuite 结构完整性。"""
        suite = load_files([EXAMPLE_YAML])

        # 验证返回类型
        assert isinstance(suite, TestSuite)
        # 验证用例数量（example.yaml 中定义了 7 个用例）
        assert len(suite.cases) == 7
        # 验证 source_files
        assert EXAMPLE_YAML in suite.source_files

        # 验证每个用例的 name 字段非空
        names = [c.name for c in suite.cases]
        assert "百度搜索关键词" in names
        assert "搜索自动补全" in names
        assert "百度图片搜索" in names
        assert "英文关键词搜索" in names
        assert "搜索历史显示" in names
        assert "空关键词搜索" in names
        assert "特殊字符搜索" in names

    def test_example_yaml_steps_parsed(self):
        """验证步骤正确解析为 TestStep 对象。"""
        suite = load_files([EXAMPLE_YAML])

        for case in suite.cases:
            # 每个用例的 steps 非空
            assert len(case.steps) > 0, f"用例 '{case.name}' 步骤为空"
            # 每个 TestStep.text 是有效字符串
            for step in case.steps:
                assert isinstance(step, TestStep)
                assert isinstance(step.text, str)
                assert len(step.text.strip()) > 0

    def test_example_yaml_config_section(self):
        """验证 YAML 中的 config 段正确解析。"""
        suite = load_files([EXAMPLE_YAML])

        # example.yaml 有 config 段: llm_provider, llm_model, max_steps, headless
        cfg = suite.yaml_config
        assert cfg.get("llm_provider") == "openai"
        assert cfg.get("llm_model") == "oc/mimo-v2.5-free"
        assert cfg.get("max_steps") == 30
        assert cfg.get("headless") is True

    def test_example_yaml_presets_parsed(self):
        """验证预设正确解析为 TestTemplate 对象。"""
        suite = load_files([EXAMPLE_YAML])

        # example.yaml 定义了 "打开百度搜索" 预设
        assert "打开百度搜索" in suite.templates
        template = suite.templates["打开百度搜索"]
        assert len(template.steps) == 2
        assert "baidu.com" in template.steps[0].text
        assert "百度一下" in template.steps[1].text

    def test_example_yaml_tags_parsed(self):
        """验证用例标签正确解析。"""
        suite = load_files([EXAMPLE_YAML])

        # 查找"百度搜索关键词"用例
        search_case = next(c for c in suite.cases if c.name == "百度搜索关键词")
        assert "smoke" in search_case.tags
        assert "search" in search_case.tags
        assert "p1" in search_case.tags

    def test_example_yaml_environments_parsed(self):
        """验证多环境配置正确解析。"""
        suite = load_files([EXAMPLE_YAML])

        # example.yaml 定义了 dev/staging/prod 三个环境
        assert "dev" in suite.environments
        assert "staging" in suite.environments
        assert "prod" in suite.environments

        # 验证 dev 环境变量
        dev_env = suite.environments["dev"]
        assert dev_env.variables.get("search_keyword") == "Python 入门教程"
        assert dev_env.variables.get("expected_result") == "Python"

    def test_load_example_yaml_with_env(self):
        """加载 example.yaml 并激活 dev 环境。"""
        suite = load_files([EXAMPLE_YAML], env_name="dev")

        assert suite.active_env == "dev"
        # 环境变量应注入到全局变量中
        assert "search_keyword" in suite.variables
        assert suite.variables["search_keyword"] == "Python 入门教程"


# ---------------------------------------------------------------------------
# 2. 数据驱动端到端测试
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDataDrivenE2E:
    """数据驱动全流程端到端测试。"""

    def setup_method(self):
        """每个测试方法前清除缓存。"""
        clear_cache()

    def test_csv_data_loading(self):
        """加载 test_data.csv 并验证数据行正确。"""
        rows = load_csv(str(TEST_DATA_CSV))

        # test_data.csv 有 4 行数据（不含表头）
        assert len(rows) == 4
        # 验证字段名
        assert "search_keyword" in rows[0]
        assert "expected_result" in rows[0]
        assert "priority" in rows[0]
        # 验证第一行数据
        assert rows[0]["search_keyword"] == "Python 教程"
        assert rows[0]["expected_result"] == "Python编程"
        assert rows[0]["priority"] == "smoke"

    def test_json_data_loading(self):
        """加载 test_users.json 并验证数据结构。"""
        rows = load_json(str(TEST_USERS_JSON))

        # test_users.json 有 3 个用户数据
        assert len(rows) == 3
        # 验证数据结构
        for row in rows:
            assert "username" in row
            assert "search_term" in row
            assert "expected" in row
        # 验证第一个用户
        assert rows[0]["username"] == "测试员小王"
        assert rows[0]["search_term"] == "Python入门"
        assert rows[0]["expected"] == "Python教程"

    def test_data_driven_case_expansion(self):
        """验证数据驱动用例正确展开为多个 TestCase。"""
        # 创建一个带数据驱动的临时 YAML，使用 CSV 作为数据源
        import tempfile

        yaml_content = f"""\
cases:
  - name: 数据驱动搜索
    data_source: "{TEST_DATA_CSV}"
    steps:
      - 搜索关键词
      - 验证搜索结果
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            tmp_path = Path(f.name)

        try:
            suite = load_files([tmp_path])
            # CSV 有 4 行数据，应展开为 4 个用例
            assert len(suite.cases) == 4
            # 验证用例名称包含索引
            assert "[0]" in suite.cases[0].name
            assert "[1]" in suite.cases[1].name
            # 验证数据行已绑定到用例
            assert suite.cases[0].data_row is not None
            assert suite.cases[0].data_row["search_keyword"] == "Python 教程"
            assert suite.cases[1].data_row["search_keyword"] == "软件测试"
            # 验证数据变量注入到 variables
            assert "data.search_keyword" in suite.cases[0].variables
        finally:
            tmp_path.unlink()


# ---------------------------------------------------------------------------
# 3. 配置合并端到端测试
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestConfigE2E:
    """配置合并全流程端到端测试。"""

    def test_config_from_env_with_yaml(self, monkeypatch):
        """环境变量 + YAML config 合并正确。"""
        # 设置环境变量
        monkeypatch.setenv("BURUNNER_LLM_PROVIDER", "openai")
        monkeypatch.setenv("BURUNNER_LLM_MODEL", "gpt-4o-mini")

        # 从环境构建配置
        cfg = RunnerConfig.from_env()
        assert cfg.llm_provider == "openai"
        assert cfg.llm_model == "gpt-4o-mini"

        # 加载 example.yaml 并合并
        suite = load_files([EXAMPLE_YAML])
        merged_cfg = cfg.merge_yaml_config(suite.yaml_config)

        # YAML config 覆盖环境变量默认值
        assert merged_cfg.llm_provider == "openai"
        assert merged_cfg.llm_model == "oc/mimo-v2.5-free"
        assert merged_cfg.max_steps == 30
        assert merged_cfg.headless is True

    def test_config_overrides(self, monkeypatch):
        """CLI 覆盖优先级最高。"""
        monkeypatch.setenv("BURUNNER_LLM_MODEL", "gpt-4o-mini")

        # from_env → merge_yaml_config → with_overrides
        cfg = RunnerConfig.from_env()
        suite = load_files([EXAMPLE_YAML])
        cfg = cfg.merge_yaml_config(suite.yaml_config)
        cfg = cfg.with_overrides(
            llm_model="gpt-4o",
            max_steps=100,
            headless=False,
        )

        # CLI 覆盖生效
        assert cfg.llm_model == "gpt-4o"
        assert cfg.max_steps == 100
        assert cfg.headless is False

    def test_config_merge_env_config(self):
        """环境配置合并到 RunnerConfig。"""
        suite = load_files([EXAMPLE_YAML], env_name="dev")

        cfg = RunnerConfig.from_env()
        cfg = cfg.merge_yaml_config(suite.yaml_config)

        # 合并 dev 环境的 config 段
        dev_env = suite.environments["dev"]
        cfg = cfg.merge_env_config(dev_env)

        # dev 环境 config: headless=false, max_steps=50
        assert cfg.headless is False
        assert cfg.max_steps == 50


# ---------------------------------------------------------------------------
# 4. 执行流水线端到端测试（Mock LLM）
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestExecutionPipelineE2E:
    """执行流水线端到端测试（Mock LLM 和浏览器）。"""

    @pytest.mark.asyncio
    async def test_run_suite_with_mocked_agent(self):
        """完整执行流水线：解析 → 配置 → 执行 → 结果。"""
        from burunner.runner.orchestrator import run_suite

        # 1. 加载 example.yaml
        suite = load_files([EXAMPLE_YAML])
        assert len(suite.cases) > 0

        # 2. 创建 RunnerConfig
        cfg = RunnerConfig(
            llm_provider="openai",
            llm_model="test-model",
            max_steps=10,
            parallel=1,
        )
        cfg.ensure_dirs()

        # 3. Mock LLM
        mock_llm = MagicMock()

        # 4. Mock run_case 直接返回 PASSED 结果
        async def mock_run_case(case, config, llm):
            return CaseResult(
                case=case,
                status=CaseStatus.PASSED,
                elapsed=0.1,
                started_at=1000.0,
                stopped_at=1100.0,
            )

        with patch("burunner.runner.orchestrator.run_case", side_effect=mock_run_case):
            # 5. 调用 run_suite()
            result = await run_suite(suite, cfg, mock_llm)

        # 6. 验证 SuiteResult 结构正确
        assert isinstance(result, SuiteResult)
        assert result.total == 7
        assert result.passed == 7
        assert result.failed == 0
        assert result.is_success is True
        assert result.total_elapsed > 0

        # 7. 验证 CaseResult 结构
        for cr in result.case_results:
            assert isinstance(cr, CaseResult)
            assert cr.status == CaseStatus.PASSED
            assert cr.case.name in [c.name for c in suite.cases]

    @pytest.mark.asyncio
    async def test_run_case_success_path(self):
        """单用例成功执行路径。"""
        from burunner.runner.executor import run_case

        case = TestCase(
            name="成功测试",
            steps=[TestStep(text="访问 https://example.com")],
        )
        cfg = RunnerConfig(max_steps=10)
        cfg.ensure_dirs()
        mock_llm = MagicMock()
        mock_history = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            with patch("burunner.runner.executor.execute_agent", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_history

                with patch("burunner.runner.executor.HistoryParser") as mock_parser_cls:
                    mock_parser = MagicMock()
                    mock_parser.final_result_text = '{"success": true, "reason": "验证通过"}'
                    mock_parser.is_done = True
                    mock_parser.total_steps = 3
                    mock_parser.token_usage = MagicMock()
                    mock_parser.extract_step_outcomes.return_value = []
                    mock_parser_cls.return_value = mock_parser

                    with patch("burunner.runner.executor.VerdictJudge") as mock_judge_cls:
                        mock_judge = MagicMock()
                        mock_judge.judge.return_value = (
                            CaseStatus.PASSED, None)
                        mock_judge_cls.return_value = mock_judge

                        result = await run_case(case, cfg, mock_llm)

                        assert result.status == CaseStatus.PASSED
                        assert result.case == case
                        assert result.elapsed > 0

    @pytest.mark.asyncio
    async def test_run_case_failure_path(self):
        """单用例失败执行路径。"""
        from burunner.runner.executor import run_case

        case = TestCase(
            name="失败测试",
            steps=[TestStep(text="验证页面包含不存在的元素")],
        )
        cfg = RunnerConfig(max_steps=10)
        cfg.ensure_dirs()
        mock_llm = MagicMock()
        mock_history = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            with patch("burunner.runner.executor.execute_agent", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_history

                with patch("burunner.runner.executor.HistoryParser") as mock_parser_cls:
                    mock_parser = MagicMock()
                    mock_parser.final_result_text = '{"success": false, "reason": "元素未找到"}'
                    mock_parser.is_done = True
                    mock_parser.total_steps = 5
                    mock_parser.token_usage = MagicMock()
                    mock_parser.extract_step_outcomes.return_value = []
                    mock_parser_cls.return_value = mock_parser

                    with patch("burunner.runner.executor.VerdictJudge") as mock_judge_cls:
                        mock_judge = MagicMock()
                        mock_judge.judge.return_value = (
                            CaseStatus.FAILED, "元素未找到")
                        mock_judge_cls.return_value = mock_judge

                        with patch("burunner.runner.executor.capture_failure_screenshot", new_callable=AsyncMock) as mock_screenshot:
                            mock_screenshot.return_value = None

                            result = await run_case(case, cfg, mock_llm)

                            assert result.status == CaseStatus.FAILED
                            assert result.error_message == "元素未找到"

    @pytest.mark.asyncio
    async def test_run_case_timeout_path(self):
        """超时场景（达到 max_steps）。"""
        from burunner.runner.executor import run_case

        case = TestCase(
            name="超时测试",
            steps=[TestStep(text="执行很多步骤")],
        )
        cfg = RunnerConfig(max_steps=5)
        cfg.ensure_dirs()
        mock_llm = MagicMock()
        mock_history = MagicMock()

        with patch("burunner.runner.executor.managed_session") as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session)
            mock_session_ctx.return_value.__aexit__ = AsyncMock(
                return_value=False)

            with patch("burunner.runner.executor.execute_agent", new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_history

                with patch("burunner.runner.executor.HistoryParser") as mock_parser_cls:
                    mock_parser = MagicMock()
                    mock_parser.final_result_text = None
                    mock_parser.is_done = False
                    mock_parser.total_steps = 5  # 达到 max_steps
                    mock_parser.token_usage = MagicMock()
                    mock_parser.extract_step_outcomes.return_value = []
                    mock_parser_cls.return_value = mock_parser

                    with patch("burunner.runner.executor.VerdictJudge") as mock_judge_cls:
                        mock_judge = MagicMock()
                        mock_judge.judge.return_value = (
                            CaseStatus.INCOMPLETE, "超过最大步骤数")
                        mock_judge_cls.return_value = mock_judge

                        with patch("burunner.runner.executor.capture_failure_screenshot", new_callable=AsyncMock) as mock_screenshot:
                            mock_screenshot.return_value = None

                            result = await run_case(case, cfg, mock_llm)

                            assert result.status == CaseStatus.INCOMPLETE
                            assert "超过最大步骤数" in result.error_message


# ---------------------------------------------------------------------------
# 5. CLI validate 命令端到端测试
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCLIValidateE2E:
    """CLI validate 命令端到端测试。"""

    def test_validate_example_yaml(self):
        """validate 命令成功验证 example.yaml。"""
        from click.testing import CliRunner
        from burunner.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["validate", str(EXAMPLE_YAML)])
        assert result.exit_code == 0
        assert "OK" in result.output
        assert "7" in result.output  # 7 个用例

    def test_validate_invalid_yaml(self, tmp_path):
        """validate 命令检测无效 YAML。"""
        from click.testing import CliRunner
        from burunner.cli import main

        # 创建一个格式错误的 YAML（缺少 cases 字段）
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text(
            "config:\n  llm_model: test\n", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["validate", str(invalid_yaml)])
        assert result.exit_code != 0

    def test_validate_empty_cases_yaml(self, tmp_path):
        """validate 命令检测空用例。"""
        from click.testing import CliRunner
        from burunner.cli import main

        # 创建用例为空的 YAML
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("cases: []\n", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(main, ["validate", str(empty_yaml)])
        # 空用例应报告 0 个
        assert result.exit_code == 0
        assert "0" in result.output

    def test_validate_nonexistent_file(self):
        """validate 命令处理不存在的文件。"""
        from click.testing import CliRunner
        from burunner.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["validate", "/nonexistent/file.yaml"])
        # Click 的 Path(exists=True) 会在参数验证时报错
        assert result.exit_code != 0
