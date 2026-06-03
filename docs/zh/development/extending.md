# 扩展开发指南

本文档介绍如何扩展 burunner 框架，包括新增 LLM Provider、通知渠道、变量函数、数据源类型和自定义浏览器驱动。

---

## 新增 LLM Provider

burunner 的 LLM 层采用 **注册表 + 策略模式**（`src/burunner/llm/provider.py`），新增 Provider 只需在注册表中添加一条 `ProviderSpec` 记录。

### 步骤

#### 1. 定义 ProviderSpec

在 `src/burunner/llm/provider.py` 的 `PROVIDER_REGISTRY` 字典中添加条目：

```python
# src/burunner/llm/provider.py

PROVIDER_REGISTRY: dict[str, ProviderSpec] = {
    # ... 现有 providers ...

    "my_provider": ProviderSpec(
        # browser_use.llm 模块中的类名候选（按优先级）
        class_candidates=("ChatMyProvider",),
        # 可选：主类不存在时的回退类（如兼容 OpenAI 协议）
        fallback_candidates=("ChatOpenAI",),
        # 可选：默认 API 端点
        default_endpoint="https://api.myprovider.com/v1",
        # endpoint 参数名（默认 "base_url"，Azure 用 "azure_endpoint"）
        endpoint_param="base_url",
        # 是否需要 API key（Ollama 等本地模型设为 False）
        requires_api_key=True,
        # 可选：特殊逻辑钩子
        customizer=None,
    ),
}
```

#### 2. 实现 Customizer（可选）

如果 Provider 需要额外参数处理（如特殊 header、版本号），编写 customizer 函数：

```python
def _my_provider_customizer(
    kwargs: dict[str, Any],
    base_url: str | None,
    api_key: str | None,
    extra: dict[str, Any],
) -> None:
    """MyProvider 额外处理逻辑。"""
    # 例如注入自定义 header
    project_id = os.getenv("BURUNNER_MY_PROJECT_ID")
    if project_id:
        kwargs["extra_headers"] = {"X-Project-Id": project_id}
```

然后在 `ProviderSpec` 中引用：

```python
"my_provider": ProviderSpec(
    class_candidates=("ChatOpenAI",),
    default_endpoint="https://api.myprovider.com/v1",
    customizer=_my_provider_customizer,
),
```

#### 3. 确保类可导入

burunner 通过 `_resolve()` 函数从 `browser_use.llm` 模块中动态查找类。如果你的 Provider 兼容 OpenAI 协议，直接使用 `ChatOpenAI` 作为 `class_candidates`；否则需确保 `browser-use` 已导出对应的 Chat 类。

#### 4. 验证

```bash
# 验证 Provider 已注册
python -c "from burunner.llm.provider import SUPPORTED_PROVIDERS; print(SUPPORTED_PROVIDERS)"

# 实际调用
burunner run examples/example.yaml --llm my_provider --model my-model --api-key sk-xxx
```

### ProviderSpec 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `class_candidates` | `tuple[str, ...]` | `browser_use.llm` 中的类名，按优先级顺序 |
| `fallback_candidates` | `tuple[str, ...]` | 主类解析失败时的回退候选 |
| `default_endpoint` | `str \| None` | 默认 API 端点 URL |
| `endpoint_param` | `str` | 传递给 Chat 类的端点参数名 |
| `requires_api_key` | `bool` | 是否需要 API key |
| `customizer` | `Callable \| None` | 特殊逻辑钩子函数 |

---

## 新增通知渠道

burunner 的通知系统采用 **插件化发现机制**（`src/burunner/notifier/`），支持两种扩展方式：

1. **内部扩展**：直接在 burunner 源代码中添加通知器
2. **外部插件**：通过 `entry_points` 机制注册独立包（推荐）

### 方式一：内部扩展（在源代码中添加）

#### 1. 创建通知器类

在 `src/burunner/notifier/` 下新建文件，继承 `BaseNotifier`：

