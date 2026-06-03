# burunner — 基于 browser-use 的自然语言浏览器测试框架

[![Documentation](https://img.shields.io/badge/docs-online-blue)](https://xiaomisum.github.io/burunner/)
[![PyPI](https://img.shields.io/pypi/v/burunner.svg)](https://pypi.org/project/burunner/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-458%20passed-brightgreen.svg)](https://github.com/xiaomisum/burunner)
[![Coverage](https://img.shields.io/badge/coverage-93.1%25-brightgreen.svg)](https://github.com/xiaomisum/burunner)

**📖 在线文档**: [查看](https://xiaomisum.github.io/burunner)

---

## 🌟 核心特性

### 🎯 自然语言测试
- **YAML + 自然语言**描述测试用例，无需编写代码
- **自带执行引擎**，不依赖 pytest / unittest
- **AI 驱动**，基于 [browser-use](https://github.com/browser-use/browser-use) 智能浏览器自动化
- **智能结果判定**，自动从 Agent 输出中解析测试结论

### 🤖 多 LLM 支持
支持 **12+ LLM Provider**：
- OpenAI / Azure OpenAI / Anthropic (Claude)
- Google (Gemini) / DeepSeek / Ollama
- Grok / Mistral / 阿里云 DashScope
- ModelScope / MoonShot / SiliconFlow / IBM Watsonx / Unbound
- 支持自定义 LLM 端点和 API Key
- 支持 temperature 调参

### 🌐 多浏览器支持
- Chromium / Chrome / Edge 及其各开发通道
- 支持 Cookie 注入，实现免登录测试
- 支持用户数据目录持久化
- 支持有头/无头模式切换
- 支持 Vision 视觉能力

### ⚡ 高性能执行
- **Worker Pool 并发执行**，渐进启动避免资源尖峰
- **单用例超时控制**，防止用例卡死
- **自动重试机制**，INCOMPLETE/ERROR 状态自动重试
- 失败自动截图，结合 vision 能力
- 支持调试模式保留浏览器打开状态

### 📊 丰富的测试能力
- **参数化变量与函数** - `${var}` / `${func()}` 动态数据，支持 12+ 内置函数
- **数据驱动测试** - CSV / JSON / YAML / 内联数据，支持数据过滤和跳过
- **多环境配置** - dev / staging / prod 一套用例多环境运行
- **预设继承** - 公共步骤复用，减少重复
- **标签过滤** - 灵活筛选测试用例
- **名称过滤** - 正则表达式匹配用例名
- **步骤级状态追踪** - 每个测试步骤独立追踪状态、耗时和错误，失败精确定位到具体步骤

### 📈 完善的报告与通知
- **Allure 报告** - 标准 allure-results 格式，包含截图、token 用量、步骤级精确状态
- **步骤级报告** - 每个步骤独立显示 PASSED/FAILED/INCOMPLETE 状态和精确耗时
- **实时进度** - 动态进度条，支持关闭
- **通知集成** - 企业微信 / 飞书 / 钉钉自动推送测试结果
- **Token 统计** - 每个用例耗时与 token 消耗明细
- **环境信息记录** - provider、model、浏览器、并行度等

---

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/xiaomisum/burunner.git
cd browser-use-runner

python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .

# 安装浏览器内核
python -m playwright install chromium
```

### 2. 配置

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置 LLM：

```bash
BURUNNER_LLM_PROVIDER=openai
BURUNNER_LLM_MODEL=gpt-4o
BURUNNER_LLM_API_KEY=your-api-key
```

### 3. 编写测试用例

创建 `test.yaml`：

```yaml
cases:
  - name: 百度搜索测试
    steps:
      - 访问 https://www.baidu.com
      - 在搜索框输入 "burunner"
      - 点击搜索按钮
      - 验证搜索结果包含 "browser-use"
```

### 4. 运行测试

```bash
burunner run test.yaml
```

**输出示例**：

```
[PASS]  百度搜索测试                      elapsed=15.23s  tokens(in/out/total)=1200/950/2150

=================================================================
Total: 1  Passed: 1  Failed: 0  Error:  0  Incomplete: 0
Total elapsed: 15.23s
Total tokens: in=1200  out=950  total=2150
Allure results: ./allure-results  (run: allure serve ./allure-results)
=================================================================
```

---

## 📖 详细功能

### 标签过滤

```yaml
cases:
  - name: 登录功能
    tags: [p1, smoke, login]
    steps:
      - 访问登录页面
      - 输入账号密码并登录
```

```bash
# 执行包含 p1 或 smoke 标签的用例
burunner run tests.yaml -t "p1,smoke"

# 与名称过滤组合
burunner run tests.yaml -k "登录" -t "smoke"
```

### 预设继承

```yaml
presets:
  已登录用户:
    steps:
      - 打开首页
      - 点击登录按钮
      - 输入正确的账号密码并登录

cases:
  - name: 查看个人信息
    preset: 已登录用户
    steps:
      - 进入个人中心
      - 验证昵称显示正确
```

### Cookie 注入

```yaml
config:
  cookies:
    - name: token
      value: abc123
      domain: .example.com

cases:
  - name: 已登录状态访问
    steps:
      - 访问个人主页
      - 验证页面显示用户名
```

### 变量与函数

```yaml
variables:
  base_url: "https://example.com"
  username: "testuser"
  today: "${date()}"
  order_id: "ORD-${timestamp()}"
  random_code: "${random_int(1000, 9999)}"
  price_calc: "${calc(100 * 0.8)}"

cases:
  - name: 动态访问页面
    steps:
      - 访问 ${base_url}/login
      - 输入用户名 ${username}
      - 验证日期：${today}
      - 使用订单号：${order_id}
      - 输入验证码：${random_code}
      - 验证折扣价格：${price_calc}元
```

**内置函数**：
| 函数 | 说明 | 示例 |
|------|------|------|
| `${date()}` | 当前日期 | `2026-01-30` |
| `${datetime()}` | 当前日期时间 | `2026-01-30 14:30:00` |
| `${utc_datetime()}` | UTC 日期时间 | `2026-01-30 06:30:00` |
| `${timestamp()}` | Unix 时间戳（秒） | `1706601600` |
| `${uuid()}` | UUID4 | `550e8400-e29b-...` |
| `${random_int()}` | 随机整数 (0-9999) | `4231` |
| `${random_int(max)}` | 随机整数 (0-max) | `42` |
| `${random_int(min, max)}` | 随机整数 [min, max] | `50` |
| `${random_string()}` | 随机字符串 (长度8) | `aB3xK9mP` |
| `${random_string(n)}` | 随机字符串 (长度n) | `xY7zQ2` |
| `${env(VAR)}` | 环境变量 | `/usr/bin` |
| `${env(VAR, default)}` | 环境变量 (带默认值) | `default` |
| `${calc(expr)}` | 数学表达式计算 | `100` |

### 数据驱动测试

```yaml
cases:
  - name: 用户登录
    data_driven:
      source: data/users.json
    steps:
      - 访问登录页
      - 输入账号 ${username} 和密码 ${password}
      - 验证登录结果 ${result}
```

**data/users.json**：
```json
[
  { "username": "alice", "password": "123", "result": "成功" },
  { "username": "bob", "password": "wrong", "result": "失败" }
]
```

### 多环境配置

```yaml
environments:
  dev:
    variables:
      base_url: "dev.example.com"
    config:
      headless: false
  prod:
    variables:
      base_url: "prod.example.com"
    config:
      headless: true

cases:
  - name: 首页访问
    steps:
      - 访问 ${base_url}
```

```bash
burunner run tests.yaml --env dev
burunner run tests.yaml --env prod
```

---

## 🔧 CLI 命令

### 运行测试

```bash
burunner run PATH [PATH ...] [OPTIONS]
```

**常用选项**：

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-k, --filter TEXT` | 正则过滤用例名 | - |
| `-t, --tags TEXT` | 标签过滤（OR 关系） | - |
| `-p, --parallel INT` | 并行度 | 1 |
| `--llm TEXT` | LLM provider | openai |
| `--model TEXT` | LLM model | gpt-4o |
| `--browser CHANNEL` | 浏览器类型 | chromium |
| `--headless / --headed` | 无头模式 | headless |
| `--max-steps INT` | 最大步数 | 0 (自动) |
| `--case-timeout SEC` | 单用例超时 | 0 (不限) |
| `--retry COUNT` | 重试次数 | 0 |
| `-e, --env TEXT` | 运行环境 | - |
| `--no-progress` | 关闭进度显示 | - |
| `-v, --verbose` | 详细日志 | - |

**完整示例**：

```bash
burunner run tests/*.yaml \
    --llm openai --model gpt-4o \
    --browser chrome \
    -p 2 \
    -k "登录" \
    -t "smoke" \
    --headed \
    --max-steps 50 \
    --case-timeout 120 \
    --retry 2 \
    --env dev \
    --results-dir ./allure-results
```

---

## 📊 Allure 报告

burunner 生成标准 `allure-results` 格式，使用 Allure CLI 查看：

```bash
# 安装 Allure
brew install allure

# 预览报告
allure serve ./allure-results

# 生成静态 HTML
allure generate ./allure-results -o ./allure-report --clean
open allure-report/index.html
```

**报告包含**：
- ✅ 用例通过/失败/异常统计
- 📋 步骤级状态追踪（每个步骤独立的 PASSED/FAILED/INCOMPLETE 状态和精确耗时）
- ⏱️ 执行时间、provider、model
- 🔢 token 用量统计 (input/output/total)
- 📸 失败截图 + Agent 输出 + traceback
- 🏷️ suite 视图、tag 视图
- ℹ️ 环境信息

---

## 💬 测试通知

测试完成后自动发送通知到企业微信/飞书/钉钉。

### 配置

```bash
# .env
BURUNNER_NOTIFY_CHANNEL=wecom
BURUNNER_NOTIFY_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

### 通知示例

```
✅ 全部通过

> 测试套件: example.yaml
> 运行环境: dev

执行结果
- 总数: 10
- 通过: 10
- 失败: 0
- 通过率: 100.0%
- 耗时: 2m 35s
```

---

## 🏗️ 项目结构

```
browser-use-runner/
├── src/burunner/
│   ├── cli.py              # CLI 命令行入口
│   ├── config.py           # 运行时配置
│   ├── exceptions.py       # 分层异常体系
│   ├── llm/
│   │   └── provider.py     # 多 LLM provider 工厂
│   ├── browser/
│   │   └── session.py      # 浏览器会话管理
│   ├── parser/             # YAML 解析层
│   │   ├── models.py       # 数据模型
│   │   ├── variables.py    # 变量解析引擎 (Mako)
│   │   ├── datasource.py   # 数据源加载
│   │   └── yaml_parser.py  # YAML 解析器
│   ├── runner/             # 执行引擎
│   │   ├── orchestrator.py # Worker Pool 并发调度
│   │   ├── executor.py     # 单用例执行器
│   │   ├── agent_runner.py # Agent 运行器
│   │   ├── verdicts.py     # 结果判定
│   │   ├── session_manager.py  # 会话管理
│   │   ├── progress.py     # 进度追踪
│   │   ├── history_parser.py   # 历史解析
│   │   └── result.py       # 结果数据
│   ├── notifier/           # 通知模块
│   │   ├── base.py         # 通知器基类
│   │   ├── wecom.py        # 企业微信
│   │   ├── feishu.py       # 飞书
│   │   ├── dingtalk.py     # 钉钉
│   │   └── factory.py      # 通知器工厂
│   ├── reporter/           # 报告模块
│   │   ├── base.py         # 报告器基类
│   │   ├── console.py      # 控制台输出
│   │   ├── allure_reporter.py  # Allure 报告
│   │   └── registry.py     # 报告器注册
│   └── utils/              # 工具类
│       ├── logger.py       # 日志工具
│       ├── screenshot.py   # 截图工具
│       └── tokens.py       # Token 统计
├── tests/                  # 单元测试 (458 个)
├── examples/               # 示例文件
└── docs/                   # 文档站点
```

---

## 🔌 扩展开发

### 新增 LLM Provider

在 `burunner/llm/provider.py` 添加分支：

```python
def get_llm_model(provider: str, **kwargs):
    if provider == "my_provider":
        from langchain_my import ChatMy
        return ChatMy(api_key=kwargs.get("api_key"))
```

### 新增通知渠道

实现 `BaseNotifier` 子类：

```python
from burunner.notifier.base import BaseNotifier, NotifyPayload

class MyNotifier(BaseNotifier):
    def send(self, payload: NotifyPayload) -> None:
        # 实现发送逻辑
        pass
```

在 `factory.py` 注册或使用 entry_points：

```toml
# pyproject.toml
[project.entry-points."burunner.notifiers"]
my_channel = "my_package:MyNotifier"
```

### 自定义浏览器驱动

实现 `BrowserDriver` 协议：

```python
from burunner.browser.session import BrowserDriver

class MyBrowserDriver(BrowserDriver):
    async def create_session(self, **kwargs):
        # 创建浏览器会话
        pass
    
    async def close_session(self, session):
        # 关闭会话
        pass
```

---

## ❓ 常见问题

### 浏览器没有打开？

默认 headless 模式，使用 `--headed` 参数可见：

```bash
burunner run tests.yaml --headed
```

### 报错 "缺少依赖"？

安装对应 LLM provider 的可选依赖：

```bash
pip install anthropic       # Claude
pip install google-generativeai  # Gemini
pip install ollama          # Ollama
```

### 如何切换浏览器？

```bash
burunner run tests.yaml --browser msedge
```

或在 `.env` 中配置：

```bash
BURUNNER_BROWSER_CHANNEL=chrome
```

**注意**：仅支持 Chromium 内核浏览器。

### 如何在 CI 中运行？

```bash
burunner run examples/*.yaml --headless || EXIT=$?
allure generate ./allure-results -o ./allure-report --clean
exit ${EXIT:-0}
```

### 用例执行超时？

使用 `--case-timeout` 设置超时（秒）：

```bash
burunner run tests.yaml --case-timeout 120
```

### 自动重试？

使用 `--retry` 设置重试次数（仅 ERROR 状态）：

```bash
burunner run tests.yaml --retry 2
```

---

## 📄 许可证

[MIT License](LICENSE)

---

## 🙏 致谢

- [browser-use](https://github.com/browser-use/browser-use) - 浏览器自动化基础能力
- [Allure](https://allurereport.org/) - 测试报告框架
- [Mako](https://www.makotemplates.org/) - 模板引擎

---

**📖 完整文档**: [https://xiaomisum.github.io/burunner/](https://xiaomisum.github.io/burunner/)
