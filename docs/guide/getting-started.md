# Getting Started

Get up and running with burunner in 30 seconds.

## Quickstart

### 1. Install

```bash
pip install burunner
python -m playwright install chromium
```

### 2. Configure

```bash
export BURUNNER_LLM_PROVIDER=openai
export BURUNNER_LLM_MODEL=gpt-4o
export BURUNNER_LLM_API_KEY=sk-your-key
```

Or create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your LLM credentials
```

### 3. Write Your First Test Case

Create `my_first_test.yaml`:

```yaml
- name: Verify homepage title
  steps:
    - Navigate to https://example.com
    - Verify the page title contains "Example Domain"
```

### 4. Run

```bash
burunner run my_first_test.yaml
```

## Expected Output

```
Provider=openai  Model=gpt-4o  Browser=chromium  Parallel=1  Headless=True  Timeout=∞s  Retry=0  Env=default  Cases=1
[1/1] Verify homepage title ... PASS (8.52s, tokens: 1205)

=================================================================
Total: 1  Passed: 1  Failed: 0  Error:  0
Total elapsed: 8.52s
Total tokens: in=890  out=315  total=1205
Allure results: ./allure-results  (run: allure serve ./allure-results)
=================================================================
```

## What's Next

- [Installation](installation.md) — Full installation guide and optional dependencies
- [Configuration](configuration.md) — Environment variables and priority rules
- [Writing Test Cases](writing-cases.md) — YAML structure, tags, and verdict rules
- [CLI Reference](cli.md) — All command-line options
