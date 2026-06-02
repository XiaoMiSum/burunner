# 配置

burunner 支持多种配置方式，按优先级从高到低排列：

1. CLI 参数（`--llm`、`--model` 等）
2. 环境变量（`.env` 文件）
3. YAML 顶层 `config` 字段
4. 框架默认值

## 环境变量配置

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

### 完整环境变量表

#### LLM 配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `BURUNNER_LLM_PROVIDER` | LLM provider 名称 | `openai` |
| `BURUNNER_LLM_MODEL` | 模型名称 | `gpt-4o` |
| `BURUNNER_LLM_TEMPERATURE` | 采样温度 | `0.0` |
| `BURUNNER_LLM_API_KEY` | 统一 API Key | — |
| `BURUNNER_LLM_BASE_URL` | 自定义 API 端点 | — |

#### Provider 专用配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `BURUNNER_AZURE_API_VERSION` | Azure OpenAI API 版本 | `2025-01-01-preview` |
| `BURUNNER_IBM_PROJECT_ID` | IBM watsonx 项目 ID | — |

#### 执行配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `BURUNNER_HEADLESS` | 无头模式 | `true` |
| `BURUNNER_BROWSER_CHANNEL` | 浏览器类型 | `chromium` |
| `BURUNNER_PARALLEL` | 并发度 | `1` |
| `BURUNNER_MAX_STEPS` | 单用例最大步数，`0` 表示自动计算（步骤数×20，最少 20） | `0` |
| `BURUNNER_CASE_TIMEOUT` | 单用例超时（秒），`0` 不限 | `0` |
| `BURUNNER_RETRY_COUNT` | 重试次数（仅对 INCOMPLETE 和 ERROR 生效，FAILED 不重试） | `0` |
| `BURUNNER_RETRY_DELAY` | 重试间隔（秒） | `2.0` |
| `BURUNNER_ENV` | 默认运行环境名 | — |
| `BURUNNER_BROWSER_USE_LOG` | 打印 browser-use 执行日志 | `false` |

#### 通知配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `BURUNNER_NOTIFY_CHANNEL` | 通知渠道：`wecom` / `feishu` / `dingtalk` | — |
| `BURUNNER_NOTIFY_WEBHOOK` | 通知 Webhook URL | — |

## 支持的 Provider

| Provider | `BURUNNER_LLM_PROVIDER` 值 |
| --- | --- |
| OpenAI | `openai` |
| Azure OpenAI | `azure_openai` |
| Anthropic | `anthropic` |
| Google Gemini | `google` |
| DeepSeek | `deepseek` |
| Ollama | `ollama` |
| Grok | `grok` |
| Mistral | `mistral` |
| 阿里云 DashScope | `alibaba` |
| ModelScope | `modelscope` |
| MoonShot | `moonshot` |
| SiliconFlow | `siliconflow` |
| IBM watsonx | `ibm` |
| Unbound | `unbound` |

## YAML 顶层 config 覆盖

在 YAML 文件中可通过顶层 `config` 字段覆盖运行时配置：

```yaml
config:
  llm_provider: openai
  llm_model: gpt-4o
  headless: true
  parallel: 2
  max_steps: 0
  case_timeout: 120
  retry_count: 1
  browser_use_log: true

cases:
  - name: 示例用例
    steps:
      - 访问 https://example.com
```

### config 支持的字段

| 字段 | 对应环境变量 | 说明 |
| --- | --- | --- |
| `llm_provider` | `BURUNNER_LLM_PROVIDER` | LLM provider 名称 |
| `llm_model` | `BURUNNER_LLM_MODEL` | 模型名称 |
| `llm_temperature` | `BURUNNER_LLM_TEMPERATURE` | 采样温度 |
| `llm_base_url` | `BURUNNER_LLM_BASE_URL` | 自定义 API 端点 |
| `llm_api_key` | `BURUNNER_LLM_API_KEY` | API Key |
| `headless` | `BURUNNER_HEADLESS` | 无头模式 |
| `browser_channel` | `BURUNNER_BROWSER_CHANNEL` | 浏览器类型 |
| `parallel` | `BURUNNER_PARALLEL` | 并行度 |
| `max_steps` | `BURUNNER_MAX_STEPS` | 最大步数（0=自动计算） |
| `case_timeout` | `BURUNNER_CASE_TIMEOUT` | 单用例超时 |
| `retry_count` | `BURUNNER_RETRY_COUNT` | 重试次数（仅 INCOMPLETE/ERROR） |
| `retry_delay` | `BURUNNER_RETRY_DELAY` | 重试间隔 |
| `browser_use_log` | `BURUNNER_BROWSER_USE_LOG` | browser-use 日志开关 |

## 优先级示例

假设存在以下配置：

- `.env`: `BURUNNER_LLM_MODEL=gpt-4o`
- YAML `config`: `llm_model: gpt-4o-mini`
- CLI: `--model gpt-4-turbo`

最终生效的模型为 `gpt-4-turbo`（CLI 最高优先级）。
