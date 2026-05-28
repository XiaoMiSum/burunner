"""数据驱动测试 - 数据源加载与缓存。

支持的数据源格式：
  - CSV 文件：${csv(file.csv)}
  - JSON 文件：${json(file.json)}
  - YAML 文件：${yaml(file.yaml)}
  - 内联数据：data: [{...}, {...}]

支持数据过滤：
  - filter: "status == 'active'"
  - skip_if: "data.skip == true"
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Callable

import yaml

from burunner.exceptions import ConfigurationError

logger = logging.getLogger("burunner.datasource")


class DataSourceError(ConfigurationError):
    """数据源加载或解析错误。"""


# ---------------------------------------------------------------------------
# 数据源缓存（封装为实例，支持独立实例化便于测试）
# ---------------------------------------------------------------------------


class DataCache:
    """数据源缓存管理器，支持独立实例化便于测试。

    测试时可创建独立实例，避免测试间通过全局缓存互相污染。
    """

    def __init__(self) -> None:
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def get(self, key: str) -> list[dict[str, Any]] | None:
        """获取缓存数据，未命中返回 None。"""
        return self._cache.get(key)

    def set(self, key: str, data: list[dict[str, Any]]) -> None:
        """设置缓存数据。"""
        self._cache[key] = data

    def clear(self) -> None:
        """清空全部缓存。"""
        self._cache.clear()

    def __contains__(self, key: str) -> bool:
        return key in self._cache


# 默认全局实例（保持向后兼容）
_default_cache = DataCache()


def clear_cache() -> None:
    """清空数据源缓存。"""
    _default_cache.clear()


# ---------------------------------------------------------------------------
# 数据加载器
# ---------------------------------------------------------------------------


def _resolve_path(file_path: str, base_dir: Path | None) -> Path:
    """解析数据文件路径（支持相对路径和绝对路径）。"""
    p = Path(file_path)
    if p.is_absolute():
        return p
    if base_dir:
        return base_dir / p
    return Path.cwd() / p


# ---------------------------------------------------------------------------
# 模板方法 + 纯解析函数
# ---------------------------------------------------------------------------


def _resolve_and_load(
    file_path: str,
    base_dir: Path | None,
    parser_fn: Callable[[Path], list[dict[str, Any]]],
    format_label: str,
    cache: DataCache | None = None,
) -> list[dict[str, Any]]:
    """模板方法：路径解析 → 缓存检查 → 文件存在检查 → 解析 → 缓存存储。

    Args:
        file_path: 数据文件路径（相对或绝对）。
        base_dir: 相对路径的基准目录。
        parser_fn: 用于解析文件的函数。
        format_label: 格式标签（用于日志和错误信息）。
        cache: 可选的缓存实例，默认使用全局缓存。
    """
    _cache = cache or _default_cache
    resolved = _resolve_path(file_path, base_dir)
    cache_key = str(resolved.resolve())

    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    if not resolved.is_file():
        raise DataSourceError(f"{format_label} 数据文件不存在: {resolved}")

    data = parser_fn(resolved)

    _cache.set(cache_key, data)
    logger.debug("加载 %s 数据源: %s (%d 行)", format_label, resolved, len(data))
    return data


def _parse_csv(path: Path) -> list[dict[str, Any]]:
    """纯 CSV 解析逻辑。"""
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            rows = [dict(row) for row in reader]
    except Exception as e:
        raise DataSourceError(f"CSV 文件读取失败 ({path}): {e}") from e

    if not rows:
        raise DataSourceError(f"CSV 文件为空: {path}")

    return rows


def _parse_json(path: Path) -> list[dict[str, Any]]:
    """纯 JSON 解析逻辑。"""
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        raise DataSourceError(f"JSON 文件读取失败 ({path}): {e}") from e

    if not isinstance(data, list):
        raise DataSourceError(
            f"JSON 数据源必须是数组，得到 {type(data).__name__}: {path}")

    if not data:
        raise DataSourceError(f"JSON 数据源为空: {path}")

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise DataSourceError(
                f"JSON 数据源第 {i} 项必须是对象，得到 {type(item).__name__}")

    return data


def _parse_yaml(path: Path) -> list[dict[str, Any]]:
    """纯 YAML 解析逻辑。"""
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as e:
        raise DataSourceError(f"YAML 数据文件读取失败 ({path}): {e}") from e

    if not isinstance(data, list):
        raise DataSourceError(
            f"YAML 数据源必须是列表，得到 {type(data).__name__}: {path}")

    if not data:
        raise DataSourceError(f"YAML 数据源为空: {path}")

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise DataSourceError(
                f"YAML 数据源第 {i} 项必须是映射，得到 {type(item).__name__}")

    return data


# ---------------------------------------------------------------------------
# 公开 API（签名保持不变）
# ---------------------------------------------------------------------------


def load_csv(file_path: str, base_dir: Path | None = None) -> list[dict[str, Any]]:
    """加载 CSV 文件为字典列表。

    CSV 第一行为表头（字段名），后续行为数据。
    """
    return _resolve_and_load(file_path, base_dir, _parse_csv, "CSV")


def load_json(file_path: str, base_dir: Path | None = None) -> list[dict[str, Any]]:
    """加载 JSON 文件为字典列表。

    JSON 文件应为数组，每个元素为对象。
    """
    return _resolve_and_load(file_path, base_dir, _parse_json, "JSON")


def load_yaml_data(file_path: str, base_dir: Path | None = None) -> list[dict[str, Any]]:
    """加载 YAML 文件为字典列表。

    YAML 文件应为列表，每个元素为映射。
    """
    return _resolve_and_load(file_path, base_dir, _parse_yaml, "YAML")


def load_inline_data(data: list[Any], ctx: str) -> list[dict[str, Any]]:
    """验证并返回内联数据列表。"""
    if not isinstance(data, list):
        raise DataSourceError(f"{ctx}: 内联 'data' 必须是列表")
    if not data:
        raise DataSourceError(f"{ctx}: 内联 'data' 不能为空")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise DataSourceError(
                f"{ctx}: data[{i}] 必须是映射，得到 {type(item).__name__}")
    return data


# ---------------------------------------------------------------------------
# 数据源解析入口
# ---------------------------------------------------------------------------


def resolve_data_source(
    raw: Any,
    base_dir: Path | None = None,
    ctx: str = "",
) -> list[dict[str, Any]]:
    """根据数据源配置加载数据。

    支持的格式：
      - 字符串（文件路径）：根据后缀自动选择加载器
      - 列表：内联数据
      - 字典：含 type/file 字段的结构化定义
    """
    if isinstance(raw, list):
        return load_inline_data(raw, ctx)

    if isinstance(raw, str):
        # 自动根据后缀选择加载器
        lower = raw.lower().strip()
        if lower.endswith(".csv"):
            return load_csv(raw, base_dir)
        elif lower.endswith(".json"):
            return load_json(raw, base_dir)
        elif lower.endswith((".yaml", ".yml")):
            return load_yaml_data(raw, base_dir)
        else:
            raise DataSourceError(
                f"{ctx}: 无法识别数据源文件类型 '{raw}'，"
                "支持的后缀: .csv, .json, .yaml, .yml")

    if isinstance(raw, dict):
        ds_type = raw.get("type", "").strip().lower()
        file_path = raw.get("file", "").strip()

        if not ds_type:
            raise DataSourceError(f"{ctx}: 数据源字典必须包含 'type' 字段")
        if not file_path and ds_type != "inline":
            raise DataSourceError(f"{ctx}: 数据源字典必须包含 'file' 字段")

        if ds_type == "csv":
            return load_csv(file_path, base_dir)
        elif ds_type == "json":
            return load_json(file_path, base_dir)
        elif ds_type in ("yaml", "yml"):
            return load_yaml_data(file_path, base_dir)
        elif ds_type == "inline":
            inline = raw.get("data")
            if inline is None:
                raise DataSourceError(f"{ctx}: inline 数据源必须包含 'data' 字段")
            return load_inline_data(inline, ctx)
        else:
            raise DataSourceError(
                f"{ctx}: 不支持的数据源类型 '{ds_type}'，"
                "支持: csv, json, yaml, inline")

    raise DataSourceError(
        f"{ctx}: 'data_source' 必须是字符串、列表或字典，"
        f"得到 {type(raw).__name__}")


# ---------------------------------------------------------------------------
# 数据过滤
# ---------------------------------------------------------------------------


def filter_data_rows(
    rows: list[dict[str, Any]],
    filter_expr: str | None = None,
    skip_if_expr: str | None = None,
    ctx: str = "",
) -> list[dict[str, Any]]:
    """根据过滤条件和跳过条件筛选数据行。

    filter_expr: 保留满足条件的行（如 "status == 'active'"）
    skip_if_expr: 跳过满足条件的行（如 "data.skip == true"）
    """
    if not filter_expr and not skip_if_expr:
        return rows

    result: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        # 构建评估上下文
        eval_ctx = _build_eval_context(row)

        # 应用 filter（保留条件）
        if filter_expr:
            try:
                if not _safe_eval(filter_expr, eval_ctx):
                    continue
            except Exception as e:
                raise DataSourceError(
                    f"{ctx}: filter 表达式 '{filter_expr}' 对第 {i} 行求值失败: {e}"
                ) from e

        # 应用 skip_if（跳过条件）
        if skip_if_expr:
            try:
                if _safe_eval(skip_if_expr, eval_ctx):
                    continue
            except Exception as e:
                raise DataSourceError(
                    f"{ctx}: skip_if 表达式 '{skip_if_expr}' 对第 {i} 行求值失败: {e}"
                ) from e

        result.append(row)

    if not result:
        logger.warning("%s: 过滤后无数据行（原始 %d 行）", ctx, len(rows))

    return result


def _build_eval_context(row: dict[str, Any]) -> dict[str, Any]:
    """构建用于条件过滤的安全评估上下文。"""

    class DataProxy:
        """允许以 data.field 形式访问行数据。"""

        def __init__(self, row_data: dict[str, Any]):
            self._data = row_data

        def __getattr__(self, name: str) -> Any:
            if name.startswith("_"):
                return super().__getattribute__(name)
            return self._data.get(name)

    ctx: dict[str, Any] = {
        "__builtins__": {},
        "data": DataProxy(row),
        "true": True,
        "false": False,
        "True": True,
        "False": False,
        "none": None,
        "None": None,
    }
    # 将行字段直接注入上下文
    ctx.update(row)
    return ctx


def _safe_eval(expr: str, context: dict[str, Any]) -> bool:
    """安全执行条件表达式。"""
    try:
        return bool(eval(expr, context))  # noqa: S307
    except Exception as e:
        raise DataSourceError(f"条件表达式求值失败: '{expr}' -> {e}") from e


# ---------------------------------------------------------------------------
# 数据行转变量
# ---------------------------------------------------------------------------


def row_to_variables(row: dict[str, Any], prefix: str = "data") -> dict[str, str]:
    """将数据行转为变量字典（加 data. 前缀）。

    例如 {"username": "alice"} -> {"data.username": "alice"}
    """
    variables: dict[str, str] = {}
    for key, value in row.items():
        variables[f"{prefix}.{key}"] = str(value) if value is not None else ""
    return variables
