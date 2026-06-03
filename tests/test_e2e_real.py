"""
真实端到端测试 —— 使用 examples/ 中的 YAML 文件真实执行。

运行条件：
- 需要配置 BURUNNER_LLM_API_KEY 环境变量
- 需要安装 playwright 浏览器：playwright install chromium
- 需要网络连接

运行方式：
    pytest tests/test_e2e_real.py -v -s --timeout=300

或只运行标记的集成测试：
    pytest -m integration tests/test_e2e_real.py -v -s
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# 跳过条件：无 API Key 则跳过
pytestmark = [
    pytest.mark.slow,
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("BURUNNER_LLM_API_KEY"),
        reason="需要 BURUNNER_LLM_API_KEY 环境变量才能运行真实端到端测试",
    ),
]

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE_YAML = EXAMPLES_DIR / "example.yaml"


class TestRealExecution:
    """使用真实 LLM 和浏览器执行 examples/ 中的测试用例。"""

    def test_run_example_yaml_via_cli(self):
        """通过 CLI 执行 example.yaml 中的第一个测试用例（使用 -k 过滤）。

        仅执行第一个用例以加快测试速度，同时验证完整的 CLI 流水线。
        """
        from click.testing import CliRunner
        from burunner.cli import main

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [
            "run",
            str(EXAMPLE_YAML),
            "--headless",
            "--max-steps", "50",
            "--case-timeout", "120",
            "--no-progress",
            "-k", "百度搜索关键词",
            "-v",
        ])
        # 不强制 exit_code == 0（用例可能失败），但不应该崩溃（exit_code 2 表示解析/初始化异常）
        assert result.exit_code in (0, 1), (
            f"CLI 异常退出 (code={result.exit_code}):\n"
            f"stdout: {result.output}\n"
            f"stderr: {result.stderr}"
        )
        # 确认有输出（实际执行了）
        output = result.output
        assert any(kw in output for kw in ("PASS", "FAIL", "ERR", "INC")), (
            f"CLI 输出中未找到执行结果关键字:\n{output}"
        )

    @pytest.mark.asyncio
    async def test_run_single_case_programmatic(self):
        """通过编程方式执行单个用例，验证完整执行流程。"""
        from burunner.parser.yaml_parser import load_files
        from burunner.config import RunnerConfig
        from burunner.llm.provider import get_llm_model
        from burunner.runner.executor import run_case
        from burunner.runner.result import CaseStatus

        # 1. 加载 YAML
        suite = load_files([EXAMPLE_YAML])
        assert suite.cases, "example.yaml 中没有用例"

        # 2. 配置
        cfg = RunnerConfig.from_env()
        cfg = cfg.merge_yaml_config(suite.yaml_config)
        cfg = cfg.with_overrides(headless=True, max_steps=50, case_timeout=120)
        cfg.ensure_dirs()

        # 3. 获取 LLM
        llm = get_llm_model(
            cfg.llm_provider,
            model_name=cfg.llm_model,
            temperature=cfg.llm_temperature,
            base_url=cfg.llm_base_url,
            api_key=cfg.llm_api_key,
        )

        # 4. 执行第一个用例
        case = suite.cases[0]
        result = await run_case(case, cfg, llm)

        # 5. 验证结果结构
        assert result.status is not None, "执行结果 status 不应为 None"
        assert result.status in (
            CaseStatus.PASSED, CaseStatus.FAILED,
            CaseStatus.ERROR, CaseStatus.INCOMPLETE,
        ), f"非预期状态: {result.status}"
        assert result.elapsed > 0, "执行耗时应大于 0"
        assert result.case == case, "结果应关联到正确的用例"
        assert result.started_at > 0
        assert result.stopped_at >= result.started_at

        # 6. 验证步骤级追踪有数据
        if result.status in (CaseStatus.PASSED, CaseStatus.FAILED):
            assert len(result.step_outcomes) > 0, (
                f"步骤级追踪应该产生数据（status={result.status.value}）"
            )
            for outcome in result.step_outcomes:
                assert outcome.step_text, "步骤文本不应为空"
                assert outcome.status in (
                    "PASSED", "FAILED", "INCOMPLETE", "UNKNOWN"
                )

    @pytest.mark.asyncio
    async def test_run_suite_first_two_cases(self):
        """通过编程方式执行测试套件前 2 个用例，验证 run_suite 流水线。"""
        from burunner.parser.yaml_parser import load_files
        from burunner.config import RunnerConfig
        from burunner.llm.provider import get_llm_model
        from burunner.runner.orchestrator import run_suite
        from burunner.runner.result import CaseResult, SuiteResult

        # 1. 加载
        suite = load_files([EXAMPLE_YAML])

        # 2. 配置（限制并行度为 1，避免资源竞争）
        cfg = RunnerConfig.from_env()
        cfg = cfg.merge_yaml_config(suite.yaml_config)
        cfg = cfg.with_overrides(
            headless=True,
            parallel=1,
            max_steps=50,
            case_timeout=120,
            # 使用 -k 过滤只执行前两个用例
            filter="百度搜索关键词|搜索自动补全",
        )
        cfg.ensure_dirs()

        # 3. LLM
        llm = get_llm_model(
            cfg.llm_provider,
            model_name=cfg.llm_model,
            temperature=cfg.llm_temperature,
            base_url=cfg.llm_base_url,
            api_key=cfg.llm_api_key,
        )

        # 4. 执行套件
        suite_result = await run_suite(suite, cfg, llm)

        # 5. 验证 SuiteResult 结构
        assert isinstance(suite_result, SuiteResult)
        assert suite_result.total > 0, "应该有至少 1 个用例被执行"
        assert suite_result.total_elapsed > 0, "总耗时应大于 0"

        # 每个结果都应该有状态
        for r in suite_result.case_results:
            assert isinstance(r, CaseResult)
            assert r.status is not None
            assert r.elapsed >= 0
            assert r.case is not None
            assert r.case.name, "用例名不应为空"

    @pytest.mark.asyncio
    async def test_llm_initialization(self):
        """验证 LLM 能正确初始化（快速检查，不需要浏览器）。"""
        from burunner.config import RunnerConfig
        from burunner.llm.provider import get_llm_model

        cfg = RunnerConfig.from_env()
        suite_from_yaml = __import__(
            "burunner.parser.yaml_parser", fromlist=["load_files"]
        ).load_files([EXAMPLE_YAML])
        cfg = cfg.merge_yaml_config(suite_from_yaml.yaml_config)

        # 初始化 LLM 不应抛异常
        llm = get_llm_model(
            cfg.llm_provider,
            model_name=cfg.llm_model,
            temperature=cfg.llm_temperature,
            base_url=cfg.llm_base_url,
            api_key=cfg.llm_api_key,
        )
        assert llm is not None, "LLM 实例不应为 None"
