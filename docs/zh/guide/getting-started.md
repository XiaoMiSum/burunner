# 快速开始

30 秒体验 burunner —— 用自然语言编写浏览器端到端测试。

## 安装

```bash
pip install burunner
python -m playwright install chromium
```

## 配置

创建 `.env` 文件，填入你的 LLM 配置：

```bash
BURUNNER_LLM_PROVIDER=openai
BURUNNER_LLM_MODEL=gpt-4o
BURUNNER_LLM_API_KEY=sk-your-api-key
```

## 编写第一个用例

创建 `my_first_test.yaml`：

```yaml
- name: 百度搜索验证
  steps:
    - 访问 https://www.baidu.com
    - 在搜索框输入 "burunner"
    - 点击 "百度一下" 按钮
    - 验证搜索结果页面正确加载
```

## 运行

```bash
burunner run my_first_test.yaml
```

## 预期输出

```
[PASS]  百度搜索验证                       elapsed=15.23s  tokens(in/out/total)=1580/525/2105

=================================================================
Total: 1  Passed: 1  Failed: 0  Error:  0  Incomplete: 0
Total elapsed: 15.23s
Total tokens: in=1580  out=525  total=2105
Allure results: ./allure-results  (run: allure serve ./allure-results)
=================================================================
```

## 下一步

- [安装指南](./installation.md) — 完整安装步骤与可选依赖
- [配置说明](./configuration.md) — 环境变量与优先级
- [编写用例](./writing-cases.md) — YAML 用例格式详解
