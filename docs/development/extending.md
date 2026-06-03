# Extending Guide

This document explains how to extend the burunner framework, including adding new LLM Providers, notification channels, variable functions, data source types, and custom browser drivers.

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

There are two approaches:
1. **Internal**: Add directly to the burunner source code (modify factory.py)
2. **Plugin**: Create an external package with `entry_points` (no source changes needed)

### Approach 1: Internal Registration

#### Steps

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

### Approach 2: External Plugin (entry_points)

For distributing a notifier as a standalone package without modifying burunner source code:

#### 1. Create a Python Package

```
burunner-slack-notifier/
├── pyproject.toml
└── src/
    └── burunner_slack/
        ├── __init__.py
        └── notifier.py
```

#### 2. Implement the Notifier

```python
# src/burunner_slack/notifier.py

from __future__ import annotations

import json
import logging
import urllib.request

from burunner.notifier.base import BaseNotifier, NotifyPayload

logger = logging.getLogger("burunner_slack")


class SlackNotifier(BaseNotifier):
    """Slack Webhook notifier plugin for burunner."""

    def send(self, payload: NotifyPayload) -> bool:
        """Send Slack notification. Returns True on success."""
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
            logger.error("Slack notification failed: %s", e)
            return False
```

#### 3. Configure entry_points in pyproject.toml

```toml
[project]
name = "burunner-slack-notifier"
version = "0.1.0"
dependencies = ["burunner"]

[project.entry-points."burunner.notifiers"]
slack = "burunner_slack.notifier:SlackNotifier"
```

The entry point **name** (`slack`) becomes the value for `BURUNNER_NOTIFY_CHANNEL`. The entry point **value** is the dotted path to the notifier class.

#### 4. Install and Use

```bash
# Install the plugin
pip install burunner-slack-notifier

# Configure
BURUNNER_NOTIFY_CHANNEL=slack
BURUNNER_NOTIFY_WEBHOOK=https://hooks.slack.com/services/T.../B.../xxx

# Run tests — notifications will use the plugin automatically
burunner run tests/*.yaml
```

#### How Discovery Works

burunner's factory loads notifiers in this order:
1. Check the built-in `NOTIFIER_REGISTRY` for a matching channel name
2. Scan `entry_points(group="burunner.notifiers")` for external plugins
3. If found, instantiate the class with the configured webhook URL

This means external plugins can also **override** built-in notifiers by using the same channel name.

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

### Best Practices

- **Naming**: Notifier class names should use PascalCase (e.g., `SlackNotifier`, `TelegramNotifier`)
- **webhook_url**: Obtained automatically by `BaseNotifier.__init__()` from the framework configuration — no manual parsing needed
- **Error Handling**: `send()` must return `True` on success and `False` on failure. Never raise exceptions — the framework will not abort test execution due to notification failures
- **Logging**: Use `logging.getLogger("burunner.notifier.<channel>")` for consistent log output
- **Timeout**: Set appropriate timeouts for HTTP requests (recommended: 10 seconds) to avoid blocking the main process
- **Content Building**: Reuse `self._build_summary_lines(payload)` to produce standardized Markdown content; customize formatting only when the target platform requires it

---

## Extending Variable Functions

burunner's variable system is powered by the [Mako template engine](https://www.makotemplates.org/) and exposes a `VariableRegistry` for registering custom functions. All `${...}` expressions in YAML test steps are resolved through this system.

### Built-in Functions

| Function | Signature | Description | Example |
| --- | --- | --- | --- |
| `timestamp` | `timestamp()` | Current Unix timestamp (seconds) | `${timestamp()}` → `1717401600` |
| `date` | `date()` | Current date in YYYY-MM-DD | `${date()}` → `2026-06-03` |
| `datetime` | `datetime()` | Current datetime YYYY-MM-DD HH:MM:SS | `${datetime()}` → `2026-06-03 14:30:00` |
| `utc_datetime` | `utc_datetime()` | Current UTC datetime | `${utc_datetime()}` → `2026-06-03 06:30:00` |
| `random_int` | `random_int([min], [max])` | Random integer (default 0–9999) | `${random_int(100, 999)}` → `427` |
| `random_string` | `random_string([length])` | Random alphanumeric string (default length 8) | `${random_string(12)}` → `aB3kQ9xMp2Yz` |
| `uuid` | `uuid()` | UUID4 string | `${uuid()}` → `a1b2c3d4-...` |
| `env` | `env(NAME[, default])` | Read environment variable | `${env('HOME')}` → `/Users/me` |
| `calc` | `calc(expression)` | Safe math evaluation (+, -, *, /, %, **) | `${calc('2 ** 10')}` → `1024` |

### Extension Approach A: Global Registration

Register functions on the global `_default_registry` instance so they are available in all test cases:

