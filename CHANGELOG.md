# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 引入 Mako 模板引擎作为变量与函数系统底层,支持 `${expression}` 内联 Python 表达式求值
- 新增 `INCOMPLETE` 执行状态，表示 Agent 执行未完成（超过最大步骤数）
- 新增 browser-use 执行日志开关（`BURUNNER_BROWSER_USE_LOG`），默认关闭
- 新增 CLI 选项 `--browser-use-log` 控制 browser-use 日志输出
- 通知模块插件化，支持外部包通过 `entry_points(group="burunner.notifiers")` 注册自定义通知器
- 新增 `HistoryParser` 类统一封装 browser-use Agent history 对象解析
- 新增 `VerdictJudge` 类独立封装结果判定逻辑
- 新增 `managed_session` async context manager 管理浏览器会话生命周期
- 新增 `agent_runner.py` 封装 Agent 初始化与版本兼容性处理
- Agent 最大步骤数支持动态计算（测试步骤数 × 20），可通过 `BURUNNER_MAX_STEPS` 环境变量覆盖
- Mako 模板安全沙箱：输入预检 + 运行时隔离，阻止任意代码执行
- **完整的单元测试体系**
  - 23 个测试文件,458 个测试用例
  - 模块覆盖率 93.1% (27/29)
  - 测试通过率 100% (456 passed, 0 failed)
  - 核心功能 100% 覆盖 (Parser/Runner/Notifier/Utils/Browser/LLM)

### Changed

- 变量系统底层从自定义正则解析改为 Mako 模板引擎渲染，保留 `${var}` / `${func()}` 语法
- 重试规则重新设计：仅 INCOMPLETE 和 ERROR 状态触发重试，FAILED（验证不通过）不再重试
- `executor.py` 拆分为 4 个独立模块（verdicts / session_manager / agent_runner / executor）
- `max_steps` 默认值改为 0（自动计算），不再硬编码 30
- 环境变量命名统一：移除 `BROWSER_USE_MAX_STEPS`，统一使用 `BURUNNER_MAX_STEPS`
- 通知工厂从静态注册表改为 `importlib.metadata` 动态插件发现
- `progress.py` 移除不必要的 `threading.Lock`（asyncio 单线程无需线程锁）
- 执行结果判定逻辑优化为 5 级优先级判定链
- `NotifyPayload` 增加 `incomplete` 字段，统计行显示未完成用例数

### Fixed

- 修复 Mako 模板 `${...}` 表达式存在的任意代码执行安全漏洞
- 修复 browser-use 日志在非 verbose 模式下仍然输出大量信息的问题
- 修复浏览器会话在异常时可能泄露的资源管理问题（改用 async context manager）

## [0.1.0] - 2026-05-30

### Added

- 基于 browser-use 的自然语言浏览器测试框架
- 支持多 LLM provider（OpenAI/Azure/Anthropic/Google/DeepSeek/Ollama/Grok/Mistral/阿里云/ModelScope/MoonShot/SiliconFlow/IBM/Unbound）
- 支持多浏览器类型（Chromium/Chrome/Chrome Beta/Chrome Dev/Chrome Canary/Edge/Edge Beta/Edge Dev/Edge Canary）
- 预设（presets）继承机制，共享公共前置步骤
- 预设 Cookie 注入，支持免登录测试
- 参数化变量与函数调用（`${var}` / `${func()}`）
  - 内置函数：`today()`, `now()`, `now_iso()`, `uuid()`, `random_int()`
- 数据驱动测试
  - CSV 数据源
  - JSON 数据源
  - YAML 数据源
  - 内联数据
- 多环境配置（environments）
  - 环境变量自动注入（`${env.VAR}` / `${env.current.VAR}`）
  - 环境级 config 和 cookies 配置
- Worker Pool 并发执行机制
  - 渐进启动，避免资源尖峰
  - 单用例超时控制（`--case-timeout`）
  - 自动重试机制（`--retry`）
  - 结果按原始顺序排列
- 测试完成通知
  - 企业微信 Webhook（Markdown 格式）
  - 飞书消息卡片
  - 钉钉 Markdown 通知
- Allure 报告集成
  - 用例级 step 记录
  - Token 用量统计
  - 失败截图附件
  - Agent 输出文本附件
  - 环境信息记录
- 实时进度显示（ProgressTracker）
  - 并行度显示
  - 动态进度条
  - 可选关闭（`--no-progress`）
- 标签（tags）过滤系统
  - 支持多标签 OR 关系
  - 与名称过滤组合使用
  - 不区分大小写
- 分层异常体系（exceptions.py）
  - ConfigurationError
  - BrowserError
  - LLMError
  - TransientError
  - BurunnerError
- CLI 命令
  - `burunner run` - 执行测试
  - `burunner validate` - 校验 YAML
  - `burunner version` - 显示版本
- src 模式项目结构
- MIT 许可证
- GitHub Actions CI/CD
  - 自动化测试（Python 3.11/3.12/3.13）
  - 代码质量检查
  - PyPI 可信发布者自动发布
  - TestPyPI 测试发布

### Changed

- 环境变量统一命名规范（`BURUNNER_LLM_*` 前缀）
- 配置合并逻辑采用元数据驱动
- notifier 采用注册表模式
- reporter 采用注册表模式
- datasource 采用模板方法模式

### Fixed

- 用例继承时数据驱动字段透传
- 变量解析支持点号语法（`data.field`）
- Python 3.10+ 类型注解兼容性

---

## 版本发布指南

### 发布新版本

1. 更新此文件，将 `[Unreleased]` 改为新版本号
2. 更新 `pyproject.toml` 中的版本号
3. 提交更改并创建 Git Tag
4. 创建 GitHub Release 触发自动发布

### 版本格式

`[版本号] - 日期`

### 变更类型

- **Added** - 新增功能
- **Changed** - 现有功能变更
- **Deprecated** - 即将废弃的功能
- **Removed** - 移除的功能
- **Fixed** - Bug 修复
- **Security** - 安全相关修复
