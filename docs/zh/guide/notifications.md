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
