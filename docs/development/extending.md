# Extending Guide

This document explains how to extend the burunner framework, including adding new LLM Providers, notification channels, data source types, and custom browser drivers.

---

## Adding a New LLM Provider

burunner's LLM layer uses a **Registry + Strategy pattern** (`src/burunner/llm/provider.py`). Adding a new Provider only requires adding a `ProviderSpec` entry to the registry.

### Steps

#### 1. Define a ProviderSpec

Add an entry to the `PROVIDER_REGISTRY` dict in `src/burunner/llm/provider.py`:

```python
# src/burunner/llm/provider.py

PROVIDER_REGISTRY: dict[str, ProviderSpec] = {
    # ... existing providers ...

    "my_provider": ProviderSpec(
        # Class name candidates in browser_use.llm (by priority)
        class_candidates=("ChatMyProvider",),
        # Optional: fallback candidates if primary class not found
        fallback_candidates=("ChatOpenAI",),
        # Optional: default API endpoint
        default_endpoint="https://api.myprovider.com/v1",
        # Endpoint parameter name (default "base_url", Azure uses "azure_endpoint")
        endpoint_param="base_url",
        # Whether API key is required (set False for local models like Ollama)
        requires_api_key=True,
        # Optional: custom logic hook
        customizer=None,
    ),
}
```

#### 2. Implement a Customizer (Optional)

If the Provider needs extra parameter handling (e.g., custom headers, version numbers), write a customizer function:

```python
def _my_provider_customizer(
    kwargs: dict[str, Any],
    base_url: str | None,
    api_key: str | None,
    extra: dict[str, Any],
) -> None:
    """Custom logic for MyProvider."""
    # Example: inject custom header
    project_id = os.getenv("BURUNNER_MY_PROJECT_ID")
    if project_id:
        kwargs["extra_headers"] = {"X-Project-Id": project_id}
```

Then reference it in the `ProviderSpec`:

```python
"my_provider": ProviderSpec(
    class_candidates=("ChatOpenAI",),
    default_endpoint="https://api.myprovider.com/v1",
    customizer=_my_provider_customizer,
),
```

#### 3. Ensure the Class is Importable

burunner uses `_resolve()` to dynamically look up classes from the `browser_use.llm` module. If your Provider is OpenAI-compatible, simply use `ChatOpenAI` as `class_candidates`; otherwise, ensure `browser-use` exports the corresponding Chat class.

#### 4. Verify

```bash
# Verify Provider is registered
python -c "from burunner.llm.provider import SUPPORTED_PROVIDERS; print(SUPPORTED_PROVIDERS)"

# Actual invocation
burunner run examples/example.yaml --llm my_provider --model my-model --api-key sk-xxx
```

### ProviderSpec Field Reference

| Field | Type | Description |
| --- | --- | --- |
| `class_candidates` | `tuple[str, ...]` | Class names in `browser_use.llm`, in priority order |
| `fallback_candidates` | `tuple[str, ...]` | Fallback candidates when primary class resolution fails |
| `default_endpoint` | `str \| None` | Default API endpoint URL |
| `endpoint_param` | `str` | Parameter name passed to the Chat class for endpoint |
| `requires_api_key` | `bool` | Whether an API key is required |
| `customizer` | `Callable \| None` | Custom logic hook function |

---

## Adding a New Notification Channel

burunner's notification system uses a **Factory + Registry pattern** (`src/burunner/notifier/`). Adding a new channel requires implementing a notifier and registering it.

### Steps

#### 1. Create a Notifier Class

Create a new file under `src/burunner/notifier/`, inheriting from `BaseNotifier`:

```python
# src/burunner/notifier/slack.py

"""Slack notifier."""

from __future__ import annotations

import json
import logging
import urllib.request

from burunner.notifier.base import BaseNotifier, NotifyPayload

logger = logging.getLogger("burunner.notifier.slack")


class SlackNotifier(BaseNotifier):
    """Slack Webhook notifier."""

    def send(self, payload: NotifyPayload) -> bool:
        """Send Slack notification. Returns True on success."""
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
            logger.error("Slack notification failed: %s", e)
            return False
```

**Core Requirements**:
- Inherit from `BaseNotifier`
- Implement `send(payload: NotifyPayload) -> bool`
- Return `True` on success, `False` on failure (never raise exceptions)
- Reuse `self._build_summary_lines(payload)` to build notification body

#### 2. Register in the Factory

Edit `src/burunner/notifier/factory.py`:

```python
from burunner.notifier.slack import SlackNotifier

NOTIFIER_REGISTRY: dict[str, type[BaseNotifier]] = {
    "wecom": WecomNotifier,
    "feishu": FeishuNotifier,
    "dingtalk": DingtalkNotifier,
    "slack": SlackNotifier,  # new
}
```

