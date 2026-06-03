"""运行时配置与 .env 加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from burunner.parser.models import CookieItem, EnvConfig

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# 字段映射元数据：驱动 merge 方法的循环处理
# ---------------------------------------------------------------------------

# YAML config 段中可直接透传的简单字段（yaml key 与 dataclass 字段名一致）
_YAML_SIMPLE_FIELDS: tuple[str, ...] = (
    "llm_provider", "llm_model", "llm_temperature", "llm_base_url",
    "headless", "keep_browser_open", "user_data_dir",
    "parallel", "max_steps", "case_timeout", "retry_count", "retry_delay",
    "filter", "tags", "use_vision", "browser_use_log",
)

# 环境配置 config 段中可直接透传的简单字段
_ENV_CONFIG_SIMPLE_FIELDS: tuple[str, ...] = (
    "llm_provider", "llm_model", "llm_temperature", "llm_base_url",
    "llm_api_key", "headless", "keep_browser_open", "user_data_dir",
    "parallel", "max_steps", "use_vision",
)

# 需要 Path 类型转换的字段
_PATH_FIELDS: tuple[str, ...] = ("results_dir",)


def _collect_fields(source: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """从 source 字典中按字段列表收集存在的键值。"""
    return {key: source[key] for key in fields if key in source}


def _collect_path_fields(source: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """从 source 字典中收集需要 Path 转换的字段。"""
    return {key: Path(source[key]) for key in fields if key in source}


@dataclass
class RunnerConfig:
    """单次运行的全局配置。CLI 参数 > yaml config 段 > .env > 默认值。"""

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.0
    llm_base_url: str | None = None
    llm_api_key: str | None = None

    # 浏览器
    headless: bool = True
    keep_browser_open: bool = False
    user_data_dir: str | None = None
    browser_channel: str | None = None  # chromium/chrome/msedge 等

    # 执行
    parallel: int = 1
    max_steps: int = 0  # 0 表示动态计算（步骤数*20）
    case_timeout: int = 0  # 单用例超时（秒），0 表示不限制
    retry_count: int = 0  # 失败/错误用例重试次数，0 不重试
    retry_delay: float = 2.0  # 重试间隔（秒）
    filter: str | None = None
    tags: list[str] | None = None
    use_vision: bool = True

    # 输出
    results_dir: Path = field(default_factory=lambda: Path("./allure-results"))
    screenshots_dir: Path | None = None
    verbose: bool = False
    browser_use_log: bool = False

    # 预设 Cookies（全局级别）
    cookies: list["CookieItem"] = field(default_factory=list)

    # 通知
    notify_channel: str | None = None  # wecom / feishu / dingtalk
    notify_webhook: str | None = None  # Webhook URL

    # 多环境配置
    env_name: str | None = None  # 当前激活的环境名

    # 文件元数据（仅运行期填充）
    source_files: list[Path] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "RunnerConfig":
        """从 .env / 进程环境构建默认配置。"""
        load_dotenv(override=False)
        return cls(
            llm_provider=os.getenv("BURUNNER_LLM_PROVIDER", "openai"),
            llm_model=os.getenv("BURUNNER_LLM_MODEL", "gpt-4o"),
            llm_temperature=_env_float("BURUNNER_LLM_TEMPERATURE", 0.0),
            llm_base_url=os.getenv("BURUNNER_LLM_BASE_URL") or None,
            llm_api_key=os.getenv("BURUNNER_LLM_API_KEY") or None,
            headless=_env_bool("BURUNNER_HEADLESS", True),
            browser_channel=os.getenv("BURUNNER_BROWSER_CHANNEL") or None,
            parallel=_env_int("BURUNNER_PARALLEL", 1),
            max_steps=_env_int("BURUNNER_MAX_STEPS", 0),
            case_timeout=_env_int("BURUNNER_CASE_TIMEOUT", 0),
            retry_count=_env_int("BURUNNER_RETRY_COUNT", 0),
            retry_delay=_env_float("BURUNNER_RETRY_DELAY", 2.0),
            notify_channel=os.getenv("BURUNNER_NOTIFY_CHANNEL") or None,
            notify_webhook=os.getenv("BURUNNER_NOTIFY_WEBHOOK") or None,
            env_name=os.getenv("BURUNNER_ENV") or None,
            browser_use_log=_env_bool("BURUNNER_BROWSER_USE_LOG", False),
        )

    def merge_yaml_config(self, yaml_cfg: dict[str, Any] | None) -> "RunnerConfig":
        """合并 yaml 顶层 config: 段（仅当 CLI 未指定时生效）。"""
        if not yaml_cfg:
            return self
        # 简单字段透传 + Path 字段转换（元数据驱动）
        kwargs: dict[str, Any] = {}
        kwargs.update(_collect_fields(yaml_cfg, _YAML_SIMPLE_FIELDS))
        kwargs.update(_collect_path_fields(yaml_cfg, _PATH_FIELDS))
        # 解析顶层 cookies 配置
        if "cookies" in yaml_cfg and isinstance(yaml_cfg["cookies"], list):
            from burunner.parser.models import CookieItem
            cookies: list[CookieItem] = []
            for entry in yaml_cfg["cookies"]:
                if isinstance(entry, dict) and entry.get("name") and entry.get("domain"):
                    cookies.append(CookieItem(
                        name=str(entry["name"]).strip(),
                        value=str(entry.get("value", "")),
                        domain=str(entry["domain"]).strip(),
                        path=str(entry.get("path", "/")).strip() or "/",
                        secure=bool(entry.get("secure", False)),
                        http_only=bool(entry.get("httpOnly")
                                       or entry.get("http_only", False)),
                    ))
            if cookies:
                kwargs["cookies"] = cookies
        return replace(self, **kwargs)

    def with_overrides(self, **overrides: Any) -> "RunnerConfig":
        """CLI 显式覆盖（None 值忽略）。"""
        clean = {k: v for k, v in overrides.items() if v is not None}
        return replace(self, **clean)

    def merge_env_config(self, env_config: "EnvConfig | None") -> "RunnerConfig":
        """合并环境配置中的 config 段和 cookies。

        环境 config 覆盖 yaml 顶层 config，但优先级低于 CLI 参数。
        """
        if env_config is None:
            return self
        # 简单字段透传 + Path 字段转换（元数据驱动）
        kwargs: dict[str, Any] = {}
        kwargs.update(_collect_fields(
            env_config.config, _ENV_CONFIG_SIMPLE_FIELDS))
        kwargs.update(_collect_path_fields(env_config.config, _PATH_FIELDS))

        # 合并环境 cookies（环境 cookies 追加到全局 cookies 后面）
        if env_config.cookies:
            merged_cookies = list(self.cookies)
            seen_keys = {(c.name, c.domain) for c in merged_cookies}
            for cookie in env_config.cookies:
                key = (cookie.name, cookie.domain)
                if key not in seen_keys:
                    seen_keys.add(key)
                    merged_cookies.append(cookie)
            kwargs["cookies"] = merged_cookies

        if kwargs:
            return replace(self, **kwargs)
        return self

    def describe(self) -> str:
        """返回当前生效配置的摘要字符串（用于日志和调试）。"""
        lines = [
            "RunnerConfig:",
            f"  LLM: provider={self.llm_provider}, model={self.llm_model}, temperature={self.llm_temperature}",
            f"  Browser: headless={self.headless}, channel={self.browser_channel}",
            f"  Execution: parallel={self.parallel}, max_steps={self.max_steps},"
            f" timeout={self.case_timeout}, retry={self.retry_count}",
            f"  Output: results_dir={self.results_dir}",
        ]
        if self.notify_channel:
            lines.append(f"  Notify: channel={self.notify_channel}")
        return "\n".join(lines)

    def validate(self) -> None:
        """校验配置值合法性，不合法则抛出 ConfigurationError。"""
        from burunner.exceptions import ConfigurationError

        if self.llm_temperature is not None and (
            self.llm_temperature < 0.0 or self.llm_temperature > 2.0
        ):
            raise ConfigurationError(
                f"temperature 必须在 0.0~2.0 之间，当前值: {self.llm_temperature}"
            )
        if self.parallel < 1:
            raise ConfigurationError(
                f"parallel 必须 >= 1，当前值: {self.parallel}"
            )
        if self.max_steps < 0:
            raise ConfigurationError(
                f"max-steps 不能为负数，当前值: {self.max_steps}"
            )
        if self.case_timeout < 0:
            raise ConfigurationError(
                f"case-timeout 不能为负数，当前值: {self.case_timeout}"
            )
        if self.retry_count < 0:
            raise ConfigurationError(
                f"retry 不能为负数，当前值: {self.retry_count}"
            )

    def ensure_dirs(self) -> None:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        if self.screenshots_dir is None:
            self.screenshots_dir = self.results_dir / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
