# Contributing Guide

Thank you for your interest in burunner! This document explains how to set up the development environment and contribute to the project.

---

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Git
- A Chromium-based browser installed (Chrome / Edge optional)

### Initialization Steps

```bash
# 1. Clone the repository
git clone https://github.com/<org>/browser-use-runner.git
cd browser-use-runner

# 2. Create a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies (editable mode)
pip install -r requirements.txt
pip install -e .

# 4. Install Playwright browser kernel
python -m playwright install chromium

# 5. Copy environment variable template
cp .env.example .env
# Fill in BURUNNER_LLM_PROVIDER / BURUNNER_LLM_API_KEY as needed
```

### Optional LLM Dependencies

```bash
pip install anthropic          # Claude
pip install google-generativeai # Gemini
pip install ollama             # Ollama
```

---

## Code Structure

```
src/burunner/
├── cli.py              # CLI entry point (Click framework)
├── config.py           # Runtime config (dataclass + .env loading)
├── exceptions.py       # Layered exception hierarchy
├── llm/
│   └── provider.py     # Multi-Provider factory (Registry + Strategy pattern)
├── notifier/           # Test completion notifications
│   ├── base.py         # Notifier base class + payload definition
│   ├── wecom.py        # WeCom (Enterprise WeChat)
│   ├── feishu.py       # Feishu (Lark)
│   ├── dingtalk.py     # DingTalk
│   └── factory.py      # Notifier factory
├── parser/             # YAML parsing
│   ├── models.py       # Data models (TestCase, TestSuite, etc.)
│   ├── datasource.py   # Data source loading (CSV/JSON/YAML)
│   ├── variables.py    # Variable substitution engine
│   └── yaml_parser.py  # Main parser logic
├── runner/             # Execution engine
│   ├── executor.py     # Single case executor
│   ├── orchestrator.py # Worker Pool concurrent scheduling
│   ├── result.py       # Result data structures
│   └── progress.py     # Progress tracking
├── browser/
│   └── session.py      # Playwright browser session management
├── reporter/           # Report output (Console + Allure)
└── utils/              # Utilities (logging/screenshots/token counting)
```

---

## Branch Strategy

| Branch | Purpose |
| --- | --- |
| `main` | Stable mainline, all merges require PR |
| `feature/*` | New feature development |
| `fix/*` | Bug fixes |
| `refactor/*` | Refactoring improvements |

**Workflow**:

1. Create a feature/fix branch from `main`
2. Develop locally and commit (keep commits atomic)
3. Push and open a Pull Request
4. Squash merge to `main` after review approval

---

## Code Conventions

### Type Annotations

All public functions and methods must include complete type annotations:

```python
def get_llm_model(
    provider: str,
    *,
    model_name: str,
    temperature: float = 0.0,
    base_url: str | None = None,
) -> Any:
    ...
```

### Docstrings

Modules, classes, and public functions require docstrings:

```python
"""Module description."""

class RunnerConfig:
    """Global configuration for a single run. CLI params > yaml config > .env > defaults."""
    ...
```

### Exception Handling

- Custom exceptions inherit from `BurunnerError`
- Configuration errors use `ConfigurationError`
- Execution errors use `ExecutionError` and its subclasses
- Non-recoverable errors (e.g., invalid config) should terminate immediately
- Retryable errors (e.g., network timeout) use `TransientError`

### Naming Conventions

- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

---

## PR Submission Guidelines

### Commit Format

```
<type>(<scope>): <subject>

<body>
```

**Allowed types**:

- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Refactoring
- `docs`: Documentation update
- `test`: Test-related changes
- `chore`: Build/toolchain

**Example**:

```
feat(notifier): add Slack notification channel

- Implement SlackNotifier extending BaseNotifier
- Register in factory.py
- Add webhook URL config support
```

### PR Description Template

- **What**: What changes were made
- **Why**: Why the change is needed
- **How**: How to verify

---

## Local Testing

### Validate YAML Parsing

```bash
burunner validate examples/example.yaml
```

### Run Test Cases

```bash
# Basic execution
burunner run examples/example.yaml --headed

# Specify provider and model
burunner run examples/example.yaml --llm openai --model gpt-4o

# Filter by name
burunner run examples/example.yaml -k "search"

# Filter by tags
burunner run examples/example.yaml -t "smoke"
```

### View Allure Reports

```bash
allure serve ./allure-results
```

---

## Important Notes

- Ensure `.env` is never committed to the repository (excluded via `.gitignore`)
- New LLM Providers must be visible in the `SUPPORTED_PROVIDERS` tuple
- New notification channels must be registered in `NOTIFIER_REGISTRY` and `SUPPORTED_CHANNELS`
- Maintain backward compatibility: YAML case format changes must support older formats
