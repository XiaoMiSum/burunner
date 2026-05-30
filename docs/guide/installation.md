# Installation

## System Requirements

- **Python** >= 3.11
- **OS**: macOS, Linux, or Windows
- **Browser**: Chromium-based browsers (Chromium, Chrome, or Edge)

## Install via PyPI

The simplest way to install burunner:

```bash
pip install burunner
```

Then install the browser driver:

```bash
python -m playwright install chromium
```

## Install from Source

```bash
git clone https://github.com/user/browser-use-runner.git
cd browser-use-runner

# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Install in development (editable) mode
pip install -e .

# Install browser driver
python -m playwright install chromium
```

## Browser Driver

burunner uses Playwright under the hood. The default browser is **Chromium**:

```bash
python -m playwright install chromium
```

To use Chrome or Edge, ensure the browser is already installed on your system. No additional Playwright install is needed — burunner connects to the locally installed browser via the `--browser` flag or `BURUNNER_BROWSER_CHANNEL` environment variable.

Supported browser channels:

| Channel           | Description                  |
| ----------------- | ---------------------------- |
| `chromium`        | Playwright bundled Chromium  |
| `chrome`          | Google Chrome (stable)       |
| `chrome-beta`     | Google Chrome Beta           |
| `chrome-dev`      | Google Chrome Dev            |
| `chrome-canary`   | Google Chrome Canary         |
| `msedge`          | Microsoft Edge (stable)      |
| `msedge-beta`     | Microsoft Edge Beta          |
| `msedge-dev`      | Microsoft Edge Dev           |
| `msedge-canary`   | Microsoft Edge Canary        |

> **Note**: Only Chromium-based browsers are supported. Firefox and Safari are not supported by browser-use.

## Optional LLM Dependencies

By default, burunner ships with OpenAI support. Install additional provider packages as needed:

```bash
# Anthropic (Claude)
pip install anthropic

# Google (Gemini)
pip install google-generativeai

# Ollama (local models)
pip install ollama
```

## Verify Installation

```bash
burunner version
```

This prints the installed version number. To verify the full pipeline works:

```bash
burunner validate examples/example.yaml
```

This parses the YAML file and reports the number of test cases found without executing them.
