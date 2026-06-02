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
| `--max-steps` | — | INTEGER | `0` | 单用例最大 Agent 步数（0=自动计算：步骤数×20，最少 20） |
| `--case-timeout` | — | SECONDS | `0` | 单用例超时（0=不限） |
| `--retry` | — | COUNT | `0` | 自动重试次数（仅对 INCOMPLETE 和 ERROR 生效，FAILED 不重试） |

### 输出与环境

| 选项 | 简写 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `--results-dir` | — | PATH | `./allure-results` | Allure 结果目录 |
| `--no-progress` | — | FLAG | — | 关闭实时进度显示 |
| `--env` | `-e` | TEXT | — | 运行环境名 |
| `--verbose` | `-v` | FLAG | — | 详细输出 |
| `--browser-use-log` | — | FLAG | — | 打印 browser-use 内部执行日志（默认关闭） |

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
| `1` | 存在 FAILED、ERROR 或 INCOMPLETE 用例 |

适用于 CI/CD 流程中判断测试是否通过。

## 输出格式

运行时控制台输出：

### 用例结果

```
[PASS]  登录功能                         elapsed=12.34s  tokens(in/out/total)=1200/601/1801
[PASS]  搜索功能                         elapsed=8.56s   tokens(in/out/total)=800/405/1205
[FAIL]  订单创建                         elapsed=20.11s  tokens(in/out/total)=2000/1090/3090  screenshot=allure-results/screenshots/...
[PASS]  个人信息                         elapsed=6.78s   tokens(in/out/total)=600/380/980
[PASS]  退出登录                         elapsed=5.12s   tokens(in/out/total)=500/256/756

=================================================================
Total: 5  Passed: 4  Failed: 1  Error:  0  Incomplete: 0
Total elapsed: 52.91s
Total tokens: in=5100  out=2732  total=7832
Allure results: ./allure-results  (run: allure serve ./allure-results)
=================================================================
```

每条用例输出：序号、名称、结果（PASS/FAIL/ERR/INC）、耗时、token 消耗。失败用例额外输出截图路径。
