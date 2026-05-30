# 扩展开发指南

本文档介绍如何扩展 burunner 框架，包括新增 LLM Provider、通知渠道、数据源类型和自定义浏览器驱动。

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

burunner 的通知系统采用 **工厂模式 + 注册表**（`src/burunner/notifier/`），新增渠道需实现通知器并注册。

### 步骤

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

编辑 `src/burunner/notifier/factory.py`：

```python
from burunner.notifier.slack import SlackNotifier

NOTIFIER_REGISTRY: dict[str, type[BaseNotifier]] = {
    "wecom": WecomNotifier,
    "feishu": FeishuNotifier,
    "dingtalk": DingtalkNotifier,
    "slack": SlackNotifier,  # 新增
}
```

#### 3. 使用

```bash
# .env
BURUNNER_NOTIFY_CHANNEL=slack
BURUNNER_NOTIFY_WEBHOOK=https://hooks.slack.com/services/xxx
```

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
| 通知渠道 | 工厂 + 继承 | `BaseNotifier.send()` + `NOTIFIER_REGISTRY` |
| 数据源 | 后缀匹配 + 加载函数 | `resolve_data_source()` |
| 浏览器驱动 | 参数扩展 | `create_session()` |
| 报告器 | 注册表 + 继承 | `BaseReporter` + `REPORTER_REGISTRY` |
