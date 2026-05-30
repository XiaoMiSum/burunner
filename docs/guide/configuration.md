# Configuration

## Quick Setup

```bash
cp .env.example .env
# Edit .env with your preferred settings
```

## Environment Variables

| Variable                    | Description                              | Default       |
| --------------------------- | ---------------------------------------- | ------------- |
| `BURUNNER_LLM_PROVIDER`    | LLM provider name                        | `openai`      |
| `BURUNNER_LLM_MODEL`       | Model identifier                         | `gpt-4o`      |
| `BURUNNER_LLM_TEMPERATURE` | Sampling temperature                     | `0.0`         |
| `BURUNNER_LLM_API_KEY`     | API key for the LLM provider             | —             |
| `BURUNNER_LLM_BASE_URL`    | Custom API endpoint (optional)           | —             |
| `BURUNNER_AZURE_API_VERSION` | Azure OpenAI API version (Azure only)  | `2025-01-01-preview` |
| `BURUNNER_IBM_PROJECT_ID`  | IBM watsonx project ID (IBM only)        | —             |
| `BURUNNER_HEADLESS`        | Run browser in headless mode             | `true`        |
| `BURUNNER_BROWSER_CHANNEL` | Browser type                             | `chromium`    |
| `BURUNNER_PARALLEL`        | Number of parallel workers               | `1`           |
| `BURUNNER_MAX_STEPS`       | Max agent steps per case                 | `30`          |
| `BURUNNER_CASE_TIMEOUT`    | Per-case timeout in seconds (0=no limit) | `0`           |
| `BURUNNER_RETRY_COUNT`     | Retry count for errored cases            | `0`           |
| `BURUNNER_RETRY_DELAY`     | Delay between retries (seconds)          | `2.0`         |
| `BURUNNER_ENV`             | Default environment name                 | —             |
| `BURUNNER_NOTIFY_CHANNEL`  | Notification channel (`wecom`/`feishu`/`dingtalk`) | — |
| `BURUNNER_NOTIFY_WEBHOOK`  | Webhook URL for notifications            | —             |

## Priority Order

Configuration values are resolved in the following order (highest priority first):

```
CLI arguments  >  Environment variables (.env)  >  YAML config section  >  Built-in defaults
```

1. **CLI arguments** (`--llm`, `--model`, `--api-key`, etc.) — highest priority
2. **Environment variables** (from `.env` file or system environment)
3. **YAML `config:` section** — defined in the test file
4. **Built-in defaults** — fallback values

## YAML Config Override

You can override runtime configuration directly in your YAML test file using a top-level `config:` section:

```yaml
config:
  llm_provider: openai
  llm_model: gpt-4o
  parallel: 2
  max_steps: 40
  headless: true
  browser_channel: chrome

cases:
  - name: My test case
    steps:
      - Navigate to https://example.com
```

### Supported YAML Config Fields

| Field              | Type    | Description                    |
| ------------------ | ------- | ------------------------------ |
| `llm_provider`     | string  | LLM provider name              |
| `llm_model`        | string  | Model identifier               |
| `llm_temperature`  | float   | Sampling temperature           |
| `llm_base_url`     | string  | Custom API endpoint            |
| `llm_api_key`      | string  | API key                        |
| `headless`         | boolean | Headless mode                  |
| `browser_channel`  | string  | Browser type                   |
| `parallel`         | integer | Parallel workers               |
| `max_steps`        | integer | Max steps per case             |
| `case_timeout`     | integer | Timeout in seconds             |
| `retry_count`      | integer | Retry count                    |
| `cookies`          | list    | Global cookies to inject       |

## Supported LLM Providers

| Provider       | `BURUNNER_LLM_PROVIDER` value |
| -------------- | ----------------------------- |
| OpenAI         | `openai`                      |
| Azure OpenAI   | `azure_openai`                |
| Anthropic      | `anthropic`                   |
| Google Gemini  | `google`                      |
| DeepSeek       | `deepseek`                    |
| Ollama         | `ollama`                      |
| Grok (xAI)    | `grok`                        |
| Mistral        | `mistral`                     |
| Alibaba        | `alibaba`                     |
| ModelScope     | `modelscope`                  |
| MoonShot       | `moonshot`                    |
| SiliconFlow    | `siliconflow`                 |
| IBM watsonx    | `ibm`                         |
| Unbound        | `unbound`                     |
