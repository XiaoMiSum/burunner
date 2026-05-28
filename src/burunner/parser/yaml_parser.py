"""YAML 测试用例解析器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml

from burunner.exceptions import ConfigurationError
from burunner.parser.models import (
    CookieItem, DataDrivenConfig, EnvConfig,
    TestCase, TestStep, TestSuite, TestTemplate,
)
from burunner.parser.variables import VariableError, resolve_text
from burunner.parser.datasource import (
    DataSourceError, filter_data_rows, resolve_data_source, row_to_variables,
)


class YamlParseError(ConfigurationError):
    """YAML 测试用例校验失败。"""


def _coerce_step(raw: Any, ctx: str) -> TestStep:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise YamlParseError(f"{ctx}: 步骤不能为空字符串")
        return TestStep(text=text)
    if isinstance(raw, dict):
        text = raw.get("text") or raw.get("step") or raw.get("action")
        if not isinstance(text, str) or not text.strip():
            raise YamlParseError(f"{ctx}: 步骤字典必须包含非空的 'text' 字段")
        return TestStep(text=text.strip())
    raise YamlParseError(
        f"{ctx}: 步骤必须是字符串或带 'text' 的字典，得到 {type(raw).__name__}")


def _coerce_cookies(raw: Any, ctx: str) -> list[CookieItem]:
    """解析 cookies 列表，返回 CookieItem 列表。"""
    if not raw:
        return []
    if not isinstance(raw, list):
        raise YamlParseError(f"{ctx}: 'cookies' 必须是列表")
    items: list[CookieItem] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise YamlParseError(
                f"{ctx} cookie#{i}: 每个 cookie 必须是字典，得到 {type(entry).__name__}")
        name = entry.get("name")
        value = entry.get("value")
        domain = entry.get("domain")
        if not isinstance(name, str) or not name.strip():
            raise YamlParseError(f"{ctx} cookie#{i}: 'name' 必须是非空字符串")
        if not isinstance(value, str):
            raise YamlParseError(f"{ctx} cookie#{i}: 'value' 必须是字符串")
        if not isinstance(domain, str) or not domain.strip():
            raise YamlParseError(f"{ctx} cookie#{i}: 'domain' 必须是非空字符串")
        items.append(CookieItem(
            name=name.strip(),
            value=value,
            domain=domain.strip(),
            path=str(entry.get("path", "/")).strip() or "/",
            secure=bool(entry.get("secure", False)),
            http_only=bool(entry.get("httpOnly")
                           or entry.get("http_only", False)),
        ))
    return items


def _coerce_preset(raw: Any, name: str, source: Path) -> TestTemplate:
    """解析单个预设定义。"""
    if not isinstance(raw, dict):
        raise YamlParseError(
            f"{source} preset({name}): 预设必须是字典，得到 {type(raw).__name__}"
        )

    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        raise YamlParseError(
            f"{source} preset({name}): 预设必须包含非空的 'steps' 列表"
        )

    steps = [_coerce_step(s, f"{source} preset({name}) step{j+1}")
             for j, s in enumerate(steps_raw)]

    description = raw.get("description")
    if description is not None and not isinstance(description, str):
        raise YamlParseError(
            f"{source} preset({name}): 'description' 必须是字符串")

    tags_raw = raw.get("tags") or []
    if not isinstance(tags_raw, list) or not all(isinstance(t, str) for t in tags_raw):
        raise YamlParseError(f"{source} preset({name}): 'tags' 必须是字符串列表")

    tpl_config = raw.get("config") or {}
    if not isinstance(tpl_config, dict):
        raise YamlParseError(f"{source} preset({name}): 'config' 必须是字典")

    cookies = _coerce_cookies(raw.get("cookies"), f"{source} preset({name})")

    # 解析预设级变量定义
    variables = raw.get("variables") or {}
    if not isinstance(variables, dict):
        raise YamlParseError(f"{source} preset({name}): 'variables' 必须是字典")
    # 确保变量值都是字符串
    variables = {str(k): str(v) for k, v in variables.items()}

    return TestTemplate(
        name=name,
        description=description.strip() if isinstance(description, str) else None,
        steps=steps,
        tags=list(tags_raw),
        config=tpl_config,
        cookies=cookies,
        variables=variables,
    )


def _coerce_case(raw: Any, source: Path, idx: int) -> TestCase:
    if not isinstance(raw, dict):
        raise YamlParseError(
            f"{source}#{idx}: 用例必须是字典，得到 {type(raw).__name__}"
        )
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise YamlParseError(f"{source}#{idx}: 用例必须包含非空的 'name' 字段")

    # extends 字段可选：当用例继承模板时，steps 可为空（将在解析后合并）
    extends = raw.get("extends")
    if extends is not None and (not isinstance(extends, str) or not extends.strip()):
        raise YamlParseError(f"{source}#{idx}({name}): 'extends' 必须是非空字符串")

    steps_raw = raw.get("steps") or []
    if not isinstance(steps_raw, list):
        raise YamlParseError(f"{source}#{idx}({name}): 'steps' 必须是列表")

    # 没有 extends 时，steps 不能为空
    if not extends and not steps_raw:
        raise YamlParseError(f"{source}#{idx}({name}): 用例必须包含非空的 'steps' 列表")

    steps = [_coerce_step(s, f"{source}#{idx}({name}) step{j+1}")
             for j, s in enumerate(steps_raw)]

    description = raw.get("description")
    if description is not None and not isinstance(description, str):
        raise YamlParseError(f"{source}#{idx}({name}): 'description' 必须是字符串")

    tags_raw = raw.get("tags") or []
    if not isinstance(tags_raw, list) or not all(isinstance(t, str) for t in tags_raw):
        raise YamlParseError(f"{source}#{idx}({name}): 'tags' 必须是字符串列表")

    case_config = raw.get("config") or {}
    if not isinstance(case_config, dict):
        raise YamlParseError(f"{source}#{idx}({name}): 'config' 必须是字典")

    cookies = _coerce_cookies(raw.get("cookies"), f"{source}#{idx}({name})")

    # 解析用例级变量定义
    variables = raw.get("variables") or {}
    if not isinstance(variables, dict):
        raise YamlParseError(f"{source}#{idx}({name}): 'variables' 必须是字典")
    variables = {str(k): str(v) for k, v in variables.items()}

    # 解析数据驱动配置
    data_driven: DataDrivenConfig | None = None
    data_source_raw = raw.get("data_source") or raw.get("data")
    if data_source_raw is not None:
        filter_expr = raw.get("data_filter") or raw.get("filter")
        skip_if_expr = raw.get("data_skip_if") or raw.get("skip_if")
        name_field = raw.get("data_name_field") or raw.get("name_field")
        if filter_expr is not None and not isinstance(filter_expr, str):
            raise YamlParseError(
                f"{source}#{idx}({name}): 'data_filter' 必须是字符串")
        if skip_if_expr is not None and not isinstance(skip_if_expr, str):
            raise YamlParseError(
                f"{source}#{idx}({name}): 'data_skip_if' 必须是字符串")
        if name_field is not None and not isinstance(name_field, str):
            raise YamlParseError(
                f"{source}#{idx}({name}): 'data_name_field' 必须是字符串")
        data_driven = DataDrivenConfig(
            source=data_source_raw,
            filter_expr=filter_expr,
            skip_if_expr=skip_if_expr,
            name_field=name_field,
        )

    return TestCase(
        name=name.strip(),
        description=description.strip() if isinstance(description, str) else None,
        steps=steps,
        tags=list(tags_raw),
        config=case_config,
        cookies=cookies,
        source_file=source,
        extends=extends.strip() if extends else None,
        variables=variables,
        data_driven=data_driven,
    )


def load_yaml(path: str | Path) -> tuple[list[TestCase], dict[str, Any], dict[str, TestTemplate]]:
    """解析单个 YAML 文件，返回 (cases, top_level_config, presets)。"""
    p = Path(path)
    if not p.is_file():
        raise YamlParseError(f"YAML 文件不存在: {p}")

    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if data is None:
        return [], {}, {}

    yaml_config: dict[str, Any] = {}
    templates: dict[str, TestTemplate] = {}
    cases_raw: list[Any]

    if isinstance(data, list):
        cases_raw = data
    elif isinstance(data, dict):
        # 解析预设步骤定义
        presets_raw = data.get("presets")
        if presets_raw is not None:
            if not isinstance(presets_raw, dict):
                raise YamlParseError(f"{p}: 'presets' 必须是字典（预设名 -> 预设定义）")
            for tpl_name, tpl_def in presets_raw.items():
                if not isinstance(tpl_name, str) or not tpl_name.strip():
                    raise YamlParseError(f"{p}: 预设名称必须是非空字符串")
                templates[tpl_name.strip()] = _coerce_preset(
                    tpl_def, tpl_name.strip(), p)

        # 解析多环境配置
        envs_raw = data.get("environments")
        if envs_raw is not None:
            if not isinstance(envs_raw, dict):
                raise YamlParseError(f"{p}: 'environments' 必须是字典（环境名 -> 环境配置）")
            yaml_config["_environments"] = envs_raw

        if "cases" in data:
            cases_raw = data.get("cases") or []
            if not isinstance(cases_raw, list):
                raise YamlParseError(f"{p}: 'cases' 必须是列表")
            cfg = data.get("config")
            if cfg is not None:
                if not isinstance(cfg, dict):
                    raise YamlParseError(f"{p}: 顶层 'config' 必须是字典")
                yaml_config = {**yaml_config, **cfg}
            # 解析顶层 variables 到 yaml_config 中
            top_vars = data.get("variables")
            if top_vars is not None:
                if not isinstance(top_vars, dict):
                    raise YamlParseError(f"{p}: 顶层 'variables' 必须是字典")
                yaml_config["_variables"] = {
                    str(k): str(v) for k, v in top_vars.items()}
        else:
            raise YamlParseError(
                f"{p}: 顶层结构必须是 list 或包含 'cases' 字段的 dict"
            )
    else:
        raise YamlParseError(f"{p}: 顶层结构必须是 list 或 dict")

    cases = [_coerce_case(c, p, i) for i, c in enumerate(cases_raw)]
    return cases, yaml_config, templates


def _resolve_extends(case: TestCase, presets: dict[str, TestTemplate], source: Path) -> TestCase:
    """解析用例的预设继承，将预设的前置步骤合并到用例步骤前面。"""
    if not case.extends:
        return case

    preset = presets.get(case.extends)
    if preset is None:
        raise YamlParseError(
            f"{source}({case.name}): 引用的预设 '{case.extends}' 不存在"
        )

    # 合并步骤：预设步骤在前，用例自身步骤在后
    merged_steps = list(preset.steps) + list(case.steps)

    # 合并 tags：预设 tags + 用例 tags（去重保序）
    seen_tags: set[str] = set()
    merged_tags: list[str] = []
    for tag in preset.tags + case.tags:
        lower_tag = tag.strip().lower()
        if lower_tag not in seen_tags:
            seen_tags.add(lower_tag)
            merged_tags.append(tag)

    # 合并 config：预设 config 被用例 config 覆盖
    merged_config = {**preset.config, **case.config}

    # 合并 cookies：预设 cookies + 用例 cookies（用例同名 cookie 覆盖预设的）
    seen_cookie_keys: set[tuple[str, str]] = set()
    merged_cookies: list[CookieItem] = []
    # 用例 cookies 优先（后加入覆盖前面的）
    for cookie in case.cookies + preset.cookies:
        key = (cookie.name, cookie.domain)
        if key not in seen_cookie_keys:
            seen_cookie_keys.add(key)
            merged_cookies.append(cookie)

    # 合并 variables：预设 variables 被用例 variables 覆盖
    merged_variables = {**preset.variables, **case.variables}

    # description 优先使用用例自身的，若无则使用预设的
    description = case.description or preset.description

    return TestCase(
        name=case.name,
        description=description,
        steps=merged_steps,
        tags=merged_tags,
        config=merged_config,
        cookies=merged_cookies,
        source_file=case.source_file,
        extends=case.extends,
        variables=merged_variables,
        data_driven=case.data_driven,
        data_row=case.data_row,
        data_index=case.data_index,
    )


def _parse_environments(
    raw_envs: dict[str, Any] | None, source: Path,
) -> dict[str, EnvConfig]:
    """解析 environments 配置段，返回环境名到 EnvConfig 的映射。"""
    if not raw_envs:
        return {}
    if not isinstance(raw_envs, dict):
        raise YamlParseError(f"{source}: 'environments' 必须是字典")

    envs: dict[str, EnvConfig] = {}
    for env_name, env_def in raw_envs.items():
        if not isinstance(env_name, str) or not env_name.strip():
            raise YamlParseError(f"{source}: 环境名称必须是非空字符串")
        env_name = env_name.strip()

        if not isinstance(env_def, dict):
            raise YamlParseError(
                f"{source} env({env_name}): 环境配置必须是字典")

        inherit = env_def.get("inherit")
        if inherit is not None and not isinstance(inherit, str):
            raise YamlParseError(
                f"{source} env({env_name}): 'inherit' 必须是字符串")

        variables = env_def.get("variables") or {}
        if not isinstance(variables, dict):
            raise YamlParseError(
                f"{source} env({env_name}): 'variables' 必须是字典")
        variables = {str(k): str(v) for k, v in variables.items()}

        config = env_def.get("config") or {}
        if not isinstance(config, dict):
            raise YamlParseError(
                f"{source} env({env_name}): 'config' 必须是字典")

        cookies = _coerce_cookies(
            env_def.get("cookies"), f"{source} env({env_name})")

        envs[env_name] = EnvConfig(
            name=env_name,
            inherit=inherit.strip() if inherit else None,
            variables=variables,
            config=config,
            cookies=cookies,
        )

    return envs


def _resolve_env_inheritance(
    envs: dict[str, EnvConfig], source: Path,
) -> dict[str, EnvConfig]:
    """解析环境配置的继承关系，合并父环境的配置。"""
    resolved: dict[str, EnvConfig] = {}

    def _resolve_single(name: str, visited: set[str]) -> EnvConfig:
        if name in resolved:
            return resolved[name]
        if name not in envs:
            raise YamlParseError(
                f"{source}: 环境 '{name}' 未定义")
        if name in visited:
            raise YamlParseError(
                f"{source}: 环境继承存在循环引用: {' -> '.join(visited)} -> {name}")

        env = envs[name]
        if not env.inherit:
            resolved[name] = env
            return env

        visited.add(name)
        parent = _resolve_single(env.inherit, visited)

        # 合并：父环境被子环境覆盖
        merged_vars = {**parent.variables, **env.variables}
        merged_config = {**parent.config, **env.config}

        # cookies 合并：子环境同名 cookie 覆盖父环境
        seen_keys: set[tuple[str, str]] = set()
        merged_cookies: list[CookieItem] = []
        for cookie in env.cookies + parent.cookies:
            key = (cookie.name, cookie.domain)
            if key not in seen_keys:
                seen_keys.add(key)
                merged_cookies.append(cookie)

        resolved[name] = EnvConfig(
            name=name,
            inherit=env.inherit,
            variables=merged_vars,
            config=merged_config,
            cookies=merged_cookies,
        )
        return resolved[name]

    for env_name in envs:
        _resolve_single(env_name, set())

    return resolved


def _expand_data_driven_cases(cases: list[TestCase]) -> list[TestCase]:
    """展开数据驱动用例，为每行数据生成独立的 TestCase 实例。"""
    expanded: list[TestCase] = []

    for case in cases:
        if case.data_driven is None or case.data_driven.source is None:
            expanded.append(case)
            continue

        ctx = f"{case.source_file or '<unknown>'}({case.name})"
        base_dir = case.source_file.parent if case.source_file else None

        # 加载数据源
        try:
            rows = resolve_data_source(
                case.data_driven.source, base_dir=base_dir, ctx=ctx)
        except DataSourceError as e:
            raise YamlParseError(str(e)) from e

        # 过滤数据行
        try:
            rows = filter_data_rows(
                rows,
                filter_expr=case.data_driven.filter_expr,
                skip_if_expr=case.data_driven.skip_if_expr,
                ctx=ctx,
            )
        except DataSourceError as e:
            raise YamlParseError(str(e)) from e

        if not rows:
            # 过滤后无数据行，跳过该用例
            continue

        # 为每行数据生成用例实例
        name_field = case.data_driven.name_field
        for idx, row in enumerate(rows):
            # 确定用例名称后缀
            if name_field and name_field in row:
                suffix = str(row[name_field])
            else:
                suffix = str(idx)

            # 将数据行转为变量（data.xxx 前缀）
            data_vars = row_to_variables(row)

            # 合并变量：原用例变量 + 数据行变量（数据行优先级高于同名变量）
            merged_vars = {**case.variables, **data_vars}

            expanded.append(TestCase(
                name=f"{case.name} [{suffix}]",
                description=case.description,
                steps=list(case.steps),  # 步骤复制（变量替换在后续阶段）
                tags=list(case.tags),
                config=dict(case.config),
                cookies=list(case.cookies),
                source_file=case.source_file,
                extends=case.extends,
                variables=merged_vars,
                data_driven=case.data_driven,
                data_row=row,
                data_index=idx,
            ))

    return expanded


def _apply_variables(case: TestCase, global_variables: dict[str, str]) -> TestCase:
    """对用例中的步骤文本应用变量替换。

    变量优先级：用例级 > 模板继承级 > 全局级。
    """
    # 合并变量：全局 < 用例（用例级已包含模板继承合并后的 variables）
    merged_vars = {**global_variables, **case.variables}

    if not merged_vars and not any("${" in s.text for s in case.steps):
        return case

    try:
        resolved_steps = [
            TestStep(text=resolve_text(s.text, merged_vars))
            for s in case.steps
        ]
    except VariableError as e:
        source = case.source_file or Path("<unknown>")
        raise YamlParseError(
            f"{source}({case.name}): 变量替换失败 - {e}"
        ) from e

    return TestCase(
        name=case.name,
        description=case.description,
        steps=resolved_steps,
        tags=case.tags,
        config=case.config,
        cookies=case.cookies,
        source_file=case.source_file,
        extends=case.extends,
        variables=merged_vars,
        data_driven=case.data_driven,
        data_row=case.data_row,
        data_index=case.data_index,
    )


def load_files(paths: Iterable[str | Path], env_name: str | None = None) -> TestSuite:
    """加载多个 YAML 文件并合并成一个 Suite。

    Args:
        paths: YAML 文件路径列表。
        env_name: 激活的环境名称，None 时不启用环境配置。
    """
    suite = TestSuite()
    seen_names: set[str] = set()
    all_presets: dict[str, TestTemplate] = {}

    for path in paths:
        cases, cfg, presets = load_yaml(path)
        suite.source_files.append(Path(path))
        if cfg and not suite.yaml_config:
            suite.yaml_config = cfg

        # 合并预设（后文件的同名预设覆盖前面的）
        all_presets.update(presets)

        for c in cases:
            if c.name in seen_names:
                # 同名用例自动加上文件名后缀，避免 Allure 同 testCaseId 合并
                c.name = f"{c.name} [{Path(c.source_file).stem if c.source_file else 'dup'}]"
            seen_names.add(c.name)
            suite.cases.append(c)

    # 解析所有用例的预设继承
    suite.templates = all_presets
    suite.cases = [
        _resolve_extends(
            c, all_presets, c.source_file or Path("<unknown>"))
        for c in suite.cases
    ]

    # 展开数据驱动用例
    suite.cases = _expand_data_driven_cases(suite.cases)

    # 提取全局变量（从 yaml_config 中取出 _variables）
    global_variables: dict[str, str] = suite.yaml_config.pop("_variables", {})
    suite.variables = global_variables

    # 解析多环境配置
    raw_envs = suite.yaml_config.pop("_environments", None)
    if raw_envs:
        source = suite.source_files[0] if suite.source_files else Path(
            "<unknown>")
        parsed_envs = _parse_environments(raw_envs, source)
        suite.environments = _resolve_env_inheritance(parsed_envs, source)

    # 应用环境配置到全局变量
    if env_name and suite.environments:
        if env_name not in suite.environments:
            available = ", ".join(sorted(suite.environments.keys()))
            raise YamlParseError(
                f"环境 '{env_name}' 未定义。可用环境: {available}")
        active_env = suite.environments[env_name]
        suite.active_env = env_name

        # 环境变量注入到全局变量中（优先级高于顶层 variables）
        # 同时注入 env.current.xxx 前缀形式
        env_vars: dict[str, str] = {}
        for k, v in active_env.variables.items():
            env_vars[k] = v
            env_vars[f"env.{k}"] = v
            env_vars[f"env.current.{k}"] = v
        global_variables = {**global_variables, **env_vars}
        suite.variables = global_variables

    # 应用变量替换到所有用例步骤
    suite.cases = [
        _apply_variables(c, global_variables)
        for c in suite.cases
    ]

    return suite
