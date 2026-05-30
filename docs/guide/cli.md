# CLI Reference

## Command Format

```bash
burunner run PATH [PATH ...]
```

Run one or more YAML test files. Multiple file paths or glob patterns are accepted.

## Options

| Flag                        | Short | Type    | Default           | Description                                    |
| --------------------------- | ----- | ------- | ----------------- | ---------------------------------------------- |
| `--filter TEXT`             | `-k`  | string  | —                 | Regex filter on case name                      |
| `--tags TEXT`               | `-t`  | string  | —                 | Tag filter (comma-separated, OR logic)         |
| `--parallel INTEGER`        | `-p`  | integer | `1`               | Number of parallel workers                     |
| `--llm TEXT`                |       | choice  | from `.env`       | LLM provider name                              |
| `--model TEXT`              |       | string  | from `.env`       | Model identifier                               |
| `--temperature FLOAT`       |       | float   | `0.0`             | Sampling temperature                           |
| `--base-url TEXT`           |       | string  | —                 | Custom LLM API endpoint                        |
| `--api-key TEXT`            |       | string  | —                 | LLM API key (overrides env var)                |
| `--headless` / `--headed`   |       | flag    | `--headless`      | Browser visibility mode                        |
| `--browser CHANNEL`         |       | choice  | `chromium`        | Browser channel                                |
| `--max-steps INTEGER`       |       | integer | `30`              | Max agent steps per case                       |
| `--case-timeout SECONDS`    |       | integer | `0` (no limit)    | Per-case timeout in seconds                    |
| `--retry COUNT`             |       | integer | `0`               | Auto-retry count for errored cases             |
| `--results-dir PATH`        |       | path    | `./allure-results` | Allure results output directory               |
| `--keep-browser-open`       |       | flag    | off               | Keep browser open after case (debug)           |
| `--no-vision`               |       | flag    | off               | Disable `use_vision` capability                |
| `--no-progress`             |       | flag    | off               | Disable real-time progress display             |
| `--env TEXT`                | `-e`  | string  | —                 | Activate a named environment from YAML         |
| `--verbose`                 | `-v`  | flag    | off               | Enable verbose logging                         |

### LLM Provider Choices

`openai`, `azure_openai`, `anthropic`, `google`, `deepseek`, `ollama`, `grok`, `mistral`, `alibaba`, `modelscope`, `moonshot`, `siliconflow`, `ibm`, `unbound`

### Browser Channel Choices

`chromium`, `chrome`, `chrome-beta`, `chrome-dev`, `chrome-canary`, `msedge`, `msedge-beta`, `msedge-dev`, `msedge-canary`

## Usage Examples

### Minimal Run

```bash
burunner run tests/smoke.yaml
```

### Specify LLM Provider and Model

```bash
burunner run tests/*.yaml --llm openai --model gpt-4o --api-key sk-xxx
```

### Parallel Execution

```bash
burunner run tests/*.yaml -p 4
```

### Filter by Name

```bash
burunner run tests/*.yaml -k "login|register"
```

### Filter by Tags

```bash
burunner run tests/*.yaml -t "smoke,p1"
```

### Combine Name and Tag Filters

```bash
burunner run tests/*.yaml -k "checkout" -t "regression"
```

### Specify Environment

```bash
burunner run tests/*.yaml --env staging
```

### Headed Mode with Timeout and Retry

```bash
burunner run tests/flaky.yaml --headed --case-timeout 120 --retry 2
```

### Use a Different Browser

```bash
burunner run tests/*.yaml --browser msedge
```

### Custom Results Directory

```bash
burunner run tests/*.yaml --results-dir ./reports/allure-results
```

### Full Example

```bash
burunner run tests/*.yaml \
    --llm openai --model gpt-4o \
    --browser chrome \
    -p 2 \
    -k "checkout" \
    -t "smoke" \
    --headed \
    --max-steps 40 \
    --case-timeout 120 \
    --retry 2 \
    --env staging \
    --results-dir ./allure-results
```

## Other Commands

### Validate

Parse YAML files without executing:

```bash
burunner validate tests/*.yaml
```

Output:

```
OK: 5 cases
  - Login test  (3 steps)  source=tests/auth.yaml
  - Search feature  (4 steps)  source=tests/search.yaml
  ...
```

### Version

```bash
burunner version
```

## Exit Codes

| Code | Meaning                                   |
| ---- | ----------------------------------------- |
| `0`  | All test cases passed                     |
| `1`  | One or more cases failed or errored       |
| `2`  | Configuration error (invalid YAML, etc.)  |
| `130`| Interrupted by user (Ctrl+C)              |

## Output Format

When running tests, burunner displays:

### Header Line

```
Provider=openai  Model=gpt-4o  Browser=chromium  Parallel=2  Headless=True  Timeout=∞s  Retry=0  Env=default  Cases=5
```

### Per-Case Progress

```
[1/5] Login test ... PASS (12.34s, tokens: 1801)
[2/5] Search feature ... FAIL (20.11s, tokens: 3090)
      Screenshot: allure-results/screenshots/...
[3/5] Register flow ... ERROR (5.02s, tokens: 450)
```

### Summary

```
=================================================================
Total: 5  Passed: 3  Failed: 1  Error:  1
Total elapsed: 45.67s
Total tokens: in=5200  out=2100  total=7300
Allure results: ./allure-results  (run: allure serve ./allure-results)
=================================================================
```
