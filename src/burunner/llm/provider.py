"""LLM Provider 工厂 — 基于注册表模式 (Registry) + 策略模式 (Strategy)。

优先使用 browser-use 内置的 LLM 抽象 (browser_use.llm.*)，这些类已经实现了
Agent 所需的协议；具体可用类型随 browser-use 版本而定，未安装的子依赖会
在 lazy import 时给出明确报错提示。

设计:
- ProviderSpec: 声明式描述每个 provider 的元数据（类候选、默认端点、环境变量回退）
- PROVIDER_REGISTRY: 所有 provider 的注册表，新增 provider 只需添加一条记录
- _build_instance: 统一构建逻辑，消除重复代码
- 特殊 provider 通过 `customizer` 回调钩子扩展行为
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from burunner.exceptions import ConfigurationError

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LLMProviderError(ConfigurationError):
    """Provider 加载或参数不合法。"""


def _missing_dep(provider: str, package: str, exc: Exception) -> LLMProviderError:
    return LLMProviderError(
        f"加载 LLM provider '{provider}' 失败：缺少依赖 '{package}'。"
        f" 请执行 `pip install {package}` 后重试。原始错误: {exc}"
    )


# ---------------------------------------------------------------------------
# Class resolver
# ---------------------------------------------------------------------------


def _resolve(name: str, *candidates: str) -> Any:
    """从 browser_use.llm 中按候选顺序查找类。"""
    import importlib

    mod = importlib.import_module("browser_use.llm")
    for cand in candidates:
        cls = getattr(mod, cand, None)
        if cls is not None:
            return cls
    raise LLMProviderError(
        f"当前 browser-use 版本未提供 {name} 对应的 chat class（尝试: {candidates}）。"
        f" 请升级 browser-use 或更换 provider。"
    )


# ---------------------------------------------------------------------------
# Provider specification (Registry Pattern)
# ---------------------------------------------------------------------------

# Customizer 签名: (kwargs, base_url, api_key, extra) -> None
# 用于对特殊 provider 注入额外逻辑（如 azure 的 api_version、ibm 的 headers）
Customizer = Callable[[dict[str, Any], Optional[str],
                       Optional[str], dict[str, Any]], None]


@dataclass(frozen=True)
class ProviderSpec:
    """声明式 Provider 规格，描述如何构建 LLM 实例。"""

    # 类解析
    class_candidates: tuple[str, ...]
    # 回退类候选（当主类解析失败时使用，如 deepseek -> ChatOpenAI）
    fallback_candidates: tuple[str, ...] = ()

    # 默认端点（为空表示不强制设置 base_url）
    default_endpoint: str | None = None

    # endpoint 参数名（azure 用 azure_endpoint）
    endpoint_param: str = "base_url"

    # 是否需要 API key（ollama 不需要）
    requires_api_key: bool = True

    # 特殊逻辑钩子
    customizer: Optional[Customizer] = None


# ---------------------------------------------------------------------------
# Customizer hooks (Strategy Pattern)
# ---------------------------------------------------------------------------


def _azure_customizer(
    kwargs: dict[str, Any],
    base_url: str | None,
    api_key: str | None,
    extra: dict[str, Any],
) -> None:
    """Azure OpenAI 额外处理: api_version。"""
    api_version = extra.pop("api_version", None) or os.getenv(
        "BURUNNER_AZURE_API_VERSION", "2024-08-01-preview"
    )
    kwargs["api_version"] = api_version


def _ibm_customizer(
    kwargs: dict[str, Any],
    base_url: str | None,
    api_key: str | None,
    extra: dict[str, Any],
) -> None:
    """IBM watsonx 额外处理: project_id header。"""
    project_id = os.getenv("BURUNNER_IBM_PROJECT_ID")
    if project_id:
        kwargs["extra_headers"] = {"X-IBM-Project-Id": project_id}


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        class_candidates=("ChatOpenAI",),
    ),
    "azure_openai": ProviderSpec(
        class_candidates=("ChatAzureOpenAI", "ChatAzureOpenAi"),
        endpoint_param="azure_endpoint",
        default_endpoint=None,
        customizer=_azure_customizer,
    ),
    "anthropic": ProviderSpec(
        class_candidates=("ChatAnthropic",),
    ),
    "google": ProviderSpec(
        class_candidates=("ChatGoogle", "ChatGemini"),
    ),
    "deepseek": ProviderSpec(
        class_candidates=("ChatDeepSeek",),
        fallback_candidates=("ChatOpenAI",),
        default_endpoint="https://api.deepseek.com",
    ),
    "ollama": ProviderSpec(
        class_candidates=("ChatOllama",),
        requires_api_key=False,
    ),
    "grok": ProviderSpec(
        class_candidates=("ChatOpenAI",),
        default_endpoint="https://api.x.ai/v1",
    ),
    "mistral": ProviderSpec(
        class_candidates=("ChatMistral", "ChatMistralAI"),
        fallback_candidates=("ChatOpenAI",),
    ),
    "alibaba": ProviderSpec(
        class_candidates=("ChatOpenAI",),
        default_endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "modelscope": ProviderSpec(
        class_candidates=("ChatOpenAI",),
        default_endpoint="https://api-inference.modelscope.cn/v1",
    ),
    "moonshot": ProviderSpec(
        class_candidates=("ChatOpenAI",),
        default_endpoint="https://api.moonshot.cn/v1",
    ),
    "siliconflow": ProviderSpec(
        class_candidates=("ChatOpenAI",),
        default_endpoint="https://api.siliconflow.cn/v1/",
    ),
    "ibm": ProviderSpec(
        class_candidates=("ChatOpenAI",),
        default_endpoint="https://us-south.ml.cloud.ibm.com",
        customizer=_ibm_customizer,
    ),
    "unbound": ProviderSpec(
        class_candidates=("ChatOpenAI",),
        default_endpoint="https://api.getunbound.ai",
    ),
}

SUPPORTED_PROVIDERS = tuple(PROVIDER_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Unified builder
# ---------------------------------------------------------------------------


def _resolve_api_key(
    api_key: str | None, spec: ProviderSpec
) -> str | None:
    """按优先级解析 API key: 显式参数 > BURUNNER_LLM_API_KEY 环境变量。"""
    if api_key:
        return api_key
    return os.getenv("BURUNNER_LLM_API_KEY")


def _resolve_endpoint(
    base_url: str | None, spec: ProviderSpec
) -> str | None:
    """按优先级解析 endpoint: 显式参数 > BURUNNER_LLM_BASE_URL 环境变量 > 默认值。"""
    if base_url:
        return base_url
    unified = os.getenv("BURUNNER_LLM_BASE_URL")
    if unified:
        return unified
    return spec.default_endpoint


def _build_instance(
    provider: str,
    spec: ProviderSpec,
    common: dict[str, Any],
    base_url: str | None,
    api_key: str | None,
    extra: dict[str, Any],
) -> Any:
    """统一构建 LLM 实例。"""
    # 1. 解析类（支持 fallback）
    try:
        cls = _resolve(provider, *spec.class_candidates)
    except LLMProviderError:
        if spec.fallback_candidates:
            cls = _resolve(provider, *spec.fallback_candidates)
        else:
            raise

    # 2. 构建 kwargs
    kwargs = dict(common)

    # 3. API key
    if spec.requires_api_key:
        resolved_key = _resolve_api_key(api_key, spec)
        kwargs["api_key"] = resolved_key

    # 4. Endpoint
    resolved_endpoint = _resolve_endpoint(base_url, spec)
    if resolved_endpoint:
        kwargs[spec.endpoint_param] = resolved_endpoint

    # 5. Customizer hook
    if spec.customizer:
        spec.customizer(kwargs, base_url, api_key, extra)

    return cls(**kwargs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_llm_model(
    provider: str,
    *,
    model_name: str,
    temperature: float = 0.0,
    base_url: str | None = None,
    api_key: str | None = None,
    **extra: Any,
) -> Any:
    """根据 provider 返回 browser-use Agent 可直接使用的 LLM 实例。

    Args:
        provider: 见 SUPPORTED_PROVIDERS。
        model_name: 模型名，如 'gpt-4o'、'claude-3-5-sonnet-latest'。
        temperature: 采样温度。
        base_url: 自定义 endpoint（OpenAI 兼容场景常用）。
        api_key: 显式 API key；为 None 时按 provider 读取对应环境变量。
        **extra: 透传给底层 chat class 的额外参数。
    """
    provider = (provider or "").lower().strip()
    if provider not in PROVIDER_REGISTRY:
        raise LLMProviderError(
            f"不支持的 LLM provider: '{provider}'。可选: {', '.join(SUPPORTED_PROVIDERS)}"
        )

    spec = PROVIDER_REGISTRY[provider]
    common: dict[str, Any] = {"model": model_name, "temperature": temperature}
    common.update({k: v for k, v in extra.items() if v is not None})

    try:
        return _build_instance(provider, spec, common, base_url, api_key, extra)
    except ImportError as e:
        raise _missing_dep(provider, getattr(e, "name", "unknown"), e) from e