```python
# my_burunner_extensions/functions.py

from burunner.parser.variables import _default_registry


@_default_registry.register("phone")
def _fn_phone(prefix="138"):
    """Generate a random Chinese mobile number."""
    import random
    suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{prefix}{suffix}"


@_default_registry.register("test_email")
def _fn_test_email(name=None):
    """Generate a test email address."""
    import random, string
    if name is None:
        name = "".join(random.choices(string.ascii_lowercase, k=6))
    return f"{name}@test.example.com"
```

Usage in YAML:

```yaml
steps:
  - Enter phone number ${phone()}
  - Enter phone number ${phone('159')}
  - Enter email ${test_email()}
  - Enter email ${test_email('alice')}
```

> **Note**: The extension module must be imported before tests run. You can add an `import` in a `conftest.py` or a startup hook.

### Extension Approach B: Passing Custom Functions via `resolve_text`

For isolated or test-specific functions, pass them directly to `resolve_text()`:

```python
from burunner.parser.variables import resolve_text

custom_functions = {
    "order_id": lambda: f"ORD-{__import__('time').strftime('%Y%m%d%H%M%S')}",
    "greet": lambda name: f"Hello, {name}!",
}

result = resolve_text("${greet('World')} Order: ${order_id()}", custom_functions=custom_functions)
# => "Hello, World! Order: ORD-20260603143000"
```

> **Note**: Functions passed via `custom_functions` can override built-in functions of the same name.

### Extension Approach C: Standalone VariableRegistry Instance

For library or plugin authors who want isolated registries:

```python
from burunner.parser.variables import VariableRegistry

my_registry = VariableRegistry()


@my_registry.register("my_func")
def _fn_my_func(arg1, arg2="default"):
    return f"{arg1}_{arg2}"


# Use with resolve_text via custom_functions
from burunner.parser.variables import resolve_text

result = resolve_text(
    "${my_func('hello', 'world')}",
    custom_functions=my_registry._functions,
)
# => "hello_world"
```

### Security Constraints

The variable system enforces a strict sandbox:

| Constraint | Detail |
| --- | --- |
| `__builtins__` cleared | All Python built-ins are removed from the template context |
| Forbidden names blocked | `__import__`, `eval`, `exec`, `compile`, `open`, `getattr`, `setattr`, `globals`, `locals`, `breakpoint`, etc. |
| Pre-render validation | `${...}` expressions are scanned for dangerous patterns before rendering |
| Only registered functions available | Only functions explicitly injected into the context can be called |
| Simple types recommended | Function parameters and return values should be simple types (`str`, `int`, `float`) |

> **Warning**: Even though `<%...%>` control blocks are escaped, `${...}` expressions can still execute arbitrary Python code if dangerous functions are injected. Always restrict your registry to safe, side-effect-free functions.

### Complete Example: Test Data Generator Plugin

Below is a full example of creating a reusable custom functions package for generating test data:

```python
# my_burunner_testdata/__init__.py

"""Test data generation functions for burunner."""

import random
import string

from burunner.parser.variables import _default_registry


@_default_registry.register("phone")
def _fn_phone(prefix="138"):
    """Generate a random mobile phone number."""
    suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{prefix}{suffix}"


@_default_registry.register("test_email")
def _fn_test_email(name=None):
    """Generate a test email address."""
    if name is None:
        name = "".join(random.choices(string.ascii_lowercase, k=6))
    return f"{name}@test.example.com"


@_default_registry.register("id_card")
def _fn_id_card():
    """Generate a random 18-digit ID card number (for testing only)."""
    area = str(random.randint(110000, 659999))
    year = str(random.randint(1970, 2005))
    month = f"{random.randint(1, 12):02d}"
    day = f"{random.randint(1, 28):02d}"
    seq = f"{random.randint(1, 999):03d}"
    base = f"{area}{year}{month}{day}{seq}"
    # Simplified check digit
    check = str(random.randint(0, 9))
    return f"{base}{check}"


@_default_registry.register("company_name")
def _fn_company_name():
    """Generate a random company name for testing."""
    prefixes = ["Acme", "Global", "Tech", "Smart", "Cloud"]
    suffixes = ["Corp", "Inc", "Ltd", "Solutions", "Systems"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"
```

Usage in test YAML:

```yaml
cases:
  - name: User registration test
    steps:
      - Navigate to registration page
      - Enter phone ${phone()}
      - Enter email ${test_email()}
      - Enter ID ${id_card()}
      - Enter company ${company_name()}
      - Click submit
```

To use this package, ensure it is imported at startup:

```python
# conftest.py or startup script
import my_burunner_testdata  # noqa: F401 — triggers registration
```

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
| Notification Channel | Factory + Inheritance + entry_points | `BaseNotifier.send()` + `NOTIFIER_REGISTRY` / `entry_points` |
| Variable Functions | Registry + Mako sandbox | `VariableRegistry` + `_default_registry` |
| Data Source | Suffix matching + loader function | `resolve_data_source()` |
| Browser Driver | Parameter extension | `create_session()` |
| Reporter | Registry + Inheritance | `BaseReporter` + `REPORTER_REGISTRY` |
