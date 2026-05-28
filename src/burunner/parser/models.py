"""测试用例数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TestStep:
    """单个测试步骤——自然语言描述。"""

    text: str

    def __str__(self) -> str:
        return self.text


@dataclass
class CookieItem:
    """预设 Cookie 条目。"""

    name: str
    value: str
    domain: str
    path: str = "/"
    secure: bool = False
    http_only: bool = False

    def to_playwright_cookie(self) -> dict[str, Any]:
        """转换为 Playwright add_cookies 所需的字典格式。"""
        return {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path,
            "secure": self.secure,
            "httpOnly": self.http_only,
        }


@dataclass
class EnvConfig:
    """单个环境的配置定义。"""

    name: str
    inherit: str | None = None  # 继承的基础环境名
    variables: dict[str, str] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    cookies: list["CookieItem"] = field(default_factory=list)


@dataclass
class TestTemplate:
    """可被用例继承的预设，包含可共享的前置步骤。"""

    name: str
    description: str | None = None
    steps: list[TestStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    cookies: list[CookieItem] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)


@dataclass
class DataDrivenConfig:
    """数据驱动测试配置。"""

    source: Any = None  # 数据源（文件路径字符串、内联列表或结构化字典）
    filter_expr: str | None = None  # 保留条件
    skip_if_expr: str | None = None  # 跳过条件
    name_field: str | None = None  # 用于命名的数据字段


@dataclass
class TestCase:
    """单个测试用例。"""

    name: str
    description: str | None = None
    steps: list[TestStep] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    cookies: list[CookieItem] = field(default_factory=list)
    source_file: Path | None = None
    extends: str | None = None
    variables: dict[str, str] = field(default_factory=dict)
    # 数据驱动相关
    data_driven: DataDrivenConfig | None = None
    data_row: dict[str, Any] | None = None  # 展开后每个实例对应的数据行
    data_index: int | None = None  # 展开后的数据行索引

    def build_task_prompt(self) -> str:
        """将自然语言步骤拼接为传给 Agent 的任务描述。

        强制结尾要求 Agent 以 done(success=...) 结束并输出
        `{"success": ..., "reason": ...}` 形式的 JSON 结果。
        """
        lines: list[str] = []
        if self.description:
            lines.append(f"测试目标: {self.description}")
        lines.append(f"测试用例: {self.name}")
        lines.append("请严格按以下步骤逐项执行:")
        for idx, step in enumerate(self.steps, 1):
            lines.append(f"{idx}. {step.text}")
        lines.append("")
        lines.append(
            '完成后必须以一行 JSON 输出最终结论: {"success": true|false, "reason": "..."},'
            " 然后调用 done(success=true) 或 done(success=false) 收尾。"
            " 任一步骤无法完成或断言失败则 success=false 并在 reason 中给出原因。"
        )
        return "\n".join(lines)


@dataclass
class TestSuite:
    """一组测试用例的集合。"""

    cases: list[TestCase] = field(default_factory=list)
    templates: dict[str, TestTemplate] = field(default_factory=dict)
    source_files: list[Path] = field(default_factory=list)
    yaml_config: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    environments: dict[str, EnvConfig] = field(default_factory=dict)
    active_env: str | None = None  # 当前激活的环境名

    def filter_by_name(self, pattern: str | None) -> "TestSuite":
        """按正则匹配 case.name 过滤。"""
        if not pattern:
            return self
        import re

        regex = re.compile(pattern)
        return TestSuite(
            cases=[c for c in self.cases if regex.search(c.name)],
            source_files=self.source_files,
            yaml_config=self.yaml_config,
        )

    def filter_by_tags(self, tags: list[str] | None) -> "TestSuite":
        """按标签过滤用例，只要用例包含指定标签中的任意一个即匹配。"""
        if not tags:
            return self
        tag_set = {t.strip().lower() for t in tags if t.strip()}
        if not tag_set:
            return self
        return TestSuite(
            cases=[
                c for c in self.cases
                if tag_set & {t.strip().lower() for t in c.tags}
            ],
            source_files=self.source_files,
            yaml_config=self.yaml_config,
        )

    def __len__(self) -> int:
        return len(self.cases)
