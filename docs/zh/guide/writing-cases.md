# YAML 用例格式

## 基本结构

每个 YAML 文件包含一组测试用例。支持两种顶层格式：

### 列表格式

```yaml
- name: 用例 A
  steps:
    - 第一步
    - 第二步

- name: 用例 B
  steps:
    - 第一步
```

### cases 对象格式

```yaml
config:
  llm_provider: openai
  llm_model: gpt-4o

cases:
  - name: 用例 A
    steps:
      - 第一步
      - 第二步
```

`cases` 格式允许在同级定义 `config`、`presets`、`variables`、`environments` 等顶层字段。

## 用例字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 用例名称，同文件内唯一 |
| `description` | string | 否 | 简短描述 |
| `tags` | string[] | 否 | 标签，用于过滤 |
| `steps` | string[] | 是 | 测试步骤（自然语言） |
| `preset` | string | 否 | 继承的预设名称 |
| `config` | object | 否 | 用例级配置覆盖 |
| `cookies` | object[] | 否 | 用例级 Cookie |
| `data_driven` | object | 否 | 数据驱动配置 |

## Steps 自然语言描述规范

`steps` 是字符串数组，每一项用自然语言描述一个操作或验证：

```yaml
steps:
  - 访问 https://www.baidu.com
  - 在搜索框输入 "Python 教程"
  - 点击 "百度一下" 按钮
  - 等待搜索结果加载完成
  - 验证搜索结果包含 "Python" 相关内容
```

建议：
- 每步描述一个明确动作或验证
- 使用具体的操作动词（访问、点击、输入、验证、等待）
- 包含必要的定位信息（按钮文字、输入框名称、URL）

## 标签（Tags）

### 设置标签

```yaml
- name: 登录功能
  tags: [p1, smoke, login]
  steps:
    - 访问登录页面
    - 输入账号密码并登录
```

### 按标签过滤

使用 `-t` / `--tags` 选项过滤，多标签逗号分隔，匹配关系为 **OR**（命中任一即选中）：

```bash
# 只执行 p1 标签
burunner run tests/*.yaml -t p1

# 执行 p1 或 smoke
burunner run tests/*.yaml -t "p1,smoke"

# 标签 + 名称组合（两者同时满足）
burunner run tests/*.yaml -k "登录" -t "smoke"
```

标签匹配不区分大小写（`P1` 和 `p1` 等价）。

## 用例级 config 覆盖

单个用例可覆盖全局配置：

```yaml
- name: 需要可视化调试的用例
  config:
    headless: false
    max_steps: 50
  steps:
    - 访问 https://example.com
    - 执行复杂交互操作
```

## 测试结论判定规则

burunner 自动在 prompt 末尾追加结论输出要求。判定优先级：

| 优先级 | 条件 | 结论 |
| --- | --- | --- |
| 1 | Agent 返回 `success=false` 或文本含"测试失败" | **FAILED** |
| 2 | `history.is_successful() == False` | **FAILED** |
| 3 | 运行期异常（浏览器崩溃 / LLM 超时 / 框架异常） | **ERROR** |
| 4 | 其余情况 | **PASSED** |

## 完整示例

```yaml
presets:
  已登录状态:
    steps:
      - 访问 https://example.com/login
      - 输入用户名 admin 和密码 123456
      - 点击登录按钮

config:
  llm_provider: openai
  llm_model: gpt-4o
  parallel: 2

variables:
  base_url: "https://example.com"

cases:
  - name: 查看个人信息
    preset: 已登录状态
    tags: [smoke, p1]
    description: 验证个人信息页面正常
    steps:
      - 进入个人中心
      - 验证页面显示用户名 admin

  - name: 搜索商品
    tags: [p2, search]
    steps:
      - 访问 ${base_url}/products
      - 在搜索框输入 "手机"
      - 验证搜索结果不为空
```