#### 3. Usage

```bash
# .env
BURUNNER_NOTIFY_CHANNEL=slack
BURUNNER_NOTIFY_WEBHOOK=https://hooks.slack.com/services/xxx
```

### NotifyPayload Fields

| Field | Type | Description |
| --- | --- | --- |
| `suite_name` | `str` | Test suite name |
| `is_success` | `bool` | Whether all cases passed |
| `total` | `int` | Total case count |
| `passed` | `int` | Passed count |
| `failed` | `int` | Failed count |
| `error` | `int` | Error count |
| `total_elapsed` | `float` | Total elapsed time (seconds) |
| `env_name` | `str \| None` | Runtime environment name |
| `failed_cases` | `list[str]` | List of failed case names |
| `pass_rate` | `str` (property) | Pass rate text |
| `status_text` | `str` (property) | Status text (✅/❌) |
| `elapsed_text` | `str` (property) | Formatted elapsed time |

---

## Adding a New Data Source Type

burunner supports CSV / JSON / YAML / inline data-driven testing. To extend with a new data source format, modify `src/burunner/parser/datasource.py`.

### Steps

#### 1. Extend the `resolve_data_source` Function

```python
# src/burunner/parser/datasource.py

def resolve_data_source(
    source: Any,
    base_dir: Path | None = None,
    ctx: str = "",
) -> list[dict[str, str]]:
    """Load data source, return list of dicts."""
    # ... existing logic ...

    # Add new format detection
    if suffix == ".xlsx":
        return _load_excel(file_path, ctx)

    raise DataSourceError(f"{ctx}: unsupported data source format '{suffix}'")
```

#### 2. Implement the Loader Function

```python
def _load_excel(path: Path, ctx: str) -> list[dict[str, str]]:
    """Load Excel file as list of dicts."""
    try:
        import openpyxl
    except ImportError:
        raise DataSourceError(
            f"{ctx}: loading Excel requires openpyxl: pip install openpyxl"
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

#### 3. Usage

```yaml
cases:
  - name: Excel data-driven
    data_driven:
      source: data/users.xlsx
    steps:
      - Enter username ${username}
```

---

## Custom Browser Driver

burunner manages Playwright browser sessions through `src/burunner/browser/session.py`.

### Extension Points

#### Custom Browser Launch Parameters

`create_session()` accepts the following parameters:

```python
async def create_session(
    headless: bool = True,
    user_data_dir: str | None = None,
    keep_alive: bool = False,
    channel: str | None = None,
) -> BrowserSession:
    ...
```

For more complex browser configurations (e.g., proxy, extensions), extend the launch parameters in `session.py`:

```python
# Example: add proxy support
async def create_session(
    headless: bool = True,
    channel: str | None = None,
    proxy: dict | None = None,  # new
) -> BrowserSession:
    launch_kwargs = {}
    if proxy:
        launch_kwargs["proxy"] = proxy
    # ...
```

#### Supported Browser Channels

`SUPPORTED_BROWSER_CHANNELS` defines all supported browser types. To add a new channel:

```python
SUPPORTED_BROWSER_CHANNELS = (
    "chromium", "chrome", "chrome-beta", "chrome-dev", "chrome-canary",
    "msedge", "msedge-beta", "msedge-dev", "msedge-canary",
    "my-custom-browser",  # new
)
```

> **Note**: browser-use only supports Chromium-based browsers. Firefox / Safari are not supported.

---

## Custom Reporter

burunner's reporting layer (`src/burunner/reporter/`) supports extension via registry.

### Steps

#### 1. Implement a Reporter

```python
# src/burunner/reporter/json_reporter.py

from burunner.reporter.base import BaseReporter
from burunner.runner.result import CaseResult


class JsonReporter(BaseReporter):
    """Custom JSON report output."""

    def write_case(self, result: CaseResult, **kwargs) -> None:
        # Implement custom reporting logic
        ...
```

#### 2. Register in registry.py

```python
from burunner.reporter.json_reporter import JsonReporter

REPORTER_REGISTRY["json"] = JsonReporter
```

---

## Summary

Design principles for burunner extension points:

| Extension Point | Pattern | Core Interface |
| --- | --- | --- |
| LLM Provider | Registry + Strategy | `ProviderSpec` + `PROVIDER_REGISTRY` |
| Notification Channel | Factory + Inheritance | `BaseNotifier.send()` + `NOTIFIER_REGISTRY` |
| Data Source | Suffix matching + loader function | `resolve_data_source()` |
| Browser Driver | Parameter extension | `create_session()` |
| Reporter | Registry + Inheritance | `BaseReporter` + `REPORTER_REGISTRY` |
