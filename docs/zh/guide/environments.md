# 多环境配置

burunner 支持在同一 YAML 文件中定义多个环境配置，实现一套用例在不同环境（dev / staging / prod）下运行。

## 环境结构定义

在 YAML 顶层 `environments` 字段定义各环境：

```yaml
environments:
  dev:
    variables:
      base_url: "https://dev.example.com"
      username: "dev_user"
    config:
      headless: false
      max_steps: 50
    cookies:
      - name: env_token
        value: "dev-token-abc"
        domain: ".dev.example.com"

  staging:
    variables:
      base_url: "https://staging.example.com"
      username: "staging_user"
    config:
      headless: true
      max_steps: 40

  prod:
    variables:
      base_url: "https://www.example.com"
      username: "prod_user"
    config:
      headless: true
      max_steps: 30
```

## 环境配置项

每个环境可包含以下字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `variables` | object | 环境专属变量，覆盖顶层 `variables` |
| `config` | object | 环境专属运行配置，覆盖顶层 `config` |
| `cookies` | object[] | 环境专属 Cookie |

## 激活方式

### CLI 参数

```bash
burunner run tests.yaml --env dev
burunner run tests.yaml --env staging
burunner run tests.yaml -e prod
```

### 环境变量

```bash
export BURUNNER_ENV=dev
burunner run tests.yaml
```

CLI `--env` 参数优先于 `BURUNNER_ENV` 环境变量。

## 环境间互不继承

每个环境独立定义自己的 `variables`、`config` 和 `cookies`，**不会**从其他环境继承。

例如 `dev` 环境定义了 `headless: false`，而 `staging` 没有定义 `headless`，则 `staging` 使用全局默认值（`true`），不会继承 `dev` 的设置。

## 完整示例

```yaml
# 全局变量（未指定环境时使用）
variables:
  base_url: "https://example.com"
  app_name: "MyApp"

# 环境配置
environments:
  dev:
    variables:
      base_url: "https://dev.example.com"
      app_name: "MyApp-Dev"
    config:
      headless: false
      max_steps: 50
      parallel: 1
    cookies:
      - name: debug
        value: "true"
        domain: ".dev.example.com"

  staging:
    variables:
      base_url: "https://staging.example.com"
      app_name: "MyApp-Staging"
    config:
      headless: true
      max_steps: 40
      parallel: 2

  prod:
    variables:
      base_url: "https://www.example.com"
      app_name: "MyApp"
    config:
      headless: true
      max_steps: 30
      parallel: 4
      case_timeout: 120

# 测试用例
cases:
  - name: 首页访问
    steps:
      - 访问 ${base_url}
      - 验证页面标题包含 ${app_name}

  - name: 搜索功能
    steps:
      - 访问 ${base_url}/search
      - 在搜索框输入 "测试"
      - 验证搜索结果正常加载
```

运行：

```bash
# 使用 dev 环境：base_url=https://dev.example.com, headless=false
burunner run tests.yaml --env dev

# 使用 prod 环境：base_url=https://www.example.com, headless=true, parallel=4
burunner run tests.yaml --env prod

# 不指定环境：使用顶层 variables 默认值
burunner run tests.yaml
```
