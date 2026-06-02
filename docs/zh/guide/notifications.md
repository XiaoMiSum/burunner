# 通知配置

burunner 支持测试执行完毕后自动发送通知到企业微信、飞书或钉钉。

## 支持渠道

| 渠道 | `BURUNNER_NOTIFY_CHANNEL` 值 | 消息格式 |
| --- | --- | --- |
| 企业微信 | `wecom` | Markdown |
| 飞书 | `feishu` | 消息卡片 |
| 钉钉 | `dingtalk` | Markdown |

## 配置方式

在 `.env` 文件中配置：

```bash
# 通知渠道（一次只激活一个）
BURUNNER_NOTIFY_CHANNEL=wecom

# 对应平台的 Webhook URL
BURUNNER_NOTIFY_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

### 各平台 Webhook 获取方式

- **企业微信**：群聊 → 群机器人 → 添加 → 复制 Webhook 地址
- **飞书**：群聊 → 设置 → 群机器人 → 添加自定义机器人 → 复制 Webhook 地址
- **钉钉**：群聊 → 设置 → 智能群助手 → 添加自定义机器人 → 复制 Webhook 地址

## 通知触发时机

通知在以下时间点发送：

1. 所有用例执行完毕
2. `print_summary()` 控制台汇总输出之后
3. `sys.exit()` 进程退出之前

## 通知内容

通知消息包含：

| 内容 | 说明 |
| --- | --- |
| 套件名称 | YAML 文件名 |
| 执行状态 | 全部通过 / 存在失败 |
| 总耗时 | 从开始到结束的总时间 |
| 通过率 | 通过数 / 总数 百分比 |
| 用例统计 | 总数、通过、失败、异常 |
| 失败用例 | 失败用例名称列表 |
| 运行环境 | 当前激活的环境名 |

## 发送失败处理

通知发送失败**不影响主流程**：

- 仅打印错误日志到控制台
- 不改变进程退出码
- 不中断后续流程

## 各平台消息格式示例

### 企业微信（Markdown）

```
# ✅ 全部通过

> 测试套件: example.yaml
> 运行环境: dev

**执行结果**
- 总数: 10
- 通过: 10
- 失败: 0
- 通过率: 100.0%
- 耗时: 2m 35s
```

存在失败时：

```
# ❌ 存在失败

> 测试套件: example.yaml
> 运行环境: staging

**执行结果**
- 总数: 10
- 通过: 8
- 失败: 2
- 通过率: 80.0%
- 耗时: 5m 12s

**失败用例**
- 登录功能
- 订单创建
```

### 飞书（消息卡片）

飞书使用富文本消息卡片格式，内容与企业微信一致，展示形式为结构化卡片。

### 钉钉（Markdown）

```
# 测试报告

**✅ 全部通过**

- 套件: example.yaml
- 环境: prod
- 总数: 10
- 通过: 10
- 失败: 0
- 通过率: 100.0%
- 耗时: 2m 35s
```

## 完整配置示例

### 企业微信

```bash
BURUNNER_NOTIFY_CHANNEL=wecom
BURUNNER_NOTIFY_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key
```

### 飞书

```bash
BURUNNER_NOTIFY_CHANNEL=feishu
BURUNNER_NOTIFY_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your-token
```

### 钉钉

```bash
BURUNNER_NOTIFY_CHANNEL=dingtalk
BURUNNER_NOTIFY_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=your-token
```

## 插件化扩展

burunner 的通知模块支持通过 Python `entry_points` 机制注册外部通知器插件。安装插件包后即可直接使用，无需修改 burunner 源代码。

### 插件发现机制

burunner 启动时会自动扫描 `burunner.notifiers` 组下的所有 entry_points：

1. 内置通知器（wecom/feishu/dingtalk）始终可用
2. 外部插件通过 `entry_points(group="burunner.notifiers")` 注册
3. 插件名称即为 `BURUNNER_NOTIFY_CHANNEL` 的值

### 开发外部插件

#### 1. 创建通知器类

```python
# my_notifier_pkg/slack.py
from burunner.notifier.base import BaseNotifier, NotifyPayload

class SlackNotifier(BaseNotifier):
    """自定义 Slack 通知器。"""

    def send(self, payload: NotifyPayload) -> bool:
        """发送通知，成功返回 True。"""
        # 实现发送逻辑...
        return True
```

#### 2. 配置 entry_points

在插件包的 `pyproject.toml` 中声明：

```toml
[project.entry-points."burunner.notifiers"]
slack = "my_notifier_pkg.slack:SlackNotifier"
```

或在 `setup.cfg` / `setup.py` 中：

```ini
[options.entry_points]
burunner.notifiers =
    slack = my_notifier_pkg.slack:SlackNotifier
```

#### 3. 安装并使用

```bash
pip install my-notifier-pkg

# .env
BURUNNER_NOTIFY_CHANNEL=slack
BURUNNER_NOTIFY_WEBHOOK=https://hooks.slack.com/services/xxx
```

安装后 burunner 会自动发现并加载该插件，无需额外配置。

> 更多插件开发细节请参考 [扩展开发指南](/zh/development/extending)。
