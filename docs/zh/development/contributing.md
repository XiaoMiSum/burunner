# 贡献指南

感谢你对 burunner 项目的关注！本文档介绍如何搭建开发环境、参与代码贡献。

---

## 开发环境搭建

### 前置要求

- Python 3.11+
- Git
- 系统已安装 Chromium 内核浏览器（Chrome / Edge 可选）

### 初始化步骤

```bash
# 1. 克隆仓库
git clone https://github.com/<org>/browser-use-runner.git
cd browser-use-runner

# 2. 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖（含开发模式）
pip install -r requirements.txt
pip install -e .

# 4. 安装 Playwright 浏览器内核
python -m playwright install chromium

# 5. 复制环境变量模板
cp .env.example .env
# 根据需要填写 BURUNNER_LLM_PROVIDER / BURUNNER_LLM_API_KEY 等
```

### 可选 LLM 依赖

```bash
pip install anthropic          # Claude
pip install google-generativeai # Gemini
pip install ollama             # Ollama
```

---

## 代码结构

```
src/burunner/
├── cli.py              # CLI 入口（Click 框架）
├── config.py           # 运行时配置（dataclass + .env 加载）
├── exceptions.py       # 分层异常体系
├── llm/
│   └── provider.py     # 多 Provider 工厂（注册表 + 策略模式）
├── notifier/           # 测试完成通知
│   ├── base.py         # 通知器基类 + 载荷定义
│   ├── wecom.py        # 企业微信
│   ├── feishu.py       # 飞书
│   ├── dingtalk.py     # 钉钉
│   └── factory.py      # 通知器工厂
├── parser/             # YAML 解析
│   ├── models.py       # 数据模型（TestCase, TestSuite 等）
│   ├── datasource.py   # 数据源加载（CSV/JSON/YAML）
│   ├── variables.py    # 变量替换引擎
│   └── yaml_parser.py  # 解析器主逻辑
├── runner/             # 执行引擎
│   ├── executor.py     # 单用例执行器
│   ├── orchestrator.py # Worker Pool 并发调度
│   ├── result.py       # 结果数据结构
│   └── progress.py     # 进度跟踪
├── browser/
│   └── session.py      # Playwright 浏览器会话管理
├── reporter/           # 报告输出（Console + Allure）
└── utils/              # 工具函数（日志/截图/token 统计）
```

---

## 分支策略

| 分支 | 用途 |
| --- | --- |
| `main` | 稳定主线，所有合并需通过 PR |
| `feature/*` | 新功能开发 |
| `fix/*` | Bug 修复 |
| `refactor/*` | 重构改进 |

**工作流**：

1. 从 `main` 创建 feature/fix 分支
2. 本地开发并提交（保持 commit 原子性）
3. 推送后发起 Pull Request
4. Review 通过后 squash merge 到 `main`

---

## 代码规范

### 类型注解

所有公共函数和方法必须包含完整的类型注解：

```python
def get_llm_model(
    provider: str,
    *,
    model_name: str,
    temperature: float = 0.0,
    base_url: str | None = None,
) -> Any:
    ...
```

### Docstring

模块、类、公共函数需编写 docstring：

```python
"""模块描述。"""

class RunnerConfig:
    """单次运行的全局配置。CLI 参数 > yaml config 段 > .env > 默认值。"""
    ...
```

### 异常处理

- 自定义异常继承 `BurunnerError`
- 配置类错误使用 `ConfigurationError`
- 执行类错误使用 `ExecutionError` 及其子类
- 不可恢复错误（如配置无效）应立即终止
- 可重试错误（如网络超时）使用 `TransientError`

### 命名约定

- 文件名：`snake_case.py`
- 类名：`PascalCase`
- 函数/变量：`snake_case`
- 常量：`UPPER_SNAKE_CASE`
- 私有成员：`_leading_underscore`

---

## PR 提交规范

### Commit 格式

```
<type>(<scope>): <subject>

<body>
```

**type 可选值**：

- `feat`: 新功能
- `fix`: 修复 Bug
- `refactor`: 重构
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具链

**示例**：

```
feat(notifier): add Slack notification channel

- Implement SlackNotifier extending BaseNotifier
- Register in factory.py
- Add webhook URL config support
```

### PR 描述模板

- **What**: 做了什么改动
- **Why**: 为什么需要这个改动
- **How**: 如何验证

---

## 本地测试方法

### 验证 YAML 解析

```bash
burunner validate examples/example.yaml
```

### 执行测试用例

```bash
# 基本执行
burunner run examples/example.yaml --headed

# 指定 provider 和模型
burunner run examples/example.yaml --llm openai --model gpt-4o

# 按名称过滤
burunner run examples/example.yaml -k "搜索"

# 按标签过滤
burunner run examples/example.yaml -t "smoke"
```

### 查看 Allure 报告

```bash
allure serve ./allure-results
```

---

## 注意事项

- 确保 `.env` 不会被提交到仓库（已在 `.gitignore` 中排除）
- 新增 LLM Provider 后需在 `SUPPORTED_PROVIDERS` 元组中可见
- 新增通知渠道后需在 `NOTIFIER_REGISTRY` 和 `SUPPORTED_CHANNELS` 中注册
- 保持向后兼容：YAML 用例格式变更需兼容旧格式
