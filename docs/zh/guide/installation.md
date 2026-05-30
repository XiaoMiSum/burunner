# 安装

## 系统要求

- Python >= 3.11
- 操作系统：macOS / Linux / Windows
- 网络连接（用于 LLM API 调用）

## 通过 PyPI 安装（推荐）

```bash
pip install burunner
```

安装完成后，需要安装浏览器内核：

```bash
python -m playwright install chromium
```

## 从源码安装

```bash
git clone https://github.com/user/browser-use-runner.git
cd browser-use-runner

# 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .

# 安装浏览器内核
python -m playwright install chromium
```

## 可选 LLM 依赖

burunner 默认支持 OpenAI，其他 provider 需按需安装额外依赖：

```bash
# Anthropic Claude
pip install anthropic

# Google Gemini
pip install google-generativeai

# Ollama（本地模型）
pip install ollama
```

## 浏览器支持

burunner 基于 Playwright，支持以下 Chromium 内核浏览器：

| 浏览器 | Channel 值 |
| --- | --- |
| Chromium（内置） | `chromium`（默认） |
| Google Chrome | `chrome` |
| Google Chrome Beta | `chrome-beta` |
| Google Chrome Dev | `chrome-dev` |
| Google Chrome Canary | `chrome-canary` |
| Microsoft Edge | `msedge` |
| Microsoft Edge Beta | `msedge-beta` |
| Microsoft Edge Dev | `msedge-dev` |
| Microsoft Edge Canary | `msedge-canary` |

> 注意：不支持 Firefox / Safari。使用 Chrome / Edge 需本地已安装对应浏览器。

## 验证安装

```bash
burunner --help
```

如能正常输出帮助信息，说明安装成功。
