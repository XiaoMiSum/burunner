"""burunner 命令行入口。"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import click

from burunner import __version__
from burunner.config import RunnerConfig
from burunner.llm.provider import SUPPORTED_PROVIDERS, get_llm_model
from burunner.browser.session import SUPPORTED_BROWSER_CHANNELS
from burunner.notifier import NotifyPayload, create_notifier
from burunner.parser.yaml_parser import YamlParseError, load_files
from burunner.reporter.allure_reporter import AllureReporter
from burunner.reporter.console import print_case_line, print_summary
from burunner.runner.orchestrator import run_suite
from burunner.runner.progress import ProgressTracker
from burunner.runner.result import CaseResult, CaseStatus
from burunner.utils.logger import setup_logging


@click.group(help="基于 browser-use 的自然语言浏览器测试框架")
@click.version_option(__version__, prog_name="burunner")
def main() -> None:
    pass


@main.command("run", help="执行一个或多个 YAML 测试文件")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("-k", "--filter", "filter_", default=None, help="正则匹配用例 name")
@click.option("-t", "--tags", "tags", default=None, help="按标签过滤用例，多个标签用逗号分隔（OR 关系）")
@click.option("-p", "--parallel", default=None, type=int, help="并行度，默认 1")
@click.option(
    "--llm",
    "llm_provider",
    default=None,
    type=click.Choice(list(SUPPORTED_PROVIDERS), case_sensitive=False),
    help="LLM provider，默认从 .env 读取",
)
@click.option("--model", "llm_model", default=None, help="LLM model name，如 gpt-4o")
@click.option("--temperature", "llm_temperature", default=None, type=float, help="采样温度")
@click.option("--base-url", "llm_base_url", default=None, help="自定义 LLM endpoint")
@click.option("--api-key", "llm_api_key", default=None, help="LLM API key（覆盖环境变量）")
@click.option("--headless/--headed", default=None, help="是否无头模式（默认 headless）")
@click.option(
    "--browser", "browser_channel",
    default=None,
    type=click.Choice(list(SUPPORTED_BROWSER_CHANNELS), case_sensitive=False),
    help="浏览器类型（默认 chromium）",
)
@click.option("--max-steps", default=None, type=int, help="单个用例最大 Agent 步数")
@click.option("--case-timeout", default=None, type=int, help="单用例超时秒数（0=不限，默认不限）")
@click.option("--retry", "retry_count", default=None, type=int, help="异常用例自动重试次数（默认 0）")
@click.option(
    "--results-dir",
    default=None,
    type=click.Path(file_okay=False),
    help="Allure 结果目录，默认 ./allure-results",
)
@click.option("--keep-browser-open", is_flag=True, default=False, help="调试用：用例后保留浏览器")
@click.option("--no-vision", is_flag=True, default=False, help="禁用 use_vision")
@click.option("--no-progress", is_flag=True, default=False, help="关闭实时进度显示")
@click.option("-e", "--env", "env_name", default=None, help="运行环境（对应 YAML 中 environments 定义）")
@click.option("-v", "--verbose", is_flag=True, default=False)
def run_cmd(
    paths: tuple[str, ...],
    filter_: str | None,
    tags: str | None,
    parallel: int | None,
    llm_provider: str | None,
    llm_model: str | None,
    llm_temperature: float | None,
    llm_base_url: str | None,
    llm_api_key: str | None,
    headless: bool | None,
    browser_channel: str | None,
    max_steps: int | None,
    case_timeout: int | None,
    retry_count: int | None,
    results_dir: str | None,
    keep_browser_open: bool,
    no_vision: bool,
    no_progress: bool,
    env_name: str | None,
    verbose: bool,
) -> None:
    setup_logging(verbose=verbose)

    # 1) 解析 YAML
    # 确定运行环境：CLI --env > 环境变量 BURUNNER_ENV
    effective_env = env_name or os.environ.get("BURUNNER_ENV") or None
    try:
        suite = load_files([Path(p) for p in paths], env_name=effective_env)
    except YamlParseError as e:
        click.echo(f"YAML 解析失败: {e}", err=True)
        sys.exit(2)

    if not suite.cases:
        click.echo("未发现任何测试用例。", err=True)
        sys.exit(2)

    # 2) 组合配置: env -> yaml.config -> env_config -> CLI
    cfg = RunnerConfig.from_env().merge_yaml_config(suite.yaml_config)
    # 合并环境级配置（LLM、浏览器、cookies 等）
    active_env_config = (
        suite.environments.get(effective_env) if effective_env else None
    )
    cfg = cfg.merge_env_config(active_env_config)
    cfg = cfg.with_overrides(
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        headless=headless,
        browser_channel=browser_channel,
        parallel=parallel,
        max_steps=max_steps,
        case_timeout=case_timeout,
        retry_count=retry_count,
        filter=filter_,
        tags=[t.strip() for t in tags.split(
            ",") if t.strip()] if tags else None,
        results_dir=Path(results_dir) if results_dir else None,
        keep_browser_open=keep_browser_open or None,
        use_vision=False if no_vision else None,
        verbose=verbose or None,
    )
    cfg.source_files = [Path(p) for p in paths]
    cfg.ensure_dirs()

    click.echo(
        f"Provider={cfg.llm_provider}  Model={cfg.llm_model}  "
        f"Browser={cfg.browser_channel or 'chromium'}  "
        f"Parallel={cfg.parallel}  Headless={cfg.headless}  "
        f"Timeout={cfg.case_timeout or '∞'}s  Retry={cfg.retry_count}  "
        f"Env={effective_env or 'default'}  Cases={len(suite)}",
    )

    # 3) 创建 LLM
    try:
        llm = get_llm_model(
            cfg.llm_provider,
            model_name=cfg.llm_model,
            temperature=cfg.llm_temperature,
            base_url=cfg.llm_base_url,
            api_key=cfg.llm_api_key,
        )
    except Exception as e:  # noqa: BLE001
        click.echo(f"LLM 初始化失败: {e}", err=True)
        sys.exit(2)

    # 4) Allure reporter
    try:
        reporter = AllureReporter(cfg.results_dir)
        reporter.write_environment(
            {
                "burunner.version": __version__,
                "burunner.env": effective_env or "default",
                "llm.provider": cfg.llm_provider,
                "llm.model": cfg.llm_model,
                "browser": cfg.browser_channel or "chromium",
                "parallel": str(cfg.parallel),
                "headless": str(cfg.headless),
            }
        )
    except Exception as e:  # noqa: BLE001
        click.echo(f"Allure reporter 初始化失败（继续执行，仅缺少报告）: {e}", err=True)
        reporter = None  # type: ignore[assignment]

    # 5) 执行
    progress = ProgressTracker(
        total=len(suite),
        parallel=cfg.parallel,
        enabled=not no_progress,
    )

    async def on_start(case: Any, index: int) -> None:
        progress.on_case_start(case, index)

    async def on_complete(result: CaseResult) -> None:
        progress.on_case_complete(result)
        print_case_line(result)
        if reporter is not None:
            try:
                reporter.write_case(
                    result, provider=cfg.llm_provider, model=cfg.llm_model)
            except Exception as e:  # noqa: BLE001
                click.echo(
                    f"写入 Allure 结果失败 ({result.case.name}): {e}", err=True)

    try:
        suite_result = asyncio.run(
            run_suite(suite, cfg, llm, on_start=on_start, on_complete=on_complete))
    except KeyboardInterrupt:
        progress.finish()
        click.echo("\n已被用户中断。", err=True)
        sys.exit(130)

    progress.finish()
    print_summary(suite_result, results_dir=str(cfg.results_dir))

    # 6) 发送通知（不阻断主流程）
    notifier = create_notifier(cfg.notify_channel, cfg.notify_webhook)
    if notifier is not None:
        try:
            suite_name = (
                suite.source_files[0].stem if suite.source_files else "burunner"
            )
            failed_names = [
                r.case.name for r in suite_result.case_results
                if r.status in (CaseStatus.FAILED, CaseStatus.ERROR)
            ]
            payload = NotifyPayload(
                suite_name=suite_name,
                is_success=suite_result.is_success,
                total=suite_result.total,
                passed=suite_result.passed,
                failed=suite_result.failed,
                error=suite_result.error,
                total_elapsed=suite_result.total_elapsed,
                env_name=effective_env,
                failed_cases=failed_names,
            )
            ok = notifier.send(payload)
            if ok:
                click.echo("通知已发送。")
            else:
                click.echo("通知发送失败（详见日志）。", err=True)
        except Exception as e:  # noqa: BLE001
            click.echo(f"通知发送异常: {e}", err=True)

    sys.exit(0 if suite_result.is_success else 1)


@main.command("validate", help="仅校验 YAML 测试文件，不执行")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
def validate_cmd(paths: tuple[str, ...]) -> None:
    setup_logging(verbose=False)
    try:
        suite = load_files([Path(p) for p in paths])
    except YamlParseError as e:
        click.echo(f"YAML 解析失败: {e}", err=True)
        sys.exit(2)
    click.echo(f"OK: 共 {len(suite)} 个用例")
    for case in suite.cases:
        click.echo(
            f"  - {case.name}  ({len(case.steps)} steps)  source={case.source_file}"
        )


@main.command("version", help="打印版本号")
def version_cmd() -> None:
    click.echo(__version__)


if __name__ == "__main__":
    main()
