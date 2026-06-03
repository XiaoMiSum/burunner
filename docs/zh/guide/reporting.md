# Allure 报告

burunner 以标准 [Allure](https://allurereport.org/) 格式输出测试结果，HTML 报告由 Allure CLI 独立生成。

## allure-results 目录

测试执行后，结果默认写入 `./allure-results/` 目录（可通过 `--results-dir` 修改），包含：

- `*-result.json` — 用例执行结果
- `*-attachment.txt` — Agent 输出文本附件
- `*-attachment.png` — 失败截图
- `screenshots/` — 截图文件
- `environment.properties` — 环境信息

## 报告内容

Allure 报告包含以下信息：

- 用例通过 / 失败 / 异常统计
- 每个用例的执行时间
- Provider、model 信息
- Input / Output / Total tokens 消耗
- 步骤级状态追踪（每个步骤独立的 PASSED/FAILED/INCOMPLETE 状态和精确耗时）
- 失败截图
- Agent 最终输出文本
- Traceback 附件（异常时）
- 按 source 文件聚合的 suite 视图
- Tag 标签视图
- 环境信息（burunner 版本、运行环境、LLM provider/model、浏览器类型等）

## 步骤级状态追踪

burunner 追踪每个测试步骤的独立执行状态。在 Allure 报告中，每个步骤包含：

- **独立状态** — 每个步骤独立的 PASSED / FAILED / INCOMPLETE 状态
- **精确耗时** — 每个步骤的精确执行时间
- **错误定位** — 用例失败时可精确定位到具体哪个步骤出错
- **动作详情** — 步骤中执行的浏览器操作
- **URL 追踪** — 每个步骤执行时的页面地址

通过步骤级追踪，你可以快速定位失败的具体步骤，无需翻阅大量日志。

### 工作原理

框架通过 Agent 的 `current_plan_item` 字段将 Agent 迭代映射回用户定义的测试步骤。每次迭代被归类到对应的步骤下，最终聚合为每个步骤的独立执行结果。

> **注意**：如果 `current_plan_item` 映射不可用（如较旧的 browser-use 版本），迭代将均匀分配到各步骤作为回退策略。该功能优雅降级，不影响测试执行。

## 安装 Allure CLI

### macOS

```bash
brew install allure
```

### Linux

```bash
# 通过 npm 安装
npm install -g allure-commandline

# 或下载二进制包
# 参考 https://allurereport.org/docs/install/
```

### Windows

```bash
scoop install allure
```

## 预览报告

一次性启动 Web 服务器预览报告：

```bash
allure serve ./allure-results
```

浏览器会自动打开报告页面。

## 生成静态站点

生成可部署的静态 HTML 报告：

```bash
allure generate ./allure-results -o ./allure-report --clean
open allure-report/index.html
```

`--clean` 会在生成前清空目标目录。

## CI 集成示例

### GitHub Actions

```yaml
- name: Run tests
  run: |
    burunner run tests/*.yaml --headless || EXIT=$?
    exit ${EXIT:-0}

- name: Generate Allure report
  if: always()
  run: |
    allure generate ./allure-results -o ./allure-report --clean

- name: Upload report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: allure-report
    path: allure-report/
```

### 通用 CI 脚本

```bash
#!/bin/bash
# 运行测试
burunner run tests/*.yaml --headless || EXIT=$?

# 生成报告
allure generate ./allure-results -o ./allure-report --clean

# 返回测试结果退出码
exit ${EXIT:-0}
```

## 自定义结果目录

```bash
burunner run tests.yaml --results-dir ./custom-results
allure serve ./custom-results
```
