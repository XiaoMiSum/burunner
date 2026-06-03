# Allure Reporting

burunner outputs test results in the standard [Allure](https://allurereport.org/) format. The framework writes raw JSON results; the HTML report is generated separately using the Allure CLI.

## Results Directory

By default, results are written to `./allure-results/`. Customize with `--results-dir`:

```bash
burunner run tests/*.yaml --results-dir ./my-results
```

The directory contains:
- `*-result.json` — One per test case with status, timing, and parameters
- `*-attachment.txt` — Agent output text and traceback
- `*-attachment.png` — Failure screenshots
- `screenshots/` — Named screenshot files
- `environment.properties` — Runtime environment metadata

## Report Contents

The Allure report includes:

| Section            | Details                                                   |
| ------------------ | --------------------------------------------------------- |
| Overview           | Pass/fail/error counts, overall duration                  |
| Per-case details   | Execution time, LLM provider, model, token usage          |
| Step-level status  | Independent status (PASSED/FAILED/INCOMPLETE), duration, and errors per step |
| Token metrics      | Input tokens, output tokens, total tokens per case        |
| Screenshots        | Automatic failure screenshots (when `use_vision` enabled) |
| Attachments        | Agent's final output text, error tracebacks               |
| Suite view         | Cases grouped by source YAML file                         |
| Tag view           | Cases grouped by tags                                     |
| Environment info   | burunner version, environment name, LLM provider/model, browser type |

## Step-Level Status Tracking

burunner tracks the execution status of each individual test step within a case. In the Allure report, each step is displayed with:

- **Independent status** — PASSED, FAILED, or INCOMPLETE per step
- **Precise timing** — Exact duration for each step
- **Error localization** — When a case fails, you can pinpoint exactly which step failed
- **Action details** — Browser actions performed during the step
- **URL tracking** — The page URL at each step

This gives you fine-grained visibility into test execution, making it easy to identify which specific step caused a failure without digging through logs.

### How It Works

The framework maps Agent iterations back to your user-defined test steps using the Agent's `current_plan_item` field. Each iteration is grouped under the corresponding step, and the results are aggregated into per-step outcomes.

> **Note**: If `current_plan_item` mapping is unavailable (e.g., older browser-use versions), iterations are distributed evenly across steps as a fallback. The feature degrades gracefully without affecting test execution.

## Installing Allure CLI

### macOS

```bash
brew install allure
```

### Linux

```bash
# Via npm
npm install -g allure-commandline

# Or download from GitHub releases
# https://github.com/allure-framework/allure2/releases
```

### Windows

```bash
scoop install allure
```

### Verify Installation

```bash
allure --version
```

## Preview Report

Launch a temporary web server to view results:

```bash
allure serve ./allure-results
```

This opens a browser with the interactive HTML report. The server stops when you press Ctrl+C.

## Generate Static Site

Generate a self-contained HTML report directory:

```bash
allure generate ./allure-results -o ./allure-report --clean
```

Then open directly:

```bash
open allure-report/index.html        # macOS
xdg-open allure-report/index.html    # Linux
start allure-report/index.html       # Windows
```

The `--clean` flag removes any previous report in the output directory before generating.

## CI Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install burunner
          python -m playwright install chromium

      - name: Run tests
        env:
          BURUNNER_LLM_PROVIDER: openai
          BURUNNER_LLM_MODEL: gpt-4o
          BURUNNER_LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
        run: |
          burunner run tests/*.yaml --headless || EXIT=$?
          exit ${EXIT:-0}

      - name: Generate Allure report
        if: always()
        run: |
          npm install -g allure-commandline
          allure generate ./allure-results -o ./allure-report --clean

      - name: Upload report artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: allure-report
          path: allure-report/
```

### Key CI Patterns

```bash
# Run tests, capture exit code, generate report, then exit with original code
burunner run tests/*.yaml --headless || EXIT=$?
allure generate ./allure-results -o ./allure-report --clean
exit ${EXIT:-0}
```

This ensures the report is always generated, even when tests fail.