```python
# src/burunner/notifier/slack.py

"""Slack 通知器。"""

from __future__ import annotations

import json
import logging
import urllib.request

from burunner.notifier.base import BaseNotifier, NotifyPayload

logger = logging.getLogger("burunner.notifier.slack")


class SlackNotifier(BaseNotifier):
    """Slack Webhook 通知器。"""

    def send(self, payload: NotifyPayload) -> bool:
        """发送 Slack 通知。成功返回 True。"""
        lines = self._build_summary_lines(payload)
        body = {
            "text": "\n".join(lines),
        }

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error("Slack 通知发送失败: %s", e)
            return False
```

**核心要求**：
- 继承 `BaseNotifier`
- 实现 `send(payload: NotifyPayload) -> bool`
- 成功返回 `True`，失败返回 `False`（不抛异常）
- 可复用 `self._build_summary_lines(payload)` 构建通知正文

#### 2. 在工厂中注册

编辑 `src/burunner/notifier/factory.py`，在 `_discover_notifiers()` 的内置通知器部分添加：

```python
from burunner.notifier.slack import SlackNotifier

# 在 _discover_notifiers() 函数中添加
registry["slack"] = SlackNotifier
```

#### 3. 使用

```bash
# .env
BURUNNER_NOTIFY_CHANNEL=slack
BURUNNER_NOTIFY_WEBHOOK=https://hooks.slack.com/services/xxx
```

### 方式二：外部插件（通过 entry_points 注册）

这是推荐的扩展方式，无需修改 burunner 源代码，只需发布独立的 Python 包。

#### 1. 创建插件项目结构

```
burunner-notify-slack/
├── pyproject.toml
└── src/
    └── burunner_notify_slack/
        ├── __init__.py
        └── notifier.py
```

#### 2. 实现通知器类

```python
# src/burunner_notify_slack/notifier.py

from __future__ import annotations

import json
import logging
import urllib.request

from burunner.notifier.base import BaseNotifier, NotifyPayload

logger = logging.getLogger("burunner.notifier.slack")


class SlackNotifier(BaseNotifier):
    """通过 Webhook 发送 Slack 通知。"""

    def send(self, payload: NotifyPayload) -> bool:
        """发送 Slack 通知。成功返回 True。"""
        lines = self._build_summary_lines(payload)
        body = {"text": "\n".join(lines)}

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error("Slack 通知发送失败: %s", e)
            return False
```

**核心要求**：
- 继承 `BaseNotifier`
- 实现 `send(payload: NotifyPayload) -> bool`
- 成功返回 `True`，失败返回 `False`（不抛异常）
- 可复用 `self._build_summary_lines(payload)` 构建通知正文

#### 3. 配置 pyproject.toml

```toml
[project]
name = "burunner-notify-slack"
version = "0.1.0"
description = "Slack notifier plugin for burunner"
dependencies = ["burunner"]

[project.entry-points."burunner.notifiers"]
slack = "burunner_notify_slack.notifier:SlackNotifier"
```

关键配置说明：
- `[project.entry-points."burunner.notifiers"]` — 组名必须为 `burunner.notifiers`
- `slack` — 插件名称，即 `BURUNNER_NOTIFY_CHANNEL` 的值
- `"burunner_notify_slack.notifier:SlackNotifier"` — 指向通知器类的完整路径

#### 4. 发布与使用

```bash
# 开发时本地安装
pip install -e ./burunner-notify-slack

# 或发布到 PyPI 后安装
pip install burunner-notify-slack

# 配置使用
# .env
BURUNNER_NOTIFY_CHANNEL=slack
BURUNNER_NOTIFY_WEBHOOK=https://hooks.slack.com/services/xxx
```

安装后 burunner 会在启动时自动发现并加载该插件，无需修改任何配置文件。

### 插件发现机制说明

burunner 启动时，`factory.py` 中的 `_discover_notifiers()` 会：

1. 注册内置通知器（wecom/feishu/dingtalk）
2. 通过 `importlib.metadata.entry_points(group="burunner.notifiers")` 扫描外部插件
3. 验证插件类是否为 `BaseNotifier` 的子类
4. 注册到可用通知器字典中

插件加载失败只会记录警告日志，不会影响 burunner 正常运行。

