# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

## [0.1.0] - 2024-XX-XX

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
