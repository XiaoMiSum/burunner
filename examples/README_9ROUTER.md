# burunner 示例 - 使用 9router 配置 LLM

本示例演示如何配置 burunner 通过 [9router](https://github.com/decolua/9router) 调用大语言模型执行浏览器自动化测试。

## 什么是 9router?

9router 是一个开源的 AI 路由器,提供以下功能:

- 🔄 **智能路由** - 统一多个 AI 提供商的接口
- 💰 **节省成本** - 自动 fallback 到免费/低价模型
- 🔗 **OpenAI 兼容** - 提供标准 OpenAI API 接口
- 📊 **配额管理** - 跟踪和管理 API 使用量

## 前置条件

### 1. 安装 9router

```bash
npm install -g 9router
```

### 2. 启动 9router

```bash
9router
```

启动后访问 http://localhost:20128 打开管理面板。

### 3. 配置 AI 提供商

在 9router 管理面板中:

1. 进入 **Providers** 页面
2. 点击 **Add OpenAI Compatible** (或添加其他提供商)
3. 填写配置信息:
   - **Name**: 自定义名称 (如 `OpenCode Free`)
   - **Base URL**: 提供商的 API 地址
   - **API Key**: 你的 API 密钥
   - **Models**: 配置可用的模型

示例配置:
```
Name: OpenCode Free
Base URL: https://your-provider-api.com/v1
API Key: sk-your-api-key
Model: oc/mimo-v2.5-free
```

## 配置 burunner

### 方式一: 使用 `.env` 文件 (推荐)

在项目根目录创建或编辑 `.env` 文件:

```bash
# ===== LLM 配置 (通过 9router) =====
BURUNNER_LLM_PROVIDER=openai
BURUNNER_LLM_MODEL=oc/mimo-v2.5-free
BURUNNER_LLM_BASE_URL=http://localhost:20128/v1
BURUNNER_LLM_API_KEY=sk-your-api-key-here
BURUNNER_LLM_TEMPERATURE=0.0

# ===== 浏览器配置 =====
BURUNNER_HEADLESS=true
BURUNNER_BROWSER_CHANNEL=msedge  # 或 chromium/chrome 等
BURUNNER_PARALLEL=1
BURUNNER_MAX_STEPS=30
```

**关键字段说明**:
- `BURUNNER_LLM_PROVIDER`: 必须设置为 `openai` (9router 提供 OpenAI 兼容接口)
- `BURUNNER_LLM_MODEL`: 填写你在 9router 中配置的模型名称
- `BURUNNER_LLM_BASE_URL`: 指向本地 9router 服务
- `BURUNNER_LLM_API_KEY`: 填写 9router 中配置的 API Key

### 方式二: 使用 CLI 参数

```bash
burunner run examples/example.yaml \
  --llm openai \
  --model oc/mimo-v2.5-free \
  --base-url http://localhost:20128/v1 \
  --api-key sk-your-api-key
```

### 方式三: 在 YAML 中配置

编辑 `example.yaml`:

```yaml
config:
  llm_provider: openai
  llm_model: oc/mimo-v2.5-free
  llm_base_url: http://localhost:20128/v1
  llm_api_key: sk-your-api-key
  max_steps: 30
  headless: true
```

## 优先级说明

配置优先级从高到低:

1. **CLI 参数** (`--llm`, `--model` 等)
2. **YAML 配置** (`config` 段)
3. **环境变量** (`.env` 文件)
4. **默认值**

## 运行测试

确保 9router 正在运行后:

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行示例测试
burunner run examples/example.yaml
```

## 验证连接

运行测试时,观察输出:

✅ **连接成功**的标志:
```
Provider=openai  Model=oc/mimo-v2.5-free  Browser=msedge
INFO [Agent] Starting a browser-use agent with version 0.12.9, 
           with provider=openai and model=oc/mimo-v2.5-free
INFO [Agent] 📍 Step 1:
INFO [Agent]   ▶️ navigate: url: https://www.baidu.com
```

❌ **连接失败**的标志:
```
WARNING [Agent] ❌ Result failed 1/6 times: 
Error code: 404 - {'error': {'message': 'No active credentials for provider: openai'}}
```

## 常见问题

### 1. 错误: "No active credentials for provider: openai"

**原因**: 9router 中没有配置或激活对应的 provider

**解决**: 
- 检查 9router 管理面板 http://localhost:20128
- 确认 provider 已正确配置且状态为活跃
- 确认 YAML/环境变量中的模型名与 9router 中配置的一致

### 2. 错误: "model_not_found"

**原因**: 模型名称不匹配或未在 9router 中配置

**解决**:
- 检查 `BURUNNER_LLM_MODEL` 或 YAML 中的 `llm_model`
- 确保与 9router 中配置的模型名称**完全一致**

### 3. 模型输出格式错误

某些免费模型可能无法严格遵循 browser-use 的 JSON schema 要求,导致:

```
90 validation errors for AgentOutput
action.0.DoneActionModel.done - Field required
```

**解决**:
- 尝试使用更强大的模型 (如 GPT-4, Claude 等)
- 在 9router 中配置多个 provider 实现自动 fallback
- 降低测试复杂度

### 4. 9router 未启动

**症状**: 连接超时或拒绝

**解决**:
```bash
# 检查 9router 是否运行
curl http://localhost:20128/v1/models

# 重新启动
9router
```

## 多 Provider 配置示例

在 9router 中可以配置多个 provider 实现智能路由:

```
Provider 1: OpenAI (GPT-4o) - 主要使用
Provider 2: Claude (Claude 3.5) - 备用
Provider 3: OpenCode Free (mimo-v2.5-free) - 免费 fallback
```

9router 会自动在主 provider 失败时切换到备用 provider。

## 推荐配置

### 开发/测试环境

```bash
BURUNNER_LLM_MODEL=oc/mimo-v2.5-free  # 免费模型
BURUNNER_PARALLEL=1
BURUNNER_MAX_STEPS=30
BURUNNER_HEADLESS=false  # 可视化调试
```

### 生产环境

```bash
BURUNNER_LLM_MODEL=gpt-4o  # 稳定模型
BURUNNER_PARALLEL=3
BURUNNER_MAX_STEPS=50
BURUNNER_HEADLESS=true
```

## 参考资料

- [9router 官方文档](https://github.com/decolua/9router)
- [9router 官网](https://9router.com/)
- [burunner 使用指南](../README.md)
