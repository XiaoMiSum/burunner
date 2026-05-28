"""并行调度与全局统计。

优化亮点：
- Worker Pool 模式：通过 asyncio.Queue 控制任务分发，避免一次性创建所有 Task
- 单用例超时：防止挂起的 Agent/浏览器永久占用并发槽位
- 自动重试：ERROR/FAILED 状态用例可配置重试次数
- 渐进启动：并发 worker 逐个启动，避免瞬时资源尖峰
- 异常隔离：单个 worker 异常不影响其他 worker
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from burunner.config import RunnerConfig
from burunner.parser.models import TestCase, TestSuite
from burunner.runner.executor import run_case
from burunner.runner.result import CaseResult, CaseStatus, SuiteResult

logger = logging.getLogger("burunner.orchestrator")

CaseHook = Callable[[CaseResult], Optional[Awaitable[None]]]
CaseStartHook = Callable[[TestCase, int], Optional[Awaitable[None]]]

# Worker 渐进启动间隔（秒）
_WORKER_STAGGER_INTERVAL = 0.3


async def _maybe_await(value: Any) -> None:
    if asyncio.iscoroutine(value):
        await value


async def _run_with_timeout(
    case: TestCase,
    cfg: RunnerConfig,
    llm: Any,
    timeout: int,
) -> CaseResult:
    """执行单个用例，带可选超时控制。"""
    if timeout > 0:
        try:
            return await asyncio.wait_for(
                run_case(case, cfg, llm),
                timeout=float(timeout),
            )
        except asyncio.TimeoutError:
            return CaseResult(
                case=case,
                status=CaseStatus.ERROR,
                elapsed=float(timeout),
                error_message=f"用例执行超时（>{timeout}s），已强制终止",
                started_at=time.time() * 1000 - timeout * 1000,
                stopped_at=time.time() * 1000,
            )
    return await run_case(case, cfg, llm)


async def _run_with_retry(
    case: TestCase,
    cfg: RunnerConfig,
    llm: Any,
    timeout: int,
    retry_count: int,
    retry_delay: float,
) -> CaseResult:
    """执行单用例，支持自动重试。

    仅对 ERROR 状态（框架/浏览器异常）进行重试，FAILED 状态（业务断言失败）不重试。
    """
    result = await _run_with_timeout(case, cfg, llm, timeout)

    attempts = 0
    while result.status == CaseStatus.ERROR and attempts < retry_count:
        attempts += 1
        logger.info(
            "用例 '%s' 执行异常，%0.1fs 后第 %d/%d 次重试...",
            case.name, retry_delay, attempts, retry_count,
        )
        if retry_delay > 0:
            await asyncio.sleep(retry_delay)
        result = await _run_with_timeout(case, cfg, llm, timeout)

    if attempts > 0:
        logger.info(
            "用例 '%s' 重试完成（共 %d 次），最终状态: %s",
            case.name, attempts, result.status.value,
        )
    return result


async def _worker(
    queue: asyncio.Queue[tuple[TestCase, int] | None],
    cfg: RunnerConfig,
    llm: Any,
    results: list[tuple[int, CaseResult]],
    results_lock: asyncio.Lock,
    on_start: CaseStartHook | None,
    on_complete: CaseHook | None,
) -> None:
    """Worker 协程：从队列中持续取任务执行，直到收到 sentinel（None）。"""
    timeout = cfg.case_timeout
    retry_count = cfg.retry_count
    retry_delay = cfg.retry_delay

    while True:
        item = await queue.get()
        if item is None:
            # Sentinel：退出信号
            queue.task_done()
            break

        case, index = item
        try:
            # on_start 回调
            if on_start is not None:
                try:
                    await _maybe_await(on_start(case, index))
                except Exception as e:  # noqa: BLE001
                    logger.warning("on_start 回调异常: %s", e)

            # 执行（含超时 + 重试）
            result = await _run_with_retry(
                case, cfg, llm, timeout, retry_count, retry_delay,
            )

            # on_complete 回调
            if on_complete is not None:
                try:
                    await _maybe_await(on_complete(result))
                except Exception as e:  # noqa: BLE001
                    logger.warning("on_complete 回调异常: %s", e)

            # 线程安全地存储结果（保留原始顺序索引）
            async with results_lock:
                results.append((index, result))

        except Exception as exc:  # noqa: BLE001
            # Worker 级兜底：确保不会因为意外异常导致 worker 退出
            logger.error("Worker 执行异常（用例: %s）: %s", case.name, exc)
            fallback = CaseResult(
                case=case,
                status=CaseStatus.ERROR,
                error_message=f"Worker 内部异常: {exc}",
                started_at=time.time() * 1000,
                stopped_at=time.time() * 1000,
            )
            async with results_lock:
                results.append((index, fallback))
            if on_complete is not None:
                try:
                    await _maybe_await(on_complete(fallback))
                except Exception:  # noqa: BLE001
                    pass
        finally:
            queue.task_done()


async def run_suite(
    suite: TestSuite,
    cfg: RunnerConfig,
    llm: Any,
    *,
    on_start: CaseStartHook | None = None,
    on_complete: CaseHook | None = None,
) -> SuiteResult:
    """Worker Pool 模式并发执行 suite 中所有用例并聚合结果。

    相比简单 gather + Semaphore 方式的优势：
    1. 任务按需分发，不会一次性创建所有 Task 对象
    2. 支持单用例超时和自动重试
    3. Worker 渐进启动避免资源尖峰
    4. 单个 Worker 异常不影响其他 Worker
    5. 结果按原始用例顺序排列
    """
    suite = suite.filter_by_name(cfg.filter)
    suite = suite.filter_by_tags(cfg.tags)

    cases = suite.cases
    if not cases:
        return SuiteResult(case_results=[], total_elapsed=0.0)

    parallel = max(1, int(cfg.parallel or 1))
    # Worker 数量不超过用例数量
    worker_count = min(parallel, len(cases))

    t0 = time.perf_counter()

    # 创建任务队列
    queue: asyncio.Queue[tuple[TestCase, int] | None] = asyncio.Queue()
    for idx, case in enumerate(cases):
        await queue.put((case, idx + 1))

    # 放入 sentinel 信号（每个 worker 一个）
    for _ in range(worker_count):
        await queue.put(None)

    # 结果存储（线程安全）
    results: list[tuple[int, CaseResult]] = []
    results_lock = asyncio.Lock()

    # 渐进启动 Workers
    workers: list[asyncio.Task[None]] = []
    for i in range(worker_count):
        task = asyncio.create_task(
            _worker(queue, cfg, llm, results,
                    results_lock, on_start, on_complete),
            name=f"burunner-worker-{i}",
        )
        workers.append(task)
        # 除最后一个外，逐个间隔启动避免资源尖峰
        if i < worker_count - 1 and worker_count > 1:
            await asyncio.sleep(_WORKER_STAGGER_INTERVAL)

    # 等待所有 worker 完成
    await asyncio.gather(*workers, return_exceptions=True)

    elapsed = time.perf_counter() - t0

    # 按原始用例顺序排列结果
    results.sort(key=lambda x: x[0])
    ordered_results = [r for _, r in results]

    return SuiteResult(case_results=ordered_results, total_elapsed=elapsed)
