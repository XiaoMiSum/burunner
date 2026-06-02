# Notifications

burunner can automatically send test result notifications to team messaging platforms after test execution completes.

## Supported Channels

| Channel    | Platform         | Config Value |
| ---------- | ---------------- | ------------ |
| WeCom      | WeChat Work      | `wecom`      |
| Feishu     | Feishu / Lark    | `feishu`     |
| DingTalk   | DingTalk         | `dingtalk`   |

## Configuration

Set two environment variables in your `.env` file:

```bash
# Notification channel (only one active at a time): wecom / feishu / dingtalk
BURUNNER_NOTIFY_CHANNEL=wecom

# Webhook URL for the chosen platform
BURUNNER_NOTIFY_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key
```

### Webhook URLs by Platform

| Platform | Webhook URL Format                                                    |
| -------- | --------------------------------------------------------------------- |
| WeCom    | `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<KEY>`         |
| Feishu   | `https://open.feishu.cn/open-apis/bot/v2/hook/<TOKEN>`               |
| DingTalk | `https://oapi.dingtalk.com/robot/send?access_token=<TOKEN>`          |

## Trigger Timing

Notifications are sent:
1. **After** the summary is printed (`print_summary()`)
2. **Before** the process exits (`sys.exit()`)

This ensures the notification contains the complete test results.

## Notification Content

Each notification includes:

| Field          | Description                               |
| -------------- | ----------------------------------------- |
| Suite name     | Source YAML filename                       |
| Status         | Overall pass/fail indicator                |
| Environment    | Active environment name (or "default")     |
| Duration       | Total execution time                       |
| Statistics     | Total / Passed / Failed / Error counts     |
| Pass rate      | Percentage of passed cases                 |
| Failed cases   | List of failed case names (up to 10)       |

## Failure Handling

Notification delivery **does not affect the main test flow**:

- If sending fails, an error message is logged to stderr
- The process exit code remains based on test results (0 or 1)
- Notification errors never cause the process to crash

## Message Format Examples

### WeCom (Markdown)

```markdown
**测试执行报告**

**套件**: smoke_tests.yaml
**状态**: ✅ 全部通过
**环境**: staging
**耗时**: 2m35s
**统计**: 总计 10 | 通过 10 | 失败 0 | 错误 0
**通过率**: 100.0%
```

When there are failures:

```markdown
**测试执行报告**

**套件**: regression.yaml
**状态**: ❌ 存在失败
**环境**: dev
**耗时**: 5m12s
**统计**: 总计 15 | 通过 12 | 失败 2 | 错误 1
**通过率**: 80.0%

**失败用例**:
- Login with expired token
- Checkout empty cart
```

### Feishu (Interactive Card)

Feishu notifications use the interactive message card format with structured fields:

```
Title: ❌ 存在失败

Suite: regression.yaml
Environment: prod
Duration: 3m45s
Total: 20 | Passed: 18 | Failed: 2 | Error: 0
Pass Rate: 90.0%

Failed Cases:
- Payment timeout handling
- Multi-currency checkout
```

### DingTalk (Markdown)

```markdown
# 测试执行报告

**套件**: smoke_tests.yaml
**状态**: ✅ 全部通过
**环境**: default
**耗时**: 1m20s
**统计**: 总计 5 | 通过 5 | 失败 0 | 错误 0
**通过率**: 100.0%
```

## Complete Setup Example

### 1. Configure `.env`

```bash
BURUNNER_NOTIFY_CHANNEL=feishu
BURUNNER_NOTIFY_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your-token
```

### 2. Run Tests

```bash
burunner run tests/*.yaml --env staging
```

### 3. Output

```
[PASS]  Login test                        elapsed=8.20s   tokens(in/out/total)=800/400/1200
...
[PASS]  Logout test                       elapsed=5.10s   tokens(in/out/total)=500/300/800

=================================================================
Total: 10  Passed: 10  Failed: 0  Error:  0  Incomplete: 0
Total elapsed: 65.30s
Total tokens: in=8000  out=3500  total=11500
Allure results: ./allure-results  (run: allure serve ./allure-results)
=================================================================
Notification sent.
```

## Disabling Notifications

To disable notifications, simply leave `BURUNNER_NOTIFY_CHANNEL` empty or unset:

```bash
BURUNNER_NOTIFY_CHANNEL=
```

Or remove both variables from your `.env` file entirely.

## Plugin System

burunner's notification system is fully pluggable. External packages can register custom notifiers via Python's `entry_points` mechanism.

### How It Works

When burunner initializes, it discovers all notifiers registered under the `burunner.notifiers` entry point group. This means you can create a standalone Python package that provides a notifier, and burunner will automatically detect and use it.

### Creating a Custom Notifier Plugin

#### 1. Implement the Notifier

Create a class that inherits from `BaseNotifier` and implements the `send()` method:

```python
# my_notifier_pkg/slack.py

from burunner.notifier.base import BaseNotifier, NotifyPayload


class SlackNotifier(BaseNotifier):
    """Slack Webhook notifier."""

    def send(self, payload: NotifyPayload) -> bool:
        """Send notification. Returns True on success."""
        import json
        import urllib.request

        body = {"text": "\n".join(self._build_summary_lines(payload))}
        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False
```

#### 2. Configure entry_points

In your package's `pyproject.toml`:

```toml
[project.entry-points."burunner.notifiers"]
slack = "my_notifier_pkg.slack:SlackNotifier"
```

Or in `setup.py`:

```python
setup(
    name="burunner-slack-notifier",
    # ...
    entry_points={
        "burunner.notifiers": [
            "slack = my_notifier_pkg.slack:SlackNotifier",
        ],
    },
)
```

The entry point name (e.g., `slack`) becomes the channel value used in `BURUNNER_NOTIFY_CHANNEL`.

#### 3. Install and Use

```bash
pip install my-notifier-pkg

# .env
BURUNNER_NOTIFY_CHANNEL=slack
BURUNNER_NOTIFY_WEBHOOK=https://hooks.slack.com/services/xxx
```

burunner will automatically discover and load the `slack` notifier from your package.
