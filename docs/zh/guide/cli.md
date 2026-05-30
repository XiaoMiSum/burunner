# CLI 参考

## 命令格式

```bash
burunner run PATH [PATH ...]
```

`PATH` 为 YAML 用例文件路径，支持多文件和 glob 通配符。

## 完整选项表

### 用例过滤

| 选项 | 简写 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `--filter` | `-k` | TEXT | — | 正则表达式过滤用例 name |
| `--tags` | `-t` | TEXT | — | 按标签过滤（逗号分隔，OR 关系） |

### LLM 配置

| 选项 | 简写 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `--llm` | — | TEXT | `openai` | Provider 名称 |
| `--model` | — | TEXT | `gpt-4o` | 模型名称 |
| `--temperature` | — | FLOAT | `0.0` | 采样温度 |
| `--base-url` | — | TEXT | — | 自定义 API 端点 |
| `--api-key` | — | TEXT | — | API Key |

### 浏览器配置

| 选项 | 简写 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `--headless` | — | FLAG | 默认启用 | 无头模式 |
| `--headed` | — | FLAG | — | 有头模式（可见浏览器） |
| `--browser` | — | TEXT | `chromium` | 浏览器类型 |
| `--keep-browser-open` | — | FLAG | — | 调试用，保持浏览器打开 |
| `--no-vision` | — | FLAG | — | 禁用 use_vision |

### 执行控制

| 选项 | 简写 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `--parallel` | `-p` | INTEGER | `1` | 并行度 |
| `--max-steps` | — | INTEGER | `30` | 单用例最大 Agent 步数 |
| `--case-timeout` | — | SECONDS | `0` | 单用例超时（0=不限） |
| `--retry` | — | COUNT | `0` | 异常用例自动重试次数 |

### 输出与环境

| 选项 | 简写 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `--results-dir` | — | PATH | `./allure-results` | Allure 结果目录 |
| `--no-progress` | — | FLAG | — | 关闭实时进度显示 |
| `--env` | `-e` | TEXT | — | 运行环境名 |
| `--verbose` | `-v` | FLAG | — | 详细输出 |

## 常用组合示例

### 最简运行

```bash
burunner run examples/example.yaml
```

### 指定 LLM 和模型

```bash
burunner run tests.yaml --llm openai --model gpt-4o --api-key sk-xxx
```

### 并行执行 + 有头模式

```bash
burunner run tests.yaml -p 4 --headed
```

### 按名称过滤

```bash
burunner run tests.yaml -k "登录"
```

### 按标签过滤

```bash
burunner run tests.yaml -t "smoke,p1"
```

### 标签 + 名称组合

```bash
burunner run tests.yaml -k "搜索" -t "p1"
```

### 指定环境运行

```bash
burunner run tests.yaml --env staging
```

### 超时 + 重试

```bash
burunner run tests.yaml --case-timeout 120 --retry 2
```

### 完整参数组合

```bash
burunner run tests/*.yaml \
    --llm openai --model gpt-4o \
    --browser chrome \
    -p 2 \
    -k "通道列表" \
    -t "p1" \
    --headed \
    --max-steps 40 \
    --case-timeout 120 \
    --retry 2 \
    --env dev \
    --results-dir ./allure-results
```

## 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 全部用例 PASSED |
| `1` | 存在 FAILED 或 ERROR 用例 |

适用于 CI/CD 流程中判断测试是否通过。

## 输出格式

运行时控制台输出：

```
Provider=openai  Model=gpt-4o  Browser=chromium  Parallel=2  Headless=True  Timeout=∞s  Retry=0  Env=default  Cases=5
[1/5] 登录功能 ... PASS (12.34s, tokens: 1801)
[2/5] 搜索功能 ... PASS (8.56s, tokens: 1205)
[3/5] 订单创建 ... FAIL (20.11s, tokens: 3090)
      截图: allure-results/screenshots/...
[4/5] 个人信息 ... PASS (6.78s, tokens: 980)
[5/5] 退出登录 ... PASS (5.12s, tokens: 756)

=================================================================
Total: 5  Passed: 4  Failed: 1  Error:  0
Total elapsed: 52.91s
Total tokens: in=5544  out=2288  total=7832
Allure results: ./allure-results  (run: allure serve ./allure-results)
=================================================================
```

每条用例输出：序号、名称、结果（PASS/FAIL/ERROR）、耗时、token 消耗。失败用例额外输出截图路径。