### NotifyPayload 可用字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `suite_name` | `str` | 测试套件名称 |
| `is_success` | `bool` | 是否全部通过 |
| `total` | `int` | 用例总数 |
| `passed` | `int` | 通过数 |
| `failed` | `int` | 失败数 |
| `error` | `int` | 错误数 |
| `total_elapsed` | `float` | 总耗时（秒） |
| `env_name` | `str \| None` | 运行环境名 |
| `failed_cases` | `list[str]` | 失败用例名称列表 |
| `pass_rate` | `str`（property） | 通过率文本 |
| `status_text` | `str`（property） | 状态文本（✅/❌） |
| `elapsed_text` | `str`（property） | 格式化耗时 |

### 开发注意事项

- **命名规范**：通知器类名使用 PascalCase（如 `SlackNotifier`、`TelegramNotifier`）
- **webhook_url**：由 `BaseNotifier.__init__()` 自动从框架配置中获取，无需手动解析
- **异常处理**：`send()` 必须返回 `True`（成功）或 `False`（失败），不可抛出异常——框架不会因通知发送失败而中断测试执行
- **日志输出**：使用 `logging.getLogger("burunner.notifier.<channel>")` 保持日志格式一致
- **超时设置**：HTTP 请求应设置合理超时（建议 10 秒），避免阻塞主流程
- **内容构建**：复用 `self._build_summary_lines(payload)` 生成标准 Markdown 格式内容；仅在目标平台有特殊要求时自定义格式

---

## 变量函数扩展

