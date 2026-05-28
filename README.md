# burunner — 基于 browser-use 的自然语言浏览器测试框架

burunner 是一个独立的端到端测试框架：

- 用 YAML + 自然语言描述测试用例，无需写脚手架代码
- 不依赖 pytest / unittest，自带执行引擎
- 基于 [browser-use](https://github.com/browser-use/browser-use) 的浏览器自动化
- 支持多 LLM provider（OpenAI / Azure / Anthropic / Google / DeepSeek / Ollama / Grok / Mistral / 阿里云 DashScope / ModelScope / MoonShot / SiliconFlow / IBM / Unbound）
- 支持多浏览器类型（Chromium / Chrome / Edge 及其各开发通道）
- 预设（presets）继承机制，共享公共前置步骤
- 预设 Cookie 注入，免登录执行
- 参数化变量与函数调用（`${var}` / `${func()}`）
- 数据驱动测试（CSV / JSON / YAML / 内联数据）
- 多环境配置（dev / staging / prod），一套用例多环境运行
- 并发执行（Worker Pool），单用例超时控制，自动重试
- 失败自动截图（结合 `use_vision`）
- 测试完成后自动发送通知（企业微信 / 飞书 / 钉钉）
- 输出每个用例的耗时与 token 消耗，并汇总总计
- 报告以标准 [Allure](https://allurereport.org/) 格式（`allure-results`）输出，HTML 由 `allure` CLI 生成

---

## 1. 安装

```bash
git clone <this-repo>
cd browser-use-runner

python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .

# 浏览器内核（首次运行需要）
python -m playwright install chromium

# 如需使用 Chrome / Edge 等其他浏览器，需本地已安装对应浏览器
```

按需安装可选 LLM 依赖（参考 `requirements.txt` 注释）：

```bash
pip install anthropic       # Claude
pip install google-generativeai  # Gemini
pip install ollama          # Ollama
```

---

## 2. 配置环境变量

复制 `.env.example` 为 `.env`，按需填写：

```bash
cp .env.example .env
```

关键变量：

| 变量 | 说明 |
| --- | --- |
| `BURUNNER_LLM_PROVIDER` | 默认 provider，如 `openai` |
| `BURUNNER_LLM_MODEL` | 默认模型，如 `gpt-4o` |
| `BURUNNER_LLM_TEMPERATURE` | 采样温度，默认 0.0 |
| `BURUNNER_LLM_API_KEY` | 统一的 API key |
| `BURUNNER_LLM_BASE_URL` | 统一的 base URL（可选） |
| `BURUNNER_AZURE_API_VERSION` | Azure OpenAI API 版本（仅 Azure 需要） |
| `BURUNNER_IBM_PROJECT_ID` | IBM watsonx 项目 ID（仅 IBM 需要） |
| `BURUNNER_HEADLESS` | 是否无头模式，默认 `true` |
| `BURUNNER_PARALLEL` | 并发度，默认 `1` |
| `BURUNNER_MAX_STEPS` | 单用例最大步数，默认 `30` |
| `BURUNNER_CASE_TIMEOUT` | 单用例超时（秒），`0` 表示不限，默认 `0` |
| `BURUNNER_RETRY_COUNT` | 异常用例重试次数，默认 `0` |
| `BURUNNER_RETRY_DELAY` | 重试间隔（秒），默认 `2.0` |
| `BURUNNER_BROWSER_CHANNEL` | 浏览器类型（`chromium`/`chrome`/`msedge` 等），默认 `chromium` |
| `BURUNNER_ENV` | 默认运行环境名（对应 YAML `environments`），默认无 |
| `BURUNNER_NOTIFY_CHANNEL` | 通知渠道（`wecom`/`feishu`/`dingtalk`），默认无 |
| `BURUNNER_NOTIFY_WEBHOOK` | 通知 Webhook URL |

CLI 参数 `--llm` `--model` `--api-key` `--base-url` 等优先级最高。

---

## 3. 编写测试用例

YAML 顶层是 **用例列表**（也可用 `{cases: [...]}` 形式），每个用例如下：

```yaml
- name: 用例名称（必填，唯一）
  description: 简短描述（可选）
  tags: [smoke, login]    # 可选，用于标签过滤
  steps:
    - 第一步：自然语言描述
    - 第二步：自然语言描述
    - 第三步：……
  config:                 # 可选，单用例覆盖
    headless: false
```

### 标签（Tags）

用例可通过 `tags` 字段设置标签（字符串数组），用于执行时按标签过滤：

```yaml
- name: 登录功能
  tags: [p1, smoke, login]
  steps:
    - 访问登录页面
    - 输入账号密码并登录

- name: 高级搜索
  tags: [p2, regression]
  steps:
    - 访问搜索页面
    - 执行高级搜索操作
```

运行时使用 `-t` / `--tags` 指定要执行的标签，多个标签用逗号分隔，匹配关系为 **OR**（用例只需包含其中任一标签即被选中）：

```bash
# 只执行包含 p1 标签的用例
burunner run tests/*.yaml -t p1

# 执行包含 p1 或 smoke 标签的用例
burunner run tests/*.yaml -t "p1,smoke"

# 可与 -k 名称过滤组合（两者同时满足）
burunner run tests/*.yaml -k "登录" -t "smoke"
```

标签匹配不区分大小写。

也支持顶层 `config:` 覆盖运行配置：

```yaml
config:
  llm_provider: openai
  llm_model: gpt-4o
  parallel: 2
  max_steps: 40

cases:
  - name: 用例 A
    steps:
      - 访问 https://example.com
      - 点击登录按钮
```

### 预设（Presets）—— 公共步骤继承

多个用例共享相同前置流程时，可用 `presets` 定义公共步骤，在用例中用 `preset` 关键字继承：

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

  - name: 修改设置
    preset: 已登录用户
    steps:
      - 进入设置页面
      - 修改通知偏好
```

执行时，用例的 `steps` 会追加在 `preset` 的 `steps` 之后，合并为一个完整流程。

### 预设 Cookie 注入

在用例或全局 `config:` 中定义 `cookies`，测试执行时自动注入到浏览器上下文，可实现免登录等场景：

```yaml
config:
  cookies:
    - name: token
      value: abc123
      domain: .example.com
    - name: user_id
      value: "1001"
      domain: .example.com

cases:
  - name: 已登录状态访问
    cookies:
      - name: session_id
        value: xyz789
        domain: .example.com
    steps:
      - 访问个人主页
      - 验证页面显示用户名
```

Cookie 合并规则：用例级 `cookies` 优先于全局 `config.cookies`，同名同 domain 的 cookie 以用例级为准。

### 参数化变量与函数

YAML 支持 `${var}` 变量替换和 `${func()}` 函数调用：

```yaml
variables:
  base_url: "https://example.com"
  username: "testuser"
  today: "${today()}"    # 函数调用

cases:
  - name: 动态访问页面
    steps:
      - 访问 ${base_url}/login
      - 输入用户名 ${username}
      - 验证日期：${today}
```

内置函数：

| 函数 | 说明 | 返回值 |
| --- | --- | --- |
| `${today()}` | 当前日期 | `YYYY-MM-DD` |
| `${now()}` | 当前时间戳（秒） | `1700000000` |
| `${now_iso()}` | 当前时间 ISO 格式 | `YYYY-MM-DDTHH:MM:SS` |
| `${uuid()}` | 随机 UUID | `550e8400-e29b-41d4-...` |
| `${random_int(min, max)}` | 随机整数 | `42` |

变量还支持三种访问方式（等价）：
- `${base_url}`
- `${env.base_url}`
- `${env.current.base_url}`（多环境模式下）

### 数据驱动测试

用例可通过 `data_driven` 字段引用外部数据源，自动展开为多条用例：

```yaml
cases:
  # CSV 数据驱动
  - name: 搜索功能
    data_driven:
      source: data/search.csv    # CSV 文件路径
    steps:
      - 访问首页
      - 在搜索框输入 ${keyword}
      - 点击搜索按钮
      - 验证搜索结果包含 ${expected}

  # JSON 数据驱动
  - name: 用户登录
    data_driven:
      source: data/users.json    # JSON 数组文件
    steps:
      - 访问登录页
      - 输入账号 ${username} 和密码 ${password}
      - 验证登录结果 ${result}

  # YAML 数据驱动
  - name: 商品测试
    data_driven:
      source: data/products.yaml
    steps:
      - 访问商品页 ${id}

  # 内联数据驱动
  - name: 注册功能
    data_driven:
      data:
        - { email: a@test.com, expect: 成功 }
        - { email: "", expect: 失败 }
    steps:
      - 访问注册页
      - 输入邮箱 ${email}
      - 验证结果包含 ${expect}
```

数据文件格式示例：

```csv
# data/search.csv
keyword,expected
Python,Python教程
Java,Java入门
Go,Go语言
```

```json
// data/users.json
[
  { "username": "alice", "password": "123", "result": "成功" },
  { "username": "bob", "password": "wrong", "result": "失败" }
]
```

### 测试结论判定规则

burunner 在每个用例的 prompt 末尾自动追加要求：

> 完成后必须以一行 JSON 输出最终结论：`{"success": true|false, "reason": "..."}`，并调用 `done(success=...)` 收尾。

判定优先级：

1. Agent 返回 `success=false` 或文本中含"测试失败" → **FAILED**
2. `history.is_successful() == False` → **FAILED**
3. 任意运行期异常（浏览器崩溃 / LLM 超时 / 框架异常） → **ERROR**
4. 其余 → **PASSED**

---

## 4. 多环境配置

YAML 可定义多个环境配置（`environments`），通过 CLI `--env` 参数或 `BURUNNER_ENV` 环境变量激活：

```yaml
environments:
  dev:
    variables:
      base_url: "dev.example.com"
      username: "dev_user"
    config:
      headless: false
      max_steps: 50
    cookies:
      - name: env_token
        value: "dev-token"
        domain: ".dev.example.com"
  staging:
    variables:
      base_url: "staging.example.com"
  prod:
    variables:
      base_url: "prod.example.com"
    config:
      headless: true
```

cases:
  - name: 首页访问
    steps:
      - 访问 ${base_url}
      - 验证页面标题包含 ${app_name}
```

运行：

```bash
burunner run tests.yaml --env dev
burunner run tests.yaml --env staging
```

每个环境独立定义自己的 `variables`、`config` 和 `cookies`，互不继承。

---

## 5. 运行测试

```bash
# 最简
burunner run examples/example.yaml

# 指定 provider / model / 浏览器 / 并行度 / 过滤
burunner run examples/example.yaml \
    --llm openai --model gpt-4o \
    --browser chrome \
    -p 2 \
    -k "通道列表" \
    --headed \
    --max-steps 40 \
    --case-timeout 120 \
    --retry 2 \
    --results-dir ./allure-results

# 按标签过滤：只执行包含 p1 或 smoke 标签的用例
burunner run examples/example.yaml -t "p1,smoke"

# 标签与名称过滤组合使用
burunner run examples/example.yaml -k "通道" -t "p1"

# 指定运行环境
burunner run tests.yaml --env dev

# 使用 .env 中配置的默认浏览器
# BURUNNER_BROWSER_CHANNEL=msedge
burunner run tests.yaml
```

进程退出码：全部 PASSED → `0`；任一 FAILED/ERROR → `1`，便于 CI 集成。

### 完整 CLI 选项

```
burunner run PATH [PATH ...]
  -k, --filter TEXT          正则过滤用例 name
  -t, --tags TEXT            按标签过滤（逗号分隔，OR 关系）
  -p, --parallel INTEGER     并行度，默认 1
      --llm TEXT             provider: openai/azure_openai/anthropic/google/
                             deepseek/ollama/grok/mistral/alibaba/modelscope/
                             moonshot/siliconflow/ibm/unbound
      --model TEXT
      --temperature FLOAT
      --base-url TEXT
      --api-key TEXT
      --headless / --headed  默认 headless
      --browser CHANNEL      浏览器类型（chromium/chrome/msedge 等），默认 chromium
      --max-steps INTEGER    单用例最大 Agent 步数，默认 30
      --case-timeout SECONDS 单用例超时（0=不限），默认 0
      --retry COUNT          异常用例自动重试次数，默认 0
      --results-dir PATH     默认 ./allure-results
      --keep-browser-open    调试用
      --no-vision            禁用 use_vision
      --no-progress          关闭实时进度显示
  -e, --env TEXT             运行环境名（对应 YAML environments）
  -v, --verbose
```

### 输出示例

```
Provider=openai  Model=gpt-4o  Browser=chromium  Parallel=2  Headless=True  Timeout=∞s  Retry=0  Env=default  Cases=2
[1/2] 通道列表查询 ... PASS (12.34s, tokens: 1801)
[2/2] 通道列表查询2 ... FAIL (20.11s, tokens: 3090)
      截图: allure-results/screenshots/...

=================================================================
Total: 2  Passed: 1  Failed: 1  Error:  0
Total elapsed: 32.45s
Total tokens: in=3344  out=1547  total=4891
Allure results: ./allure-results  (run: allure serve ./allure-results)
=================================================================
```

---

## 6. 生成 Allure HTML 报告

burunner 仅写出标准 `allure-results/*.json`（含 step、参数、token 用量、失败截图、Agent 输出附件）。HTML 报告由 [Allure CLI](https://allurereport.org/docs/install/) 生成：

```bash
# macOS
brew install allure

# 一次性预览
allure serve ./allure-results

# 生成静态 HTML 站点
allure generate ./allure-results -o ./allure-report --clean
open allure-report/index.html
```

报告包含：

- 用例通过 / 失败 / 异常统计
- 每个用例的执行时间、provider、model、input/output/total tokens
- 失败截图 + Agent 最终输出文本 + traceback 附件
- 按 source 文件聚合的 suite 视图、tag 视图
- 环境信息（burunner 版本、运行环境、LLM provider/model、浏览器类型等）

---

## 7. 测试完成通知

测试执行完毕后，可自动发送通知到企业微信、飞书或钉钉。通知内容包括：套件名称、执行状态、耗时、通过率、失败用例列表、运行环境等。

### 配置方式（`.env` 文件）

```bash
# 通知渠道（一次只激活一个）: wecom / feishu / dingtalk
BURUNNER_NOTIFY_CHANNEL=wecom
# 对应平台的 Webhook URL
BURUNNER_NOTIFY_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

通知在 `print_summary()` 之后、`sys.exit()` 之前发送。发送失败仅打印错误日志，不影响主流程和退出码。

### 通知示例

**企业微信**（Markdown 格式）：

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

---

## 8. 目录结构

```
browser-use-runner/
├── src/
│   └── burunner/
│       ├── cli.py              # 命令行入口
│       ├── config.py           # 运行时配置
│       ├── llm/provider.py     # 多 provider 工厂（注册表+策略模式）
│       ├── notifier/           # 测试完成通知
│       │   ├── base.py         # 通知器基类 + 载荷定义
│       │   ├── wecom.py        # 企业微信 Webhook
│       │   ├── feishu.py       # 飞书消息卡片
│       │   ├── dingtalk.py     # 钉钉 Markdown
│       │   └── factory.py      # 通知器工厂
│       ├── parser/             # YAML 解析
│       │   ├── models.py       # 数据模型（TestCase, TestSuite, EnvConfig, CookieItem）
│       │   └── yaml_parser.py  # YAML 解析器（含环境/预设/数据驱动/变量替换）
│       ├── runner/             # 执行引擎与并行调度
│       │   ├── executor.py     # 单用例执行器
│       │   ├── orchestrator.py # Worker Pool 并发调度 + 超时 + 重试
│       │   ├── result.py       # 结果数据结构
│       │   └── progress.py     # 进度跟踪器
│       ├── browser/            # BrowserSession 封装
│       │   └── session.py      # 多浏览器 channel 支持
│       ├── reporter/           # 控制台 + Allure
│       ├── utils/              # tokens / 截图 / 日志
│       └── exceptions.py       # 分层异常体系
├── examples/example.yaml
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## 9. 扩展

- **新增 LLM provider**：在 `burunner/llm/provider.py` 添加分支，复用 browser-use 内置的 `Chat*` 类即可。
- **自定义结果输出**：直接消费 `burunner.runner.run_suite` 返回的 `SuiteResult`，或在 `cli.py` 中替换 `on_complete` 回调。
- **新增通知渠道**：在 `burunner/notifier/` 下实现 `BaseNotifier` 子类，并在 `factory.py` 注册。
- **用例级覆盖**：在用例 yaml 里写 `config:` 字段（当前通过顶层 config 覆盖；用例级动态覆盖可通过自定义 hook 实现）。
- **自定义浏览器驱动**：实现 `BrowserDriver` 协议，通过 `create_session(driver=...)` 注入。

---

## 10. 常见问题

**Q: 浏览器没有打开？**
默认 headless，加 `--headed` 可见。

**Q: 报错 "缺少依赖 …"？**
对应 provider 的可选依赖未安装，按提示 `pip install` 即可。

**Q: 报告里没有截图？**
仅在 FAILED / ERROR 时截图。若依然缺失，确认浏览器仍存活（异常发生在浏览器崩溃后则只能从 vision 历史回退抓取）。

**Q: 如何在 CI 中跑？**

```bash
burunner run examples/*.yaml --headless || EXIT=$?
allure generate ./allure-results -o ./allure-report --clean
exit ${EXIT:-0}
```

**Q: 如何切换浏览器？**
通过 `--browser` 参数或 `.env` 中的 `BURUNNER_BROWSER_CHANNEL`：

```bash
burunner run tests.yaml --browser msedge
# 或 .env 中配置 BURUNNER_BROWSER_CHANNEL=chrome
```

注意：browser-use 仅支持 Chromium 内核浏览器（chromium / chrome / msedge 及其各开发通道），不支持 Firefox / Safari。

**Q: 用例执行超时或被强制终止？**
使用 `--case-timeout` 设置单用例超时（秒），`0` 表示不限制：

```bash
burunner run tests.yaml --case-timeout 120
```

**Q: 用例执行异常后自动重试？**
使用 `--retry` 设置重试次数（仅对 ERROR 状态生效，FAILED 业务断言不重试）：

```bash
burunner run tests.yaml --retry 2
```

**Q: 通知发送失败怎么办？**
通知发送失败仅打印错误日志，不影响主流程和退出码。检查 `BURUNNER_NOTIFY_CHANNEL` 和 `BURUNNER_NOTIFY_WEBHOOK` 是否正确。
