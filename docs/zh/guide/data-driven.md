# 数据驱动测试

数据驱动测试允许一条用例模板结合外部数据源，自动展开为多条用例实例。

## 基本概念

通过 `data_driven` 字段指定数据源，用例模板中的 `${field_name}` 会被数据行中对应字段的值替换。一条模板 + N 行数据 = N 条用例实例。

## data_driven 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source` | string | 外部数据文件路径（相对于 YAML 文件） |
| `data` | object[] | 内联数据（与 source 二选一） |

## 四种数据源

### CSV 文件

```yaml
cases:
  - name: 搜索功能
    data_driven:
      source: data/search.csv
    steps:
      - 访问首页
      - 在搜索框输入 ${keyword}
      - 点击搜索按钮
      - 验证搜索结果包含 ${expected}
```

CSV 文件格式：

```csv
keyword,expected
Python,Python教程
Java,Java入门
Go,Go语言
```

第一行为表头（字段名），后续每行为一条数据。

### JSON 文件

```yaml
cases:
  - name: 用户登录
    data_driven:
      source: data/users.json
    steps:
      - 访问登录页
      - 输入账号 ${username} 和密码 ${password}
      - 验证登录结果 ${result}
```

JSON 文件格式（数组）：

```json
[
  { "username": "alice", "password": "123", "result": "成功" },
  { "username": "bob", "password": "wrong", "result": "失败" },
  { "username": "", "password": "", "result": "失败" }
]
```

### YAML 文件

```yaml
cases:
  - name: 商品测试
    data_driven:
      source: data/products.yaml
    steps:
      - 访问商品页 ${id}
      - 验证商品名称为 ${name}
      - 验证价格为 ${price}
```

YAML 数据文件格式（列表）：

```yaml
- id: "1001"
  name: "手机"
  price: "2999"
- id: "1002"
  name: "平板"
  price: "3999"
```

### 内联数据

无需外部文件，直接在用例中定义 `data` 字段：

```yaml
cases:
  - name: 注册功能
    data_driven:
      data:
        - { email: "a@test.com", expect: "成功" }
        - { email: "", expect: "失败" }
        - { email: "invalid", expect: "失败" }
    steps:
      - 访问注册页
      - 输入邮箱 ${email}
      - 点击注册按钮
      - 验证结果包含 ${expect}
```

## 变量引用

数据行中的每个字段都可通过 `${field_name}` 在 steps 中引用：

```yaml
data_driven:
  data:
    - { url: "https://a.com", title: "站点A", keyword: "test" }
```

对应的引用：`${url}`、`${title}`、`${keyword}`。

## 用例展开逻辑

假设模板用例名为 "搜索功能"，CSV 有 3 行数据，则展开为：

- 搜索功能 [1/3] — 使用第 1 行数据
- 搜索功能 [2/3] — 使用第 2 行数据
- 搜索功能 [3/3] — 使用第 3 行数据

每条实例独立执行、独立判定结果。

## 完整示例

```yaml
config:
  llm_provider: openai
  llm_model: gpt-4o

cases:
  - name: 多关键词搜索验证
    data_driven:
      data:
        - { keyword: "Python", expected: "Python" }
        - { keyword: "人工智能", expected: "AI" }
        - { keyword: "browser-use", expected: "browser" }
    steps:
      - 访问 https://www.baidu.com
      - 在搜索框输入 "${keyword}"
      - 点击搜索按钮
      - 验证搜索结果包含 "${expected}" 相关内容
```

## 注意事项

- `source` 路径相对于 YAML 文件所在目录
- CSV 文件建议使用 UTF-8 编码
- `source` 和 `data` 二选一，不能同时指定
- 数据驱动变量与 `variables` 中定义的变量可共存，数据驱动字段优先