burunner 的变量系统基于 [Mako 模板引擎](https://www.makotemplates.org/)，通过 `VariableRegistry` 注册自定义函数。YAML 测试步骤中所有 `${...}` 表达式均通过此系统解析。

### 内置函数列表

| 函数 | 签名 | 说明 | 示例 |
| --- | --- | --- | --- |
| `timestamp` | `timestamp()` | 当前 Unix 时间戳（秒） | `${timestamp()}` → `1717401600` |
| `date` | `date()` | 当前日期 YYYY-MM-DD | `${date()}` → `2026-06-03` |
| `datetime` | `datetime()` | 当前日期时间 YYYY-MM-DD HH:MM:SS | `${datetime()}` → `2026-06-03 14:30:00` |
| `utc_datetime` | `utc_datetime()` | 当前 UTC 日期时间 | `${utc_datetime()}` → `2026-06-03 06:30:00` |
| `random_int` | `random_int([min], [max])` | 随机整数（默认 0–9999） | `${random_int(100, 999)}` → `427` |
| `random_string` | `random_string([length])` | 随机字母数字字符串（默认长度 8） | `${random_string(12)}` → `aB3kQ9xMp2Yz` |
| `uuid` | `uuid()` | UUID4 字符串 | `${uuid()}` → `a1b2c3d4-...` |
| `env` | `env(NAME[, default])` | 读取环境变量 | `${env('HOME')}` → `/Users/me` |
| `calc` | `calc(expression)` | 安全数学表达式计算（+, -, *, /, %, **） | `${calc('2 ** 10')}` → `1024` |

### 扩展方式 A：全局注册

在全局 `_default_registry` 实例上注册函数，使其在所有测试用例中可用：

```python
# my_burunner_extensions/functions.py

from burunner.parser.variables import _default_registry


@_default_registry.register("phone")
def _fn_phone(prefix="138"):
    """生成随机中国手机号。"""
    import random
    suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{prefix}{suffix}"


@_default_registry.register("test_email")
def _fn_test_email(name=None):
    """生成测试邮箱地址。"""
    import random, string
    if name is None:
        name = "".join(random.choices(string.ascii_lowercase, k=6))
    return f"{name}@test.example.com"
```

在 YAML 中使用：

```yaml
steps:
  - 输入手机号 ${phone()}
  - 输入手机号 ${phone('159')}
  - 输入邮箱 ${test_email()}
  - 输入邮箱 ${test_email('alice')}
```

> **注意**：扩展模块必须在测试运行前被导入。可在 `conftest.py` 或启动钩子中添加 `import` 语句。

### 扩展方式 B：通过 `resolve_text` 传入自定义函数

对于隔离的或特定测试场景的函数，直接传递给 `resolve_text()`：

```python
from burunner.parser.variables import resolve_text

custom_functions = {
    "order_id": lambda: f"ORD-{__import__('time').strftime('%Y%m%d%H%M%S')}",
    "greet": lambda name: f"Hello, {name}!",
}

result = resolve_text("${greet('World')} Order: ${order_id()}", custom_functions=custom_functions)
# => "Hello, World! Order: ORD-20260603143000"
```

> **注意**：通过 `custom_functions` 传入的函数可以覆盖同名的内置函数。

### 扩展方式 C：独立 VariableRegistry 实例

适合库或插件开发者使用独立的注册表实例：

```python
from burunner.parser.variables import VariableRegistry

my_registry = VariableRegistry()


@my_registry.register("my_func")
def _fn_my_func(arg1, arg2="default"):
    return f"{arg1}_{arg2}"


# 通过 custom_functions 参数传入 resolve_text
from burunner.parser.variables import resolve_text

result = resolve_text(
    "${my_func('hello', 'world')}",
    custom_functions=my_registry._functions,
)
# => "hello_world"
```

### 安全约束说明

变量系统实施严格的沙箱机制：

| 约束 | 详细说明 |
| --- | --- |
| `__builtins__` 被清空 | 所有 Python 内置函数在模板上下文中被移除 |
| 危险名称被阻止 | `__import__`、`eval`、`exec`、`compile`、`open`、`getattr`、`setattr`、`globals`、`locals`、`breakpoint` 等 |
| 预渲染校验 | `${...}` 表达式在渲染前会扫描危险模式 |
| 仅注册函数可用 | 只有显式注入上下文的函数才能被调用 |
| 建议使用简单类型 | 函数参数和返回值应为简单类型（`str`、`int`、`float`） |

> **警告**：虽然 `<%...%>` 控制块已被转义，但如果注入了危险函数，`${...}` 表达式仍可执行任意 Python 代码。请始终将注册表限制在安全、无副作用的函数范围内。

### 完整示例：测试数据生成器插件

以下是一个完整的自定义函数包开发示例，用于生成测试数据：

```python
# my_burunner_testdata/__init__.py

"""burunner 测试数据生成函数扩展包。"""

import random
import string

from burunner.parser.variables import _default_registry


@_default_registry.register("phone")
def _fn_phone(prefix="138"):
    """生成随机手机号。"""
    suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{prefix}{suffix}"


@_default_registry.register("test_email")
def _fn_test_email(name=None):
    """生成测试邮箱地址。"""
    if name is None:
        name = "".join(random.choices(string.ascii_lowercase, k=6))
    return f"{name}@test.example.com"


@_default_registry.register("id_card")
def _fn_id_card():
    """生成随机 18 位身份证号（仅用于测试）。"""
    area = str(random.randint(110000, 659999))
    year = str(random.randint(1970, 2005))
    month = f"{random.randint(1, 12):02d}"
    day = f"{random.randint(1, 28):02d}"
    seq = f"{random.randint(1, 999):03d}"
    base = f"{area}{year}{month}{day}{seq}"
    # 简化校验位
    check = str(random.randint(0, 9))
    return f"{base}{check}"


@_default_registry.register("company_name")
def _fn_company_name():
    """生成随机公司名（用于测试）。"""
    prefixes = ["华创", "全球", "智联", "云端", "星辰"]
    suffixes = ["科技", "信息", "网络", "数据", "系统"]
    return f"{random.choice(prefixes)}{random.choice(suffixes)}有限公司"
```

在测试 YAML 中使用：

```yaml
cases:
  - name: 用户注册测试
    steps:
      - 打开注册页面
      - 输入手机号 ${phone()}
      - 输入邮箱 ${test_email()}
      - 输入身份证号 ${id_card()}
      - 输入公司名称 ${company_name()}
      - 点击提交
```

确保该扩展包在启动时被导入：

```python
# conftest.py 或启动脚本
import my_burunner_testdata  # noqa: F401 — 触发注册
```

---

## 新增数据源类型

burunner 支持 CSV / JSON / YAML / 内联数据驱动。扩展新数据源格式需修改 `src/burunner/parser/datasource.py`。

### 步骤

#### 1. 扩展 `resolve_data_source` 函数

```python
# src/burunner/parser/datasource.py

def resolve_data_source(
    source: Any,
    base_dir: Path | None = None,
    ctx: str = "",
) -> list[dict[str, str]]:
    """加载数据源，返回字典列表。"""
    # ... 现有逻辑 ...

    # 新增格式判断
    if suffix == ".xlsx":
        return _load_excel(file_path, ctx)

    raise DataSourceError(f"{ctx}: 不支持的数据源格式 '{suffix}'")
```

#### 2. 实现加载函数

```python
def _load_excel(path: Path, ctx: str) -> list[dict[str, str]]:
    """加载 Excel 文件为字典列表。"""
    try:
        import openpyxl
    except ImportError:
        raise DataSourceError(
            f"{ctx}: 加载 Excel 需要安装 openpyxl：pip install openpyxl"
        )

    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return []

    headers = [str(h).strip() for h in rows[0]]
    return [
        {headers[i]: str(cell or "") for i, cell in enumerate(row)}
        for row in rows[1:]
    ]
```

#### 3. 使用

```yaml
cases:
  - name: Excel 数据驱动
    data_driven:
      source: data/users.xlsx
    steps:
      - 输入用户名 ${username}
```

---

## 自定义浏览器驱动

burunner 通过 `src/burunner/browser/session.py` 管理 Playwright 浏览器会话。

### 扩展点

#### 自定义浏览器启动参数

`create_session()` 函数接受以下参数：

```python
async def create_session(
    headless: bool = True,
    user_data_dir: str | None = None,
    keep_alive: bool = False,
    channel: str | None = None,
) -> BrowserSession:
    ...
```

如需更复杂的浏览器配置（如代理、扩展），可在 `session.py` 中扩展启动参数：

```python
# 示例：添加代理支持
async def create_session(
    headless: bool = True,
    channel: str | None = None,
    proxy: dict | None = None,  # 新增
) -> BrowserSession:
    launch_kwargs = {}
    if proxy:
        launch_kwargs["proxy"] = proxy
    # ...
```

#### 支持的浏览器 Channel

`SUPPORTED_BROWSER_CHANNELS` 定义了所有支持的浏览器类型。如需添加新 channel：

```python
SUPPORTED_BROWSER_CHANNELS = (
    "chromium", "chrome", "chrome-beta", "chrome-dev", "chrome-canary",
    "msedge", "msedge-beta", "msedge-dev", "msedge-canary",
    "my-custom-browser",  # 新增
)
```

> **注意**：browser-use 仅支持 Chromium 内核浏览器，Firefox / Safari 不受支持。

---

## 自定义报告器

burunner 的报告层（`src/burunner/reporter/`）支持通过注册表扩展。

### 步骤

#### 1. 实现报告器

```python
# src/burunner/reporter/json_reporter.py

from burunner.reporter.base import BaseReporter
from burunner.runner.result import CaseResult


class JsonReporter(BaseReporter):
    """自定义 JSON 报告输出。"""

    def write_case(self, result: CaseResult, **kwargs) -> None:
        # 实现自定义报告逻辑
        ...
```

#### 2. 在 registry.py 中注册

```python
from burunner.reporter.json_reporter import JsonReporter

REPORTER_REGISTRY["json"] = JsonReporter
```

---

## 总结

burunner 各扩展点的设计原则：

| 扩展点 | 模式 | 核心接口 |
| --- | --- | --- |
| LLM Provider | 注册表 + 策略 | `ProviderSpec` + `PROVIDER_REGISTRY` |
| 通知渠道 | 插件化发现 | `BaseNotifier.send()` + `entry_points` |
| 变量函数 | 注册表 + Mako 沙箱 | `VariableRegistry` + `_default_registry` |
| 数据源 | 后缀匹配 + 加载函数 | `resolve_data_source()` |
| 浏览器驱动 | 参数扩展 | `create_session()` |
| 报告器 | 注册表 + 继承 | `BaseReporter` + `REPORTER_REGISTRY` |
